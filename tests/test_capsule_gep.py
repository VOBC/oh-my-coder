"""
Capsule / GEP 协议测试

测试 Gene 序列化、Capsule 向后兼容、注册发现、Event 导出。
"""

import json as json_lib
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.capsule import Capsule, Gene, GEPRegistry


# ============================================================
# Gene 序列化
# ============================================================


class TestGeneSerialization:
    def test_gene_to_dict_roundtrip(self):
        gene = Gene(
            id="abc123",
            name="code-reviewer",
            category="review",
            tags=["python", "security"],
            description="专业代码审查",
            capabilities=["security-scan", "style-check"],
            version="1.2.0",
            author="test-author",
            created_at="2026-04-13T00:00:00Z",
        )
        data = gene.to_dict()
        restored = Gene.from_dict(data)
        assert restored.id == gene.id
        assert restored.name == gene.name
        assert restored.category == gene.category
        assert restored.tags == gene.tags
        assert restored.description == gene.description
        assert restored.capabilities == gene.capabilities
        assert restored.version == gene.version
        assert restored.author == gene.author
        assert restored.created_at == gene.created_at

    def test_gene_to_json_roundtrip(self):
        gene = Gene(name="planner", category="coding")
        json_str = gene.to_json()
        restored = Gene.from_dict(json_lib.loads(json_str))
        assert restored.name == gene.name

    def test_gene_from_dict_ignores_extra_keys(self):
        data = {
            "id": "id-only",
            "name": "test",
            "category": "coding",
            "extra_field": 123,
            "another_extra": "ignored",
        }
        gene = Gene.from_dict(data)
        assert gene.name == "test"
        assert gene.category == "coding"
        assert not hasattr(gene, "extra_field")
        assert not hasattr(gene, "another_extra")

    def test_gene_validation_valid(self):
        gene = Gene(name="test", category="review")
        assert gene.validate() == []

    def test_gene_validation_invalid_category(self):
        gene = Gene(name="test", category="invalid")
        errors = gene.validate()
        assert any("无效 category" in e for e in errors)

    def test_gene_validation_empty_name(self):
        gene = Gene(name="", category="coding")
        errors = gene.validate()
        assert any("name 不能为空" in e for e in errors)

    def test_gene_auto_id_and_timestamp(self):
        gene = Gene(name="auto", category="docs")
        assert gene.id != ""
        assert gene.created_at != ""


# ============================================================
# Capsule 向后兼容 .omcp
# ============================================================


class TestCapsuleOMCPBackwardCompat:
    def test_from_omcp_with_existing_gene(self):
        omcp = {
            "gene": {
                "id": "gene-001",
                "name": "web-reviewer",
                "category": "review",
                "tags": ["python", "security"],
                "description": "Web 安全审查",
                "capabilities": ["xss-scan", "csrf-scan"],
                "version": "2.0.0",
                "author": "evomap",
            },
            "prompts": {
                "system": "You are a security reviewer.",
            },
            "tools": ["grep", "curl"],
        }
        capsule = Capsule.from_omcp(omcp)
        assert capsule.gene.id == "gene-001"
        assert capsule.gene.name == "web-reviewer"
        assert capsule.gene.category == "review"
        assert "prompts" in capsule.manifest
        assert "tools" in capsule.manifest
        assert "gene" not in capsule.manifest

    def test_from_omcp_without_gene_generates_virtual_gene(self):
        omcp = {
            "name": "security-review",
            "description": "安全审查包",
            "version": "1.0.0",
            "author": "user",
            "tools": ["grep", "shell"],
        }
        capsule = Capsule.from_omcp(omcp, file_name="security-review")
        assert capsule.gene.name == "security-review"
        assert capsule.gene.id != ""

    def test_from_omcp_infers_category(self):
        omcp_with_review = {"name": "code-review", "description": "review code"}
        capsule = Capsule.from_omcp(omcp_with_review)
        assert capsule.gene.category == "review"

        omcp_with_debug = {"name": "debug-fix", "description": "debug tools"}
        capsule2 = Capsule.from_omcp(omcp_with_debug)
        assert capsule2.gene.category == "debug"

        omcp_with_test = {"tools": ["pytest", "unittest"]}
        capsule3 = Capsule.from_omcp(omcp_with_test)
        assert capsule3.gene.category == "test"

        omcp_default = {"name": "generic"}
        capsule4 = Capsule.from_omcp(omcp_default)
        assert capsule4.gene.category == "coding"

    def test_capsule_checksum_is_computed(self):
        gene = Gene(name="test-capsule", category="coding")
        capsule = Capsule(gene=gene, manifest={"tools": ["ls", "cat"]})
        assert capsule.checksum != ""
        assert len(capsule.checksum) == 64  # SHA256 hex

    def test_capsule_verify_checksum_valid(self):
        gene = Gene(name="verify-test", category="docs")
        capsule = Capsule(gene=gene, manifest={"prompts": {}})
        assert capsule.verify_checksum() is True

    def test_capsule_verify_checksum_tampered(self):
        gene = Gene(name="tampered", category="debug")
        capsule = Capsule(gene=gene, manifest={"data": 1})
        capsule.checksum = "0000000000000000000000000000000000000000"
        assert capsule.verify_checksum() is False

    def test_capsule_to_dict_roundtrip(self):
        gene = Gene(name="roundtrip", category="review")
        capsule = Capsule(
            gene=gene,
            manifest={"tools": ["ruff", "mypy"]},
            dependencies=["dep-001"],
        )
        data = capsule.to_dict()
        restored = Capsule.from_dict(data)
        assert restored.gene.name == "roundtrip"
        assert restored.manifest["tools"] == ["ruff", "mypy"]
        assert restored.dependencies == ["dep-001"]
        assert restored.checksum == capsule.checksum

    def test_capsule_save_load(self):
        gene = Gene(name="persist-test", category="test")
        capsule = Capsule(gene=gene, manifest={"tools": ["pytest"]})
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "persist.json"
            capsule.save(path)
            loaded = Capsule.load(path)
            assert loaded.gene.name == "persist-test"
            assert loaded.manifest["tools"] == ["pytest"]


# ============================================================
# GEPRegistry 注册 / 发现 / 解析
# ============================================================


class TestGEPRegistry:
    @pytest.fixture
    def registry(self):
        return GEPRegistry()

    @pytest.fixture
    def sample_capsules(self):
        return [
            Capsule(
                gene=Gene(
                    name="code-reviewer",
                    category="review",
                    tags=["python", "security"],
                    description="专业代码审查",
                    capabilities=["security-scan", "style-check"],
                    author="evomap",
                ),
                manifest={"tools": ["ruff", "pylint"]},
            ),
            Capsule(
                gene=Gene(
                    name="planner",
                    category="coding",
                    tags=["task-decomposition"],
                    description="任务规划与分解",
                    capabilities=["task-breakdown"],
                    author="evomap",
                ),
                manifest={},
            ),
            Capsule(
                gene=Gene(
                    name="bugfixer",
                    category="debug",
                    tags=["python", "bug-fix"],
                    description="Bug 定位与修复",
                    capabilities=["root-cause", "patch-gen"],
                    author="user",
                ),
                manifest={"tools": ["pytest", "debugger"]},
            ),
        ]

    def test_register_returns_gene_id(self, registry, sample_capsules):
        gene_id = registry.register(sample_capsules[0])
        assert gene_id == sample_capsules[0].gene.id

    def test_register_overwrites_existing(self, registry, sample_capsules):
        capsule = sample_capsules[0]
        registry.register(capsule)
        registry.register(capsule)  # 覆盖
        assert registry.count() == 1

    def test_discover_single_keyword(self, registry, sample_capsules):
        for c in sample_capsules:
            registry.register(c)
        results = registry.discover("python")
        names = [g.name for g in results]
        assert "code-reviewer" in names
        assert "bugfixer" in names
        assert "planner" not in names

    def test_discover_multiple_keywords_and(self, registry, sample_capsules):
        for c in sample_capsules:
            registry.register(c)
        results = registry.discover("python security")
        names = [g.name for g in results]
        assert "code-reviewer" in names
        assert "bugfixer" not in names  # 没有 security 标签

    def test_discover_no_match(self, registry, sample_capsules):
        for c in sample_capsules:
            registry.register(c)
        results = registry.discover("golang")
        assert results == []

    def test_discover_empty_query(self, registry, sample_capsules):
        for c in sample_capsules:
            registry.register(c)
        assert registry.discover("") == []

    def test_resolve_existing(self, registry, sample_capsules):
        capsule = sample_capsules[0]
        registry.register(capsule)
        resolved = registry.resolve(capsule.gene.id)
        assert resolved is not None
        assert resolved.gene.name == "code-reviewer"

    def test_resolve_nonexistent(self, registry):
        assert registry.resolve("not-exist") is None

    def test_list_all(self, registry, sample_capsules):
        for c in sample_capsules:
            registry.register(c)
        genes = registry.list_all()
        assert len(genes) == 3

    def test_unregister_existing(self, registry, sample_capsules):
        capsule = sample_capsules[0]
        registry.register(capsule)
        assert registry.unregister(capsule.gene.id) is True
        assert registry.count() == 0

    def test_unregister_nonexistent(self, registry):
        assert registry.unregister("not-exist") is False


# ============================================================
# GEP Event 导出
# ============================================================


class TestGEPEventExport:
    @pytest.fixture
    def registry(self):
        reg = GEPRegistry()
        capsule = Capsule(
            gene=Gene(
                name="event-capsule",
                category="coding",
                tags=["test"],
                description="测试能力",
            ),
            manifest={"tools": ["ls"]},
        )
        reg.register(capsule)
        return reg

    def test_export_event_format(self, registry):
        gene_id = registry.list_all()[0].id
        event = registry.export_event(gene_id)
        assert event is not None
        assert event["type"] == "GEP/Register"
        assert event["version"] == "1.0"
        assert "payload" in event
        assert "gene" in event["payload"]
        assert "manifest" in event["payload"]
        assert "checksum" in event["payload"]

    def test_export_event_nonexistent_id(self, registry):
        assert registry.export_event("no-such-id") is None

    def test_export_event_contains_gene_fields(self, registry):
        gene_id = registry.list_all()[0].id
        event = registry.export_event(gene_id)
        gene = event["payload"]["gene"]
        assert gene["name"] == "event-capsule"
        assert gene["category"] == "coding"
        assert "test" in gene["tags"]
