"""
DocumentAgent 测试
"""

from src.agents.base import AgentLane, get_agent
from src.agents.document import DocumentAgent


class TestDocumentAgentMetadata:
    """测试 DocumentAgent 元数据和注册"""

    def test_document_agent_registered(self):
        """DocumentAgent 已正确注册"""
        cls = get_agent("document")
        assert cls is not None
        assert cls == DocumentAgent

    def test_document_agent_metadata(self):
        """元数据正确"""
        agent = DocumentAgent.__new__(DocumentAgent)
        assert agent.name == "document"
        assert agent.icon == "📄"
        assert agent.lane == AgentLane.DOMAIN
        assert agent.default_tier == "low"
        assert "file_read" in agent.tools
        assert "file_write" in agent.tools

    def test_document_agent_description(self):
        """描述包含关键信息"""
        agent = DocumentAgent.__new__(DocumentAgent)
        desc = agent.description
        assert "长篇" in desc
        assert "文档" in desc
        assert "架构" in desc or "API" in desc or "文档" in desc


class TestDocumentAgentSystemPrompt:
    """测试 DocumentAgent system_prompt 内容"""

    def test_prompt_contains_document_types(self):
        """system_prompt 包含支持的文档类型"""
        agent = DocumentAgent.__new__(DocumentAgent)
        prompt = agent.system_prompt
        assert "架构文档" in prompt
        assert "API 参考" in prompt
        assert "用户手册" in prompt

    def test_prompt_contains_output_format(self):
        """system_prompt 包含输出格式规范"""
        agent = DocumentAgent.__new__(DocumentAgent)
        prompt = agent.system_prompt
        assert "H1" in prompt or "H2" in prompt
        assert "##" in prompt  # Markdown heading
        assert "```" in prompt  # Code block

    def test_prompt_distinguishes_from_writer(self):
        """明确区分 DocumentAgent 和 WriterAgent"""
        agent = DocumentAgent.__new__(DocumentAgent)
        prompt = agent.system_prompt
        assert "WriterAgent" in prompt
        # DocumentAgent 负责长文档，WriterAgent 负责快速文档
        assert "长篇" in prompt or "README" in prompt

    def test_prompt_requires_1500_words(self):
        """要求文档长度 ≥ 1500 字（在 _run 的 doc_hint 中）"""
        import inspect

        agent = DocumentAgent.__new__(DocumentAgent)
        src = inspect.getsource(agent._run)
        assert "1500" in src


class TestDocumentAgentPostProcess:
    """测试 DocumentAgent 后处理"""

    def test_post_process(self):
        """后处理返回正确的 AgentOutput"""
        from src.agents.base import AgentStatus

        agent = DocumentAgent.__new__(DocumentAgent)
        agent.name = "document"
        output = agent._post_process("# 文档内容", None)
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "# 文档内容"
        assert len(output.recommendations) == 2
        assert "docs/" in output.recommendations[0]


class TestDocumentAgentMarkdown:
    """测试文档生成 Markdown 结构"""

    def test_markdown_structure_in_prompt(self):
        """system_prompt 要求正确的 Markdown 结构"""
        agent = DocumentAgent.__new__(DocumentAgent)
        prompt = agent.system_prompt

        # 检查必要的结构元素
        required_elements = [
            "# 文档标题",  # H1 标题
            "##",  # H2 章节
            "```",  # 代码块
            "| 参数 |",  # 表格
            "常见问题",  # FAQ
        ]
        for element in required_elements:
            assert element in prompt, f"缺少必要元素: {element}"

    def test_table_format(self):
        """参数说明使用表格"""
        agent = DocumentAgent.__new__(DocumentAgent)
        prompt = agent.system_prompt
        assert "| 参数 |" in prompt
        assert "| 类型 |" in prompt
        assert "| 必需 |" in prompt or "| 描述 |" in prompt

    def test_code_block_language(self):
        """代码块指定语言"""
        agent = DocumentAgent.__new__(DocumentAgent)
        prompt = agent.system_prompt
        # 应有语言标记如 ```python
        assert "```" in prompt
        # Python 示例在文档中
        assert "python" in prompt.lower() or "yaml" in prompt.lower()
