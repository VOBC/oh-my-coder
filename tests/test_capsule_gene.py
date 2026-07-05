"""
Gene 单元测试

覆盖 gene.py 的所有方法及边界情况。
"""

import json

import pytest

from src.capsule import Gene


# ============================================================
# 初始化 & 默认值
# ============================================================


class TestGeneInit:
    def test_default_version(self):
        gene = Gene(name="default-test", category="coding")
        assert gene.version == "0.2.0"

    def test_default_author(self):
        gene = Gene(name="default-test", category="coding")
        assert gene.author == "anonymous"

    def test_default_tags_empty_list(self):
        gene = Gene(name="test", category="debug")
        assert gene.tags == []
        assert isinstance(gene.tags, list)

    def test_default_capabilities_empty_list(self):
        gene = Gene(name="test", category="docs")
        assert gene.capabilities == []
        assert isinstance(gene.capabilities, list)

    def test_default_signature_is_none(self):
        gene = Gene(name="test", category="coding")
        assert gene.signature is None

    def test_all_valid_categories(self):
        for cat in ("coding", "review", "debug", "docs", "test"):
            gene = Gene(name=f"cat-{cat}", category=cat)
            assert gene.category == cat

    def test_mutable_tags_dont_share_state(self):
        g1 = Gene(name="g1", category="coding", tags=["a", "b"])
        g2 = Gene(name="g2", category="coding")
        g2.tags.append("c")
        assert g1.tags == ["a", "b"]
        assert g2.tags == ["c"]


# ============================================================
# 自动生成字段
# ============================================================


class TestGeneAutoFields:
    def test_auto_id_is_valid_uuid(self):
        import uuid

        gene = Gene(name="uuid-test", category="coding")
        # 不应抛异常
        uuid.UUID(gene.id)

    def test_auto_id_unique_per_instance(self):
        gene1 = Gene(name="u1", category="coding")
        gene2 = Gene(name="u2", category="coding")
        assert gene1.id != gene2.id

    def test_manual_id_not_overridden(self):
        gene = Gene(name="manual", category="coding", id="my-fixed-id")
        assert gene.id == "my-fixed-id"

    def test_auto_created_at_is_iso_format(self):
        gene = Gene(name="time-test", category="coding")
        from datetime import datetime

        # 不应抛异常
        datetime.fromisoformat(gene.created_at)

    def test_manual_created_at_not_overridden(self):
        gene = Gene(
            name="manual-time",
            category="coding",
            created_at="2025-01-01T00:00:00",
        )
        assert gene.created_at == "2025-01-01T00:00:00"


# ============================================================
# 序列化
# ============================================================


class TestGeneSerialization:
    def test_to_dict_contains_all_fields(self):
        gene = Gene(
            name="serialize-test",
            category="review",
            tags=["python"],
            description="测试描述",
            capabilities=["cap1"],
            version="1.0.0",
            author="alice",
            created_at="2026-01-01T00:00:00",
            signature="sig-abc",
            id="id-123",
        )
        d = gene.to_dict()
        assert d["name"] == "serialize-test"
        assert d["category"] == "review"
        assert d["tags"] == ["python"]
        assert d["description"] == "测试描述"
        assert d["capabilities"] == ["cap1"]
        assert d["version"] == "1.0.0"
        assert d["author"] == "alice"
        assert d["created_at"] == "2026-01-01T00:00:00"
        assert d["signature"] == "sig-abc"
        assert d["id"] == "id-123"

    def test_to_json_produces_valid_json(self):
        gene = Gene(name="json-test", category="coding", tags=["go"])
        json_str = gene.to_json()
        parsed = json.loads(json_str)
        assert parsed["name"] == "json-test"
        assert parsed["tags"] == ["go"]

    def test_to_json_ensure_ascii_false_preserves_unicode(self):
        gene = Gene(name="unicode", category="coding", description="中文描述")
        json_str = gene.to_json()
        assert "中文描述" in json_str

    def test_from_dict_full_roundtrip(self):
        original = Gene(
            name="roundtrip",
            category="debug",
            tags=["bug", "trace"],
            description="完整往返",
            capabilities=["stack-trace"],
            version="3.0.0",
            author="bob",
            created_at="2026-06-01T12:00:00",
            signature="sig-xyz",
            id="id-full",
        )
        restored = Gene.from_dict(original.to_dict())
        assert restored.name == original.name
        assert restored.category == original.category
        assert restored.tags == original.tags
        assert restored.description == original.description
        assert restored.capabilities == original.capabilities
        assert restored.version == original.version
        assert restored.author == original.author
        assert restored.created_at == original.created_at
        assert restored.signature == original.signature
        assert restored.id == original.id

    def test_from_dict_minimal_data(self):
        data = {"name": "minimal", "category": "coding"}
        gene = Gene.from_dict(data)
        assert gene.name == "minimal"
        assert gene.category == "coding"
        assert gene.version == "0.2.0"
        assert gene.author == "anonymous"

    def test_from_dict_with_extra_keys_ignores_them(self):
        data = {
            "name": "extra-keys",
            "category": "docs",
            "foo": "ignored",
            "bar": 999,
            "baz": None,
            "nested": {"x": 1},
        }
        gene = Gene.from_dict(data)
        assert gene.name == "extra-keys"
        assert not hasattr(gene, "foo")
        assert not hasattr(gene, "bar")

    def test_from_dict_partial_override(self):
        data = {
            "name": "partial",
            "category": "test",
            "author": "custom-author",
            "version": "99.0.0",
        }
        gene = Gene.from_dict(data)
        assert gene.author == "custom-author"
        assert gene.version == "99.0.0"

    def test_from_json_classmethod(self):
        gene = Gene(name="from-json", category="review")
        restored = Gene.from_dict(json.loads(gene.to_json()))
        assert restored.name == "from-json"
        assert restored.category == "review"


# ============================================================
# 校验
# ============================================================


class TestGeneValidation:
    def test_validate_all_valid_returns_empty_list(self):
        gene = Gene(name="valid", category="review", tags=["py"])
        assert gene.validate() == []

    def test_validate_invalid_category_returns_error(self):
        gene = Gene(name="bad-cat", category="invalid-category")
        errors = gene.validate()
        assert len(errors) == 1
        assert "无效 category" in errors[0]
        assert "invalid-category" in errors[0]

    def test_validate_empty_name_returns_error(self):
        gene = Gene(name="", category="coding")
        errors = gene.validate()
        assert any("name 不能为空" in e for e in errors)

    def test_validate_multiple_errors(self):
        gene = Gene(name="", category="bad-cat")
        errors = gene.validate()
        assert len(errors) == 2
        error_msgs = " ".join(errors)
        assert "name 不能为空" in error_msgs
        assert "无效 category" in error_msgs

    def test_validate_category_case_sensitive(self):
        gene_upper = Gene(name="upper", category="CODING")
        assert gene_upper.validate()[0] == gene_upper.validate()[0]
        assert "无效 category" in gene_upper.validate()[0]

    def test_validate_whitespace_name(self):
        gene = Gene(name="   ", category="coding")
        errors = gene.validate()
        # whitespace name is not empty string but also not valid
        # Gene only checks name == "" so "   " is valid per current impl
        # This documents current behavior
        assert gene.name == "   "

    def test_validate_empty_category_passes(self):
        # 源码不禁止空 category
        gene = Gene(name="valid", category="")
        assert gene.validate() == []

    def test_validate_unknown_category(self):
        gene = Gene(name="test", category="unknown-type")
        errors = gene.validate()
        assert any("无效 category" in e and "unknown-type" in e for e in errors)
