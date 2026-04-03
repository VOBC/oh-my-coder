"""
Explore Agent - 代码库探索智能体

职责：
1. 快速扫描代码库，构建文件/符号映射
2. 识别项目结构、技术栈
3. 发现关键文件和依赖关系
4. 为后续 Agent 提供上下文

模型层级：LOW（快速便宜，对应 haiku）

工作流程：
1. 扫描目录结构
2. 识别文件类型和分布
3. 提取关键符号（函数、类、模块）
4. 生成项目地图
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import os

from .base import (
    BaseAgent,
    AgentContext,
    AgentOutput,
    AgentStatus,
    AgentLane,
    register_agent,
)
from ..core.router import TaskType


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    type: str  # python, javascript, markdown, etc.
    size: int
    lines: int
    importance: float  # 0-1，基于位置和命名推断


@dataclass
class ProjectMap:
    """项目地图"""
    root_path: str
    language_distribution: Dict[str, int]  # 语言 -> 文件数
    key_directories: List[str]
    entry_points: List[str]  # 入口文件
    config_files: List[str]
    test_files: List[str]
    dependencies: List[str]  # 依赖（从 package.json/requirements.txt 提取）
    structure_tree: str  # 目录树


@register_agent
class ExploreAgent(BaseAgent):
    """
    代码库探索 Agent
    
    特点：
    - 使用 LOW tier 模型（快速便宜）
    - 不需要深度理解代码，只需识别结构
    - 输出结构化的项目地图
    """
    
    name = "explore"
    description = "代码库探索智能体 - 快速扫描并构建项目地图"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "low"
    icon = "🔍"
    tools = ["file_read", "directory_scan"]
    
    @property
    def system_prompt(self) -> str:
        return """你是一个专业的代码库探索智能体。

## 角色
你的职责是快速扫描代码库，构建文件和符号的映射关系，为后续分析提供基础。

## 能力
1. 目录结构扫描 - 识别项目的组织方式
2. 技术栈识别 - 从文件类型和配置推断技术栈
3. 关键文件定位 - 找出入口文件、配置文件、核心模块
4. 依赖分析 - 从 package.json、requirements.txt 等提取依赖

## 工作原则
1. **快速优先** - 不要深度阅读代码，只需识别结构
2. **结构化输出** - 使用 Markdown 表格和代码块组织信息
3. **重点突出** - 标记最重要的文件和目录
4. **语言中立** - 支持多种编程语言

## 输出格式
你的输出应该包含：
1. 项目概览（语言、框架、规模）
2. 目录结构树
3. 关键文件列表（带说明）
4. 技术栈总结
5. 建议的后续探索路径

## 注意事项
- 不要猜测项目的功能，只描述观察到的事实
- 如果找不到关键信息，明确说明
- 保持简洁，避免冗余
"""
    
    async def _run(
        self,
        context: AgentContext,
        prompt: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        执行代码库探索
        
        步骤：
        1. 扫描目录结构
        2. 收集文件统计
        3. 调用模型生成项目地图
        """
        project_path = context.project_path
        
        # 1. 扫描目录结构
        structure = self._scan_directory(project_path)
        
        # 2. 收集文件统计
        file_stats = self._collect_file_stats(project_path)
        
        # 3. 提取依赖信息
        dependencies = self._extract_dependencies(project_path)
        
        # 4. 构建完整 prompt
        exploration_context = f"""
## 扫描结果

### 目录结构
```
{structure}
```

### 文件统计
{self._format_file_stats(file_stats)}

### 依赖信息
{self._format_dependencies(dependencies)}

请基于以上信息，生成项目地图和探索建议。
"""
        
        prompt.append({"role": "user", "content": exploration_context})
        
        # 5. 调用模型
        from ..models.base import Message
        
        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in prompt
        ]
        
        # 使用路由器选择模型
        response = await self.model_router.route_and_call(
            task_type=TaskType.EXPLORE,
            messages=messages,
            complexity="low",  # Explore 使用 LOW tier
        )
        
        return response.content
    
    def _scan_directory(
        self,
        root_path: Path,
        max_depth: int = 3,
        ignore_dirs: set = None,
    ) -> str:
        """扫描目录结构并生成树形表示"""
        if ignore_dirs is None:
            ignore_dirs = {
                '__pycache__', '.git', 'node_modules', '.venv', 'venv',
                'build', 'dist', '.idea', '.vscode', '.pytest_cache',
            }
        
        lines = []
        
        def scan(path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return
            
            try:
                items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            except PermissionError:
                return
            
            dirs = [x for x in items if x.is_dir() and x.name not in ignore_dirs]
            files = [x for x in items if x.is_file()]
            
            # 限制显示的文件数量
            max_files = 20
            if len(files) > max_files:
                shown_files = files[:max_files]
                hidden_count = len(files) - max_files
            else:
                shown_files = files
                hidden_count = 0
            
            for i, dir_item in enumerate(dirs):
                is_last = (i == len(dirs) - 1) and not shown_files
                lines.append(f"{prefix}{'└── ' if is_last else '├── '}{dir_item}/")
                new_prefix = prefix + ('    ' if is_last else '│   ')
                scan(dir_item, new_prefix, depth + 1)
            
            for i, file_item in enumerate(shown_files):
                is_last = (i == len(shown_files) - 1) and hidden_count == 0
                lines.append(f"{prefix}{'└── ' if is_last else '├── '}{file_item.name}")
            
            if hidden_count > 0:
                lines.append(f"{prefix}└── ... ({hidden_count} more files)")
        
        lines.append(f"{root_path.name}/")
        scan(root_path, "", 0)
        
        return "\n".join(lines)
    
    def _collect_file_stats(
        self,
        root_path: Path,
        ignore_dirs: set = None,
    ) -> Dict[str, Any]:
        """收集文件统计信息"""
        if ignore_dirs is None:
            ignore_dirs = {
                '__pycache__', '.git', 'node_modules', '.venv', 'venv',
                'build', 'dist', '.idea', '.vscode', '.pytest_cache',
            }
        
        language_map = {}
        total_files = 0
        total_lines = 0
        key_files = []
        
        # 文件扩展名到语言的映射
        ext_to_lang = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'JavaScript (React)',
            '.tsx': 'TypeScript (React)',
            '.go': 'Go',
            '.java': 'Java',
            '.md': 'Markdown',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.toml': 'TOML',
            '.txt': 'Text',
            '.sh': 'Shell',
        }
        
        for root, dirs, files in os.walk(root_path):
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                ext = Path(file).suffix.lower()
                lang = ext_to_lang.get(ext, 'Other')
                
                language_map[lang] = language_map.get(lang, 0) + 1
                total_files += 1
                
                # 统计行数
                try:
                    file_path = Path(root) / file
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = sum(1 for _ in f)
                        total_lines += lines
                except:
                    pass
                
                # 识别关键文件
                if file in ['main.py', 'app.py', 'index.js', 'index.ts', '__init__.py']:
                    key_files.append(str(Path(root).relative_to(root_path) / file))
        
        return {
            'language_distribution': language_map,
            'total_files': total_files,
            'total_lines': total_lines,
            'key_files': key_files,
        }
    
    def _extract_dependencies(
        self,
        root_path: Path,
    ) -> Dict[str, List[str]]:
        """提取项目依赖"""
        dependencies = {
            'python': [],
            'node': [],
            'other': [],
        }
        
        # Python 依赖
        req_file = root_path / 'requirements.txt'
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    dependencies['python'] = [
                        line.strip() for line in f
                        if line.strip() and not line.startswith('#')
                    ]
            except:
                pass
        
        # Node 依赖
        package_file = root_path / 'package.json'
        if package_file.exists():
            try:
                import json
                with open(package_file, 'r') as f:
                    package = json.load(f)
                    dependencies['node'] = list(package.get('dependencies', {}).keys())
            except:
                pass
        
        return dependencies
    
    def _format_file_stats(self, stats: Dict[str, Any]) -> str:
        """格式化文件统计"""
        lines = []
        
        lines.append(f"- 总文件数：{stats['total_files']}")
        lines.append(f"- 总代码行数：{stats['total_lines']:,}")
        
        lines.append("\n### 语言分布")
        for lang, count in sorted(stats['language_distribution'].items(), key=lambda x: -x[1]):
            lines.append(f"- {lang}: {count} 文件")
        
        if stats['key_files']:
            lines.append("\n### 关键文件")
            for file in stats['key_files']:
                lines.append(f"- {file}")
        
        return "\n".join(lines)
    
    def _format_dependencies(self, deps: Dict[str, List[str]]) -> str:
        """格式化依赖信息"""
        lines = []
        
        if deps['python']:
            lines.append("### Python 依赖")
            for dep in deps['python'][:20]:  # 限制显示数量
                lines.append(f"- {dep}")
            if len(deps['python']) > 20:
                lines.append(f"- ... ({len(deps['python']) - 20} more)")
        
        if deps['node']:
            lines.append("### Node 依赖")
            for dep in deps['node'][:20]:
                lines.append(f"- {dep}")
            if len(deps['node']) > 20:
                lines.append(f"- ... ({len(deps['node']) - 20} more)")
        
        if not lines:
            lines.append("（未找到依赖文件）")
        
        return "\n".join(lines)
    
    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """后处理 - 提取关键信息"""
        # TODO: 从结果中提取结构化信息
        
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "使用 analyst Agent 深入分析项目需求",
                "使用 architect Agent 设计系统架构",
            ],
            next_agent="analyst",
        )
