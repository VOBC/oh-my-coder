"""
GEPRegistry 单元测试

覆盖 registry.py 的所有方法及边界情况。
"""

import pytest

from src.capsule import Capsule, Gene, GEPRegistry


# ============================================================
# 辅助 Fixture
# ============================================================


@pytest.fixture
def gene_review():
    return Gene(
        id="gene-review-001",
        name="code-reviewer",
        category="review",
        tags=["python", "security"],
        description="专业代码审查",
        capabilities=["security-scan"],
        version="1.0.0",
        author="evomap",
    )


@pytest.fixture
def gene_debug():
    return Gene(
        id="gene-debug-002",
        name="bugfixer",
        category="debug",
        tags=["python", "bug-fix"],
        description="Bug 定位与修复",
        capabilities=["root-cause", "patch-gen"],
        version="0.9.0",
        author="user",
    )


@pytest.fixture
def gene_docs():
    return Gene(
        id="gene-docs-003",
        name="doc-writer",
        category="docs",
        tags=["markdown", "readme"],
        description="文档生成工具",
        capabilities=["readme-gen"],
        version="2.0.0",
        author="bob",
    )


@pytest.fixture
def capsule_review(gene_review):
    return Capsule(gene=gene_review, manifest={"tools": ["ruff", "pylint"]})


@pytest.fixture
def capsule_debug(gene_debug):
    return Capsule(gene=gene_debug, manifest={"tools": ["pytest", "debugger"]})


@pytest.fixture
def capsule_docs(gene_docs):
    return Capsule(gene=gene_docs, manifest={"prompts": {"system": "You are a doc writer."}})


@pytest.fixture
def registry(capsule_review, capsule_debug, capsule_docs):
    reg = GEPRegistry()
    reg.register(capsule_review)
    reg.register(capsule_debug)
    reg.register(capsule_docs)
    return reg


# ============================================================
# 注册
# ============================================================


class TestRegistryRegister:
    def test_register_returns_gene_id(self, registry, capsule_review):
        gene_id = registry.register(capsule_review)
        assert gene_id == capsule_review.gene.id

    def test_register_adds_to_store(self, capsule_review):
        reg = GEPRegistry()
        assert reg.count() == 0
        reg.register(capsule_review)
        assert reg.count() == 1

    def test_register_same_capsule_twice_keeps_one(self, capsule_review):
        reg = GEPRegistry()
        reg.register(capsule_review)
        reg.register(capsule_review)
        assert reg.count() == 1

    def test_register_replaces_existing(self, capsule_review, capsule_debug):
        reg = GEPRegistry()
        reg.register(capsule_review)
        reg.register(capsule_debug)
        assert reg.count() == 2
        # 使用相同 gene_id 覆盖
        capsule_review.gene.category = "debug"
        reg.register(capsule_review)
        assert reg.count() == 2
        resolved = reg.resolve(capsule_review.gene.id)
        assert resolved.gene.category == "debug"


# ============================================================
# 发现
# ============================================================


class TestRegistryDiscover:
    def test_discover_single_keyword_in_name(self, registry):
        results = registry.discover("reviewer")
        assert len(results) == 1
        assert results[0].name == "code-reviewer"

    def test_discover_single_keyword_in_category(self, registry):
        results = registry.discover("debug")
        names = [g.name for g in results]
        assert "bugfixer" in names

    def test_discover_single_keyword_in_tags(self, registry):
        results = registry.discover("security")
        names = [g.name for g in results]
        assert "code-reviewer" in names
        assert "bugfixer" not in names

    def test_discover_single_keyword_in_description(self, registry):
        results = registry.discover("修复")
        names = [g.name for g in results]
        assert "bugfixer" in names

    def test_discover_single_keyword_in_capabilities(self, registry):
        results = registry.discover("patch-gen")
        assert len(results) == 1
        assert results[0].name == "bugfixer"

    def test_discover_multiple_keywords_and_logic(self, registry):
        results = registry.discover("python security")
        names = [g.name for g in results]
        assert "code-reviewer" in names
        assert "bugfixer" not in names  # has python but not security

    def test_discover_multiple_keywords_all_match(self, registry):
        results = registry.discover("python bug-fix")
        names = [g.name for g in results]
        assert "bugfixer" in names
        assert "code-reviewer" not in names  # has python but not bug-fix

    def test_discover_three_keywords(self, registry):
        # bugfixer has python + bug-fix + root-cause
        results = registry.discover("python bug-fix root-cause")
        assert len(results) == 1
        assert results[0].name == "bugfixer"

    def test_discover_no_match(self, registry):
        results = registry.discover("golang")
        assert results == []

    def test_discover_empty_query(self, registry):
        results = registry.discover("")
        assert results == []

    def test_discover_whitespace_only_query(self, registry):
        results = registry.discover("   ")
        assert results == []

    def test_discover_case_insensitive(self, registry):
        results = registry.discover("PYTHON")
        names = [g.name for g in results]
        assert "code-reviewer" in names
        assert "bugfixer" in names

    def test_discover_strips_whitespace(self, registry):
        results = registry.discover("  python  ")
        assert len(results) == 2

    def test_discover_all_keywords_must_be_present(self, registry):
        # "review" only in code-reviewer (name + description)
        results = registry.discover("review python")
        names = [g.name for g in results]
        assert "code-reviewer" in names
        # bugfixer has no "review"
        assert "bugfixer" not in names


# ============================================================
# 解析
# ============================================================


class TestRegistryResolve:
    def test_resolve_existing_gene_id(self, registry, capsule_review):
        resolved = registry.resolve(capsule_review.gene.id)
        assert resolved is not None
        assert resolved.gene.name == "code-reviewer"

    def test_resolve_nonexistent_returns_none(self, registry):
        assert registry.resolve("not-exist-id") is None

    def test_resolve_empty_string_returns_none(self, registry):
        assert registry.resolve("") is None

    def test_resolve_returns_full_capsule(self, registry):
        resolved = registry.resolve("gene-review-001")
        assert resolved is not None
        assert resolved.manifest["tools"] == ["ruff", "pylint"]

    def test_resolve_after_unregister_returns_none(self, capsule_review):
        reg = GEPRegistry()
        reg.register(capsule_review)
        gene_id = capsule_review.gene.id
        reg.unregister(gene_id)
        assert reg.resolve(gene_id) is None


# ============================================================
# 事件导出
# ============================================================


class TestRegistryExportEvent:
    def test_export_event_returns_dict(self, registry):
        event = registry.export_event("gene-review-001")
        assert isinstance(event, dict)

    def test_export_event_structure(self, registry):
        event = registry.export_event("gene-review-001")
        assert event["type"] == "GEP/Register"
        assert event["version"] == "1.0"
        assert "payload" in event

    def test_export_event_payload_contains_capsule_fields(self, registry):
        event = registry.export_event("gene-review-001")
        payload = event["payload"]
        assert "gene" in payload
        assert "manifest" in payload
        assert "dependencies" in payload
        assert "checksum" in payload

    def test_export_event_gene_fields(self, registry):
        event = registry.export_event("gene-review-001")
        gene = event["payload"]["gene"]
        assert gene["name"] == "code-reviewer"
        assert gene["category"] == "review"
        assert "python" in gene["tags"]
        assert "security-scan" in gene["capabilities"]

    def test_export_event_nonexistent_returns_none(self, registry):
        assert registry.export_event("no-such-id") is None

    def test_export_event_empty_string_returns_none(self, registry):
        assert registry.export_event("") is None

    def test_export_event_manifest_preserved(self, registry):
        event = registry.export_event("gene-docs-003")
        manifest = event["payload"]["manifest"]
        assert "prompts" in manifest


# ============================================================
# _infer_category 边界
# ============================================================


class TestInferCategory:
    def test_infer_doc_in_description(self):
        from src.capsule import Capsule

        capsule = Capsule.from_omcp({"name": "doc-writer", "description": "write docs"})
        assert capsule.gene.category == "docs"

    def test_infer_readme_in_name(self):
        from src.capsule import Capsule

        capsule = Capsule.from_omcp({"name": "readme-writer"})
        assert capsule.gene.category == "docs"

    def test_infer_readme_in_tools(self):
        from src.capsule import Capsule

        capsule = Capsule.from_omcp({"tools": ["readme-gen"]})
        assert capsule.gene.category == "docs"

    def test_infer_fix_without_debug(self):
        from src.capsule import Capsule

        capsule = Capsule.from_omcp({"name": "quick-fix"})
        assert capsule.gene.category == "debug"

    def test_infer_default_coding(self):
        from src.capsule import Capsule

        capsule = Capsule.from_omcp({"name": "generic"})
        assert capsule.gene.category == "coding"


# ============================================================
# 辅助 API
# ============================================================


class TestRegistryAuxiliary:
    def test_list_all_returns_all_genes(self, registry):
        genes = registry.list_all()
        names = [g.name for g in genes]
        assert "code-reviewer" in names
        assert "bugfixer" in names
        assert "doc-writer" in names

    def test_list_all_returns_gene_objects(self, registry):
        genes = registry.list_all()
        for g in genes:
            assert isinstance(g, Gene)

    def test_list_all_empty_registry(self):
        reg = GEPRegistry()
        assert reg.list_all() == []

    def test_unregister_existing(self, registry):
        result = registry.unregister("gene-review-001")
        assert result is True
        assert registry.count() == 2

    def test_unregister_nonexistent_returns_false(self, registry):
        result = registry.unregister("not-exist")
        assert result is False
        assert registry.count() == 3

    def test_unregister_already_unregistered(self, registry):
        registry.unregister("gene-review-001")
        result = registry.unregister("gene-review-001")
        assert result is False

    def test_count_initial_zero(self):
        reg = GEPRegistry()
        assert reg.count() == 0

    def test_count_after_register(self, capsule_review):
        reg = GEPRegistry()
        reg.register(capsule_review)
        assert reg.count() == 1

    def test_count_consistent_after_mixed_operations(self):
        reg = GEPRegistry()
        g1 = Gene(name="g1", category="coding")
        g2 = Gene(name="g2", category="review")
        reg.register(Capsule(gene=g1))
        reg.register(Capsule(gene=g2))
        assert reg.count() == 2
        reg.unregister(g1.id)
        assert reg.count() == 1
        reg.register(Capsule(gene=g1))
        assert reg.count() == 2

    def test_resolve_after_clear(self, capsule_review):
        reg = GEPRegistry()
        reg.register(capsule_review)
        gene_id = capsule_review.gene.id
        # 清空 store
        reg._store.clear()
        assert reg.resolve(gene_id) is None
