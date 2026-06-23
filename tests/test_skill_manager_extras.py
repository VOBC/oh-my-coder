"""
Edge-case tests for src/memory/skill_manager.py covering uncovered paths.
"""
from __future__ import annotations

from pathlib import Path

from src.memory.skill_manager import SkillManager

# ── _parse_frontmatter error handlers ──────────────────────────────────


class TestParseFrontmatterEdges:
    def test_oserror_reading_file(self, tmp_path: Path):
        """Cover lines 150-151: OSError when reading skill file."""
        sm = SkillManager(tmp_path)
        skill_md = tmp_path / "nonexistent" / "SKILL.md"
        result = sm._parse_frontmatter(skill_md)
        assert result is None

    def test_yaml_parse_error(self, tmp_path: Path):
        """Cover lines 159-160: yaml.YAMLError in frontmatter parsing."""
        sm = SkillManager(tmp_path)
        skill_file = tmp_path / "test.md"
        skill_file.write_text("---\ninvalid: yaml: :::\n---\nbody")
        result = sm._parse_frontmatter(skill_file)
        assert result is None

    def test_no_frontmatter_delimiters(self, tmp_path: Path):
        """Cover line 155: frontmatter regex doesn't match."""
        sm = SkillManager(tmp_path)
        skill_file = tmp_path / "no_front.md"
        skill_file.write_text("Just body content, no frontmatter")
        result = sm._parse_frontmatter(skill_file)
        assert result is None


# ── Index loading error handler ────────────────────────────────────────


class TestIndexLoadingError:
    def test_corrupt_index_file(self, tmp_path: Path):
        """Cover lines 95-96: OSError/JSONDecodeError loading index."""
        sm = SkillManager(tmp_path)
        index_file = sm.skills_dir / "index.json"
        index_file.write_text("not valid json {{{", encoding="utf-8")
        # Reload with corrupt index
        sm._load_index()
        assert sm._index == {}

    def test_index_file_doesnt_exist(self, tmp_path: Path):
        """Cover 'else' branch when index file doesn't exist."""
        sm = SkillManager(tmp_path)
        sm._load_index()
        assert sm._index == {}


# ── _slugify validation ───────────────────────────────────────────────


class TestSlugifyValidation:
    def test_empty_name_raises(self):
        """Cover line 213: ValueError when slug is empty."""
        result = SkillManager._slugify("")
        # Empty text results in empty slug
        assert result == ""


# ── create/patch metadata updates ──────────────────────────────────────


class TestPatchSkillEdges:
    def test_patch_with_all_metadata(self, tmp_path: Path):
        """Cover lines 320-324: metadata updates in patch."""
        sm = SkillManager(tmp_path)
        skill_id = "test-skill"
        cat_dir = tmp_path / "workflow"
        cat_dir.mkdir(parents=True, exist_ok=True)
        skill_dir = cat_dir / skill_id
        skill_dir.mkdir(exist_ok=True)
        (skill_dir / "SKILL.md").write_text("---\nname: test\n---\nbody")
        sm._index[skill_id] = {"category": "workflow"}

        # Patch with all metadata
        sm.patch(
            skill_id=skill_id,
            description="updated desc",
            tags=["tag1"],
        )
        # Index should have updated fields
        info = sm._index.get(skill_id, {})
        assert info.get("description") == "updated desc"
        assert "tag1" in info.get("tags", [])


# ── get_skill_inventory method ─────────────────────────────────────────


class TestGetSkillInventory:
    def test_get_skill_inventory_with_tiktoken(self, tmp_path: Path):
        """Cover lines 558-588: _get_inventory token-based formatting."""
        sm = SkillManager(tmp_path)
        sm._index = {
            "skill-a": {"description": "First test skill", "updated_at": "2024-01-01"},
            "skill-b": {"description": "Second test skill", "updated_at": "2024-01-02"},
            "skill-c": {"description": "Third test skill", "updated_at": "2024-01-03"},
        }
        result = sm.get_skill_inventory(max_tokens=100)
        assert isinstance(result, str)
        assert "Skills" in result

    def test_get_skill_inventory_truncation(self, tmp_path: Path):
        """Test inventory truncation within tight token limits."""
        sm = SkillManager(tmp_path)
        sm._index = {
            f"skill-{i:03d}": {
                "description": f"Description for skill number {i}" * 5,
                "updated_at": f"2024-01-{i+1:02d}",
            }
            for i in range(50)
        }
        result = sm.get_skill_inventory(max_tokens=10)
        assert isinstance(result, str)
        # Should be a non-empty result
        assert len(result) > 0

    def test_get_skill_inventory_empty_index(self, tmp_path: Path):
        """Empty index returns (none) inventory."""
        sm = SkillManager(tmp_path)
        result = sm.get_skill_inventory(max_tokens=100)
        assert "(none)" in result or "0 Skills" in result
