from __future__ import annotations
"""
Wiki Generator - Markdown 文档生成器

从解析的模块信息生成结构化 Markdown 文档。
"""

from pathlib import Path

from .parser import ClassInfo, FunctionInfo, ModuleInfo, PythonParser


class WikiGenerator:
    """Wiki 文档生成器"""

    def __init__(
        self,
        project_name: str,
        project_path: Path | str,
        parser: PythonParser | None = None,
    ):
        """
        初始化生成器

        Args:
            project_name: 项目名称
            project_path: 项目路径
            parser: Python 解析器
        """
        self.project_name = project_name
        self.project_path = Path(project_path)
        self.parser = parser or PythonParser(project_path)

    def generate(self, output_path: Path | str | None = None) -> str:
        """
        生成 Wiki 文档

        Args:
            output_path: 输出文件路径，默认输出到 REPO_WIKI.md

        Returns:
            生成的 Markdown 内容
        """
        modules = self.parser.scan_directory(self.project_path)

        # 按目录结构组织
        content = self._generate_header()
        content += self._generate_summary(modules)
        content += self._generate_project_structure(modules)
        content += self._generate_module_details(modules)
        content += self._generate_footer()

        # 如果指定了输出路径，写入文件
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            print(f"✅ Wiki 文档已生成: {output_path}")

        return content

    def _generate_header(self) -> str:
        """生成文档头部"""
        return f"""# {self.project_name}

> ⚠️ **注意**: 此文档由 oh-my-coder 自动生成，请勿手动编辑。
> 生成时间: <!-- GENERATED_AT -->

---

## 目录

- [项目概述](#项目概述)
- [项目结构](#项目结构)
- [模块详解](#模块详解)
- [API 参考](#api-参考)

---

"""

    def _generate_summary(self, modules: list[ModuleInfo]) -> str:
        """生成项目摘要"""
        total_files = len(modules)
        total_classes = sum(len(m.classes) for m in modules)
        total_functions = sum(len(m.functions) for m in modules)

        # 统计导入最多的模块
        top_imports = sorted(
            modules,
            key=lambda m: len(m.imports),
            reverse=True,
        )[:5]

        content = "## 项目概述\n\n"

        if modules and modules[0].docstring:
            content += f"{modules[0].docstring}\n\n"

        content += f"""| 指标 | 数值 |
|------|------|
| 总文件数 | {total_files} |
| 总类数 | {total_classes} |
| 总函数数 | {total_functions} |

"""

        if top_imports:
            content += "### 核心依赖\n\n"
            content += "```python\n"
            for mod in top_imports[:3]:
                for imp in mod.imports[:3]:
                    if imp.module:
                        content += f"import {imp.module}\n"
            content += "```\n\n"

        return content

    def _generate_project_structure(self, modules: list[ModuleInfo]) -> str:
        """生成项目结构树"""
        content = "## 项目结构\n\n"
        content += "```\n"

        # 按路径分组
        by_dir: dict[str, list[ModuleInfo]] = {}
        for mod in modules:
            dir_name = str(mod.relative_path.parent)
            if dir_name not in by_dir:
                by_dir[dir_name] = []
            by_dir[dir_name].append(mod)

        # 生成树形结构
        for dir_name in sorted(by_dir.keys()):
            if dir_name == ".":
                content += f"{self.project_path.name}/\n"
                prefix = "├── "
            else:
                parts = dir_name.split("/")
                indent = "│   " * (len(parts) - 1)
                content += f"{indent}├── {parts[-1]}/\n"
                prefix = indent + "│   "

            for i, mod in enumerate(
                sorted(by_dir[dir_name], key=lambda m: m.relative_path.name)
            ):
                is_last = i == len(by_dir[dir_name]) - 1
                file_prefix = "└── " if is_last else "├── "
                content += f"{prefix}{file_prefix}{mod.relative_path.name}\n"

        content += "```\n\n"

        # 目录说明
        if "src" in [str(m.relative_path.parent) for m in modules]:
            content += "### 目录说明\n\n"
            content += "| 目录 | 说明 |\n|------|------|\n"
            content += "| src/ | 源代码目录 |\n"
            content += "| tests/ | 测试文件 |\n"
            content += "| docs/ | 文档 |\n\n"

        return content

    def _generate_module_details(self, modules: list[ModuleInfo]) -> str:
        """生成模块详情"""
        content = "## 模块详解\n\n"

        for module in sorted(modules, key=lambda m: str(m.relative_path)):
            content += self._generate_module_section(module)

        return content

    def _generate_module_section(self, module: ModuleInfo) -> str:
        """生成单个模块的文档"""
        rel_path = module.relative_path

        content = f"### `{rel_path}`\n\n"

        if module.docstring:
            content += f"{module.docstring}\n\n"

        # 类列表
        if module.classes:
            content += "#### 类\n\n"
            for cls in module.classes:
                content += self._generate_class(cls)

        # 函数列表
        if module.functions:
            content += "#### 函数\n\n"
            for func in module.functions:
                content += self._generate_function(func)

        return content

    def _generate_class(self, cls: ClassInfo) -> str:
        """生成类文档"""
        content = f"##### `{cls.name}`\n\n"

        if cls.docstring:
            # 截取文档字符串第一行作为简短描述
            doc_lines = cls.docstring.strip().split("\n")
            content += f"{doc_lines[0].strip()}\n\n"

        if cls.base_classes:
            content += f"**继承**: {', '.join(cls.base_classes)}\n\n"

        # 公开方法
        public_methods = cls.public_methods
        if public_methods:
            content += "| 方法 | 说明 |\n|------|------|\n"
            for method in public_methods:
                desc = (
                    method.docstring.split("\n")[0].strip() if method.docstring else ""
                )
                content += f"| `{method.signature}` | {desc} |\n"
            content += "\n"

        return content

    def _generate_function(self, func: FunctionInfo) -> str:
        """生成函数文档"""
        content = f"##### `{func.signature}`\n\n"

        if func.docstring:
            # 截取文档字符串第一段
            doc_lines = func.docstring.strip().split("\n")
            content += f"{doc_lines[0].strip()}\n\n"

        return content

    def _generate_footer(self) -> str:
        """生成文档尾部"""
        return """---

*此文档由 [oh-my-coder](https://github.com/VOBC/oh-my-coder) 自动生成*
"""
