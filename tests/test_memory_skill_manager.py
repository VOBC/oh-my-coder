"""Tests for src/memory/skill_manager.py"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.memory.skill_manager import SkillManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_skill(skill_dir: Path, category: str, skill_id: str, frontmatter: dict, body: str) -> Path:
    """Write a SKILL.md file to the skills directory."""
    cat_dir = skill_dir / category / skill_id
    cat_dir.mkdir(parents=True, exist_ok=True)
    fm_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False)
    content = f"---\n{fm_str}---\n\n{body}\n"
    path = cat_dir / "SKILL.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_skills_dir(tmp_path: Path) -> Path:
    """A temporary skills root directory with all category subdirs created."""
    d = tmp_path / "skills"
    d.mkdir(parents=True, exist_ok=True)
    for cat in SkillManager.CATEGORIES:
        (d / cat).mkdir(exist_ok=True)
    return d


@pytest.fixture
def manager(tmp_skills_dir: Path) -> SkillManager:
    """A SkillManager backed by a temporary directory."""
    return SkillManager(skills_dir=tmp_skills_dir)


@pytest.fixture
def manager_with_index(tmp_skills_dir: Path) -> SkillManager:
    """A SkillManager pre-loaded with two skills in the index."""
    mgr = SkillManager(skills_dir=tmp_skills_dir)

    # Write a real skill file on disk (so rebuild_index works)
    _write_skill(
        tmp_skills_dir,
        "debugging",
        "slow-query",
        {
            "name": "slow-query",
            "description": "Fix slow queries",
            "category": "debugging",
            "tags": ["sql", "performance"],
            "triggers": ["query slow", "timeout"],
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        },
        "# Slow Query\n\nWhen SQL is slow...\n",
    )

    # Add a second skill only to the index (no file on disk — for edge cases)
    now = time.strftime("%Y-%m-%d")
    mgr._index["index-only-skill"] = {
        "name": "Index Only",
        "description": "Only in index, no file",
        "category": "workflow",
        "tags": ["test"],
        "triggers": [],
        "created_at": now,
        "updated_at": now,
        "path": str(tmp_skills_dir / "workflow" / "index-only-skill" / "SKILL.md"),
    }

    return mgr


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_default_skills_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Default skills_dir falls back to Path('.omc/skills')."""
        # cd to tmp so default path is clean
        monkeypatch.chdir(tmp_path)
        mgr = SkillManager()
        assert mgr.skills_dir == Path(".omc/skills")

    def test_custom_skills_dir(self, tmp_skills_dir: Path):
        """Custom skills_dir is stored and index_file derived from it."""
        mgr = SkillManager(skills_dir=tmp_skills_dir)
        assert mgr.skills_dir == tmp_skills_dir
        assert mgr.index_file == tmp_skills_dir / "index.json"

    def test_init_creates_categories(self, tmp_skills_dir: Path):
        """_init() creates all category sub-directories."""
        SkillManager(skills_dir=tmp_skills_dir)
        for cat in SkillManager.CATEGORIES:
            assert (tmp_skills_dir / cat).is_dir()


# ---------------------------------------------------------------------------
# _load_index / _save_index
# ---------------------------------------------------------------------------

class TestIndexPersistence:
    def test_load_index_file_not_exists(self, tmp_skills_dir: Path):
        """When index.json does not exist, _index is empty."""
        mgr = SkillManager(skills_dir=tmp_skills_dir)
        assert mgr._index == {}

    def test_load_index_valid_json(self, tmp_skills_dir: Path):
        """Valid index.json is loaded correctly."""
        index_data = {"test-skill": {"name": "Test", "description": "A test skill"}}
        (tmp_skills_dir / "index.json").write_text(
            json.dumps(index_data), encoding="utf-8"
        )
        mgr = SkillManager(skills_dir=tmp_skills_dir)
        assert mgr._index == index_data

    def test_load_index_corrupt_json(self, tmp_skills_dir: Path):
        """Corrupt JSON falls back to empty index."""
        (tmp_skills_dir / "index.json").write_text("{not json", encoding="utf-8")
        mgr = SkillManager(skills_dir=tmp_skills_dir)
        assert mgr._index == {}

    def test_save_index_roundtrip(self, tmp_skills_dir: Path):
        """_save_index writes valid JSON and _load_index reads it back."""
        mgr = SkillManager(skills_dir=tmp_skills_dir)
        mgr._index["roundtrip"] = {"name": "Roundtrip", "description": "Test"}
        mgr._save_index()

        # Read directly from disk
        raw = json.loads((tmp_skills_dir / "index.json").read_text(encoding="utf-8"))
        assert raw == mgr._index


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_basic(self):
        assert SkillManager._slugify("Hello World") == "hello-world"

    def test_special_chars_removed(self):
        assert SkillManager._slugify("Fix @#$% Bug!") == "fix-bug"

    def test_underscore_space_merged(self):
        assert SkillManager._slugify("foo_bar  baz") == "foo-bar-baz"

    def test_multiple_dashes_collapsed(self):
        assert SkillManager._slugify("a--b---c") == "a-b-c"

    def test_trim_dashes(self):
        assert SkillManager._slugify("---hello---") == "hello"

    def test_truncate_long(self):
        long_name = "a" * 60
        slug = SkillManager._slugify(long_name)
        assert len(slug) <= 48
        assert slug == "a" * 48


# ---------------------------------------------------------------------------
# _parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_valid_frontmatter(self, tmp_path: Path):
        fm = {
            "name": "test",
            "description": "A test",
            "category": "debugging",
            "tags": ["a", "b"],
            "triggers": ["trigger1"],
        }
        content = f"---\n{yaml.dump(fm)}---\n\n# Body\n"
        p = tmp_path / "SKILL.md"
        p.write_text(content, encoding="utf-8")

        result = SkillManager._parse_frontmatter(p)
        assert result == fm

    def test_no_frontmatter(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("# Just a header\n\nNo frontmatter here", encoding="utf-8")
        assert SkillManager._parse_frontmatter(p) is None

    def test_invalid_yaml(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: [broken\n  yaml\n---", encoding="utf-8")
        assert SkillManager._parse_frontmatter(p) is None

    def test_oserror(self, tmp_path: Path):
        p = tmp_path / "nonexistent" / "SKILL.md"
        assert SkillManager._parse_frontmatter(p) is None


# ---------------------------------------------------------------------------
# _serialize_frontmatter
# ---------------------------------------------------------------------------

class TestSerializeFrontmatter:
    def test_basic(self):
        meta = {
            "name": "my-skill",
            "description": "Does things",
            "category": "workflow",
            "tags": ["tag1"],
            "triggers": ["trigger1"],
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
            "extra_field": "ignored",
        }
        result = SkillManager._serialize_frontmatter(meta)
        parsed = yaml.safe_load(result)
        assert parsed["name"] == "my-skill"
        assert parsed["description"] == "Does things"
        assert "extra_field" not in parsed

    def test_minimal_meta(self):
        """Only known keys are serialized."""
        result = SkillManager._serialize_frontmatter({"name": "only-name"})
        parsed = yaml.safe_load(result)
        assert parsed["name"] == "only-name"


# ---------------------------------------------------------------------------
# rebuild_index
# ---------------------------------------------------------------------------

class TestRebuildIndex:
    def test_rebuild_index_empty(self, manager: SkillManager):
        count = manager.rebuild_index()
        assert count == 0
        assert manager._index == {}

    def test_rebuild_index_with_skills(self, tmp_skills_dir: Path):
        _write_skill(tmp_skills_dir, "debugging", "skill-one", {
            "name": "Skill One",
            "description": "Desc one",
            "category": "debugging",
            "tags": ["tag1"],
            "triggers": ["t1"],
        }, "# Skill One\n\nBody")
        _write_skill(tmp_skills_dir, "workflow", "skill-two", {
            "name": "Skill Two",
            "description": "Desc two",
            "category": "workflow",
            "tags": [],
            "triggers": [],
        }, "# Skill Two\n\nBody")

        mgr = SkillManager(skills_dir=tmp_skills_dir)
        count = mgr.rebuild_index()
        assert count == 2
        assert "skill-one" in mgr._index
        assert mgr._index["skill-one"]["category"] == "debugging"
        assert "skill-two" in mgr._index
        assert mgr._index["skill-two"]["category"] == "workflow"

    def test_rebuild_index_skips_missing_skill_md(self, tmp_skills_dir: Path):
        """Directory without SKILL.md is skipped."""
        (tmp_skills_dir / "debugging" / "empty-skill").mkdir(parents=True, exist_ok=True)
        mgr = SkillManager(skills_dir=tmp_skills_dir)
        count = mgr.rebuild_index()
        assert count == 0

    def test_rebuild_index_skips_non_directories(self, tmp_skills_dir: Path):
        """Files in category dirs are skipped."""
        (tmp_skills_dir / "debugging" / "not-a-dir.txt").write_text("nope", encoding="utf-8")
        mgr = SkillManager(skills_dir=tmp_skills_dir)
        count = mgr.rebuild_index()
        assert count == 0


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

class TestCreate:
    def test_create_minimal(self, manager: SkillManager):
        result = manager.create(name="My Skill", body="# My Skill\n\nBody content")
        assert "skill_id" in result
        assert result["name"] == "My Skill"
        assert result["category"] == "workflow"

    def test_create_with_all_fields(self, manager: SkillManager):
        result = manager.create(
            name="Full Skill",
            body="# Full Skill\n\nThe body",
            category="debugging",
            tags=["tag1", "tag2"],
            triggers=["trigger1"],
            description="A full skill",
        )
        assert result["skill_id"] == "full-skill"
        assert result["category"] == "debugging"
        assert result["tags"] == ["tag1", "tag2"]
        assert result["triggers"] == ["trigger1"]
        assert result["description"] == "A full skill"

    def test_create_invalid_category(self, manager: SkillManager):
        with pytest.raises(ValueError, match="无效 category"):
            manager.create(name="Bad", body="Body", category="invalid")

    def test_create_file_exists(self, manager: SkillManager):
        manager.create(name="Duplicate", body="# Duplicate\n\nFirst")
        with pytest.raises(FileExistsError, match="已存在"):
            manager.create(name="Duplicate", body="# Duplicate\n\nSecond")

    def test_create_empty_slug(self, manager: SkillManager):
        """Slugify returns empty string for certain inputs."""
        with pytest.raises(ValueError, match="无法从 name"):
            manager.create(name="---", body="Body")

    def test_create_auto_description_from_body(self, manager: SkillManager):
        """When description is None, auto-extracted from first non-heading line."""
        result = manager.create(
            name="AutoDesc",
            body="# Title\n\nThis is the auto description line.\n\nMore content.",
        )
        assert result["description"] == "This is the auto description line."

    def test_create_auto_description_from_name(self, manager: SkillManager):
        """When body has no eligible line, name is used as description."""
        result = manager.create(name="NameOnly", body="# NameOnly\n# Section\n")
        assert result["description"] == "NameOnly"

    def test_create_updates_index(self, manager: SkillManager):
        manager.create(name="Indexed", body="# Indexed\n\nBody")
        assert "indexed" in manager._index

    def test_create_saves_index_file(self, manager: SkillManager):
        manager.create(name="Saved", body="# Saved\n\nBody")
        raw = json.loads(manager.index_file.read_text(encoding="utf-8"))
        assert "saved" in raw


# ---------------------------------------------------------------------------
# patch
# ---------------------------------------------------------------------------

class TestPatch:
    def test_patch_updates_existing(self, manager: SkillManager):
        manager.create(name="Existing", body="# Existing\n\nOld body", category="debugging")
        result = manager.patch(
            skill_id="existing",
            description="New description",
            tags=["new-tag"],
        )
        assert result["skill_id"] == "existing"
        assert result["description"] == "New description"
        assert result["tags"] == ["new-tag"]

    def test_patch_with_body(self, manager: SkillManager):
        manager.create(name="BodyPatch", body="# BodyPatch\n\nOld body", category="debugging")
        result = manager.patch(skill_id="bodypatch", body="# BodyPatch\n\nNew body")
        assert result["skill_id"] == "bodypatch"

        # Verify file content
        skill_path = manager._find_skill_path("bodypatch")
        content = skill_path.read_text(encoding="utf-8")
        assert "New body" in content

    def test_patch_nonexistent_creates(self, manager: SkillManager):
        """patch() on non-existent skill auto-creates it."""
        result = manager.patch(
            skill_id="brand-new",
            body="# Brand New\n\nCreated by patch",
            category="workflow",
            description="New skill",
        )
        assert result["skill_id"] == "brand-new"
        assert result["description"] == "New skill"

    def test_patch_nonexistent_no_body_raises(self, manager: SkillManager):
        with pytest.raises(ValueError, match="未提供 body"):
            manager.patch(skill_id="no-body", body=None)

    def test_patch_only_body_preserves_meta(self, manager: SkillManager):
        """patch with only body keeps existing frontmatter."""
        manager.create(
            name="Preserve",
            body="# Preserve\n\nOld",
            category="best-practices",
            tags=["keep-me"],
            description="Keep this",
        )
        result = manager.patch(skill_id="preserve", body="# Preserve\n\nNew")
        assert result["tags"] == ["keep-me"]
        assert result["description"] == "Keep this"

    def test_patch_updates_index(self, manager: SkillManager):
        manager.create(name="IdxPatch", body="# IdxPatch\n\nBody")
        manager.patch(skill_id="idxpatch", name="IdxPatch Renamed")
        assert manager._index["idxpatch"]["name"] == "IdxPatch Renamed"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_existing(self, manager: SkillManager):
        manager.create(name="ToDelete", body="# ToDelete\n\nBody")
        result = manager.delete("todelete")
        assert result is True
        assert "todelete" not in manager._index
        # Directory should be gone
        assert not (manager.skills_dir / "workflow" / "todelete").exists()

    def test_delete_nonexistent(self, manager: SkillManager):
        result = manager.delete("does-not-exist")
        assert result is False

    def test_delete_updates_index_file(self, manager: SkillManager):
        manager.create(name="IdxDel", body="# IdxDel\n\nBody")
        manager.delete("idxdel")
        raw = json.loads(manager.index_file.read_text(encoding="utf-8"))
        assert "idxdel" not in raw


# ---------------------------------------------------------------------------
# list_skills
# ---------------------------------------------------------------------------

class TestListSkills:
    def test_list_empty(self, manager: SkillManager):
        assert manager.list_skills() == []

    def test_list_all(self, manager: SkillManager):
        manager.create(name="A", body="# A\n\n", category="debugging")
        manager.create(name="B", body="# B\n\n", category="workflow")
        results = manager.list_skills()
        assert len(results) == 2

    def test_list_filter_category(self, manager: SkillManager):
        manager.create(name="A", body="# A\n\n", category="debugging")
        manager.create(name="B", body="# B\n\n", category="workflow")
        results = manager.list_skills(category="debugging")
        assert all(r["category"] == "debugging" for r in results)

    def test_list_filter_tag(self, manager: SkillManager):
        manager.create(name="A", body="# A\n\n", tags=["python"])
        manager.create(name="B", body="# B\n\n", tags=["rust"])
        results = manager.list_skills(tag="python")
        assert all("python" in r.get("tags", []) for r in results)

    def test_list_limit(self, manager: SkillManager):
        for i in range(10):
            manager.create(name=f"Skill{i}", body=f"# Skill{i}\n\n", category="workflow")
        results = manager.list_skills(limit=3)
        assert len(results) == 3

    def test_list_sorted_by_updated_at(self, manager: SkillManager):
        manager.create(name="First", body="# First\n\n")
        manager.create(name="Second", body="# Second\n\n")
        # Patch First to update its timestamp
        manager.patch(skill_id="first", body="# First\n\nUpdated")
        results = manager.list_skills()
        # "first" should be first since it was patched more recently
        assert results[0]["skill_id"] == "first"


# ---------------------------------------------------------------------------
# get_skill
# ---------------------------------------------------------------------------

class TestGetSkill:
    def test_get_skill_not_found(self, manager: SkillManager):
        assert manager.get_skill("does-not-exist") is None

    def test_get_skill_without_body(self, manager: SkillManager):
        manager.create(name="NoBody", body="# NoBody\n\nBody text", description="Desc")
        result = manager.get_skill("nobody")
        assert result["skill_id"] == "nobody"
        assert "body" not in result

    def test_get_skill_with_body(self, manager: SkillManager):
        manager.create(name="WithBody", body="# WithBody\n\nThe body content")
        result = manager.get_skill("withbody", include_body=True)
        assert result["body"] == "# WithBody\n\nThe body content"

    def test_get_skill_with_body_file_missing(self, manager: SkillManager):
        """get_skill with include_body returns empty body if file is gone."""
        # Manually add to index without creating file
        manager._index["orphan"] = {
            "name": "Orphan",
            "description": "",
            "category": "workflow",
            "tags": [],
            "triggers": [],
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
            "path": str(manager.skills_dir / "workflow" / "orphan" / "SKILL.md"),
        }
        result = manager.get_skill("orphan", include_body=True)
        assert result["body"] == ""


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_basic(self, manager: SkillManager):
        manager.create(name="PyTest Skill", body="# PyTest\n\nPython testing",
                        description="Run pytest", tags=["pytest", "python"])
        results = manager.search("pytest")
        assert len(results) >= 1
        assert any("pytest" in r.get("name", "").lower() for r in results)

    def test_search_multiple_terms(self, manager: SkillManager):
        manager.create(name="PyUnit", body="# PyUnit\n\n",
                        description="Python unit testing", tags=["python", "unittest"])
        results = manager.search("python unittest")
        assert len(results) >= 1

    def test_search_no_match(self, manager: SkillManager):
        manager.create(name="Rust Skill", body="# Rust\n\n")
        results = manager.search("python")
        assert len(results) == 0

    def test_search_filter_category(self, manager: SkillManager):
        manager.create(name="Dbg", body="# Dbg\n\n", category="debugging")
        manager.create(name="Wkf", body="# Wkf\n\n", category="workflow")
        results = manager.search("Dbg", category="workflow")
        assert all(r["category"] == "workflow" for r in results)

    def test_search_filter_tags(self, manager: SkillManager):
        manager.create(name="Skill1", body="# Skill1\n\n", tags=["backend"])
        manager.create(name="Skill2", body="# Skill2\n\n", tags=["frontend"])
        results = manager.search("skill", tags=["backend"])
        assert all("backend" in r.get("tags", []) for r in results)

    def test_search_limit(self, manager: SkillManager):
        for i in range(10):
            manager.create(name=f"Search{i}", body=f"# Search{i}\n\n", tags=["match"])
        results = manager.search("search", limit=3)
        assert len(results) == 3

    def test_search_scoring(self, manager: SkillManager):
        """Name matches score higher than description matches."""
        manager.create(name="exact-match", body="# Exact\n\nOther stuff")
        manager.create(name="partial", body="# Exact\n\nOther stuff")
        results = manager.search("exact")
        # exact-match should come first (name match = 3pts, description match = 1pt)
        assert results[0]["name"] == "exact-match"


# ---------------------------------------------------------------------------
# _find_skill_path
# ---------------------------------------------------------------------------

class TestFindSkillPath:
    def test_find_existing(self, manager: SkillManager):
        manager.create(name="FindMe", body="# FindMe\n\n", category="debugging")
        path = manager._find_skill_path("findme")
        assert path is not None
        assert path.name == "SKILL.md"

    def test_find_not_existing(self, manager: SkillManager):
        path = manager._find_skill_path("does-not-exist")
        assert path is None


# ---------------------------------------------------------------------------
# get_skill_inventory
# ---------------------------------------------------------------------------

class TestGetSkillInventory:
    def test_inventory_empty(self, manager: SkillManager):
        result = manager.get_skill_inventory(max_tokens=100)
        assert "[0 Skills]" in result

    def test_inventory_single_skill(self, manager: SkillManager):
        manager.create(name="InvSkill", body="# InvSkill\n\n",
                       description="An inventory skill")
        result = manager.get_skill_inventory(max_tokens=500)
        assert "invskill" in result
        assert "An inventory skill" in result

    def test_inventory_respects_max_tokens(self, manager: SkillManager):
        """With a very low token budget, not all skills are listed."""
        for i in range(5):
            manager.create(
                name=f"Large{i}",
                body="# Large\n\n" + "x" * 100,
                description="A very long description " + "x" * 50,
            )
        result = manager.get_skill_inventory(max_tokens=30)
        # Should show header
        assert "[5 Skills]" in result

    def test_inventory_truncated_message(self, manager: SkillManager):
        """When some skills are omitted, ... (+N more) is appended."""
        for i in range(3):
            manager.create(
                name=f"Trunc{i}",
                body=f"# Trunc{i}\n\n",
                description=f"Description {i}",
            )
        # Very small budget — only header fits
        result = manager.get_skill_inventory(max_tokens=10)
        assert "[3 Skills]" in result

    def test_inventory_tiktoken_available(self, manager: SkillManager):
        """When tiktoken is available, it is used instead of fallback."""
        manager.create(name="TkSkill", body="# Tk\n\n", description="With tiktoken")
        mock_enc = MagicMock()
        mock_enc.encode.side_effect = lambda x: [1] * len(x)
        mock_tk_module = MagicMock()
        mock_tk_module.get_encoding.return_value = mock_enc
        with patch.dict("sys.modules", {"tiktoken": mock_tk_module}):
            with patch("src.memory.skill_manager._HAS_TIKTOKEN", True):
                result = manager.get_skill_inventory(max_tokens=500)
                assert "tkskill" in result

    def test_inventory_tiktoken_fallback_on_error(self, manager: SkillManager):
        """If tiktoken.get_encoding raises, fall back to char-based estimation."""
        manager.create(name="FbSkill", body="# Fb\n\n", description="Fallback skill")
        mock_tk_module = MagicMock()
        mock_tk_module.get_encoding.side_effect = RuntimeError("no encoding")
        with patch.dict("sys.modules", {"tiktoken": mock_tk_module}):
            with patch("src.memory.skill_manager._HAS_TIKTOKEN", True):
                result = manager.get_skill_inventory(max_tokens=500)
                assert "fbskill" in result


# ---------------------------------------------------------------------------
# evaluate_skill_worthy
# ---------------------------------------------------------------------------

class TestEvaluateSkillWorthy:
    def test_tool_call_threshold_met(self):
        assert SkillManager.evaluate_skill_worthy(
            tool_call_count=5, had_error=False, had_fix=False,
            had_user_correction=False, is_nontrivial_workflow=False,
        ) is True

    def test_tool_call_threshold_not_met(self):
        assert SkillManager.evaluate_skill_worthy(
            tool_call_count=4, had_error=False, had_fix=False,
            had_user_correction=False, is_nontrivial_workflow=False,
        ) is False

    def test_error_fixed(self):
        assert SkillManager.evaluate_skill_worthy(
            tool_call_count=2, had_error=True, had_fix=True,
            had_user_correction=False, is_nontrivial_workflow=False,
        ) is True

    def test_error_without_fix(self):
        assert SkillManager.evaluate_skill_worthy(
            tool_call_count=2, had_error=True, had_fix=False,
            had_user_correction=False, is_nontrivial_workflow=False,
        ) is False

    def test_user_correction(self):
        assert SkillManager.evaluate_skill_worthy(
            tool_call_count=1, had_error=False, had_fix=False,
            had_user_correction=True, is_nontrivial_workflow=False,
        ) is True

    def test_nontrivial_workflow(self):
        assert SkillManager.evaluate_skill_worthy(
            tool_call_count=1, had_error=False, had_fix=False,
            had_user_correction=False, is_nontrivial_workflow=True,
        ) is True

    def test_no_trigger(self):
        assert SkillManager.evaluate_skill_worthy(
            tool_call_count=1, had_error=False, had_fix=False,
            had_user_correction=False, is_nontrivial_workflow=False,
        ) is False


# ---------------------------------------------------------------------------
# build_skill_from_execution
# ---------------------------------------------------------------------------

class TestBuildSkillFromExecution:
    def test_basic(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="agent",
            task_description="Fix database timeout",
            workflow_name="debug",
            final_result="Fixed by adding index",
        )
        assert "skill_id" not in result  # name is skill_id
        assert "name" in result
        assert "body" in result
        assert "category" in result
        assert "tags" in result
        assert "triggers" in result
        assert "description" in result

    def test_error_context_sets_debugging_category(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="debugger",
            task_description="Fix error in pipeline",
            workflow_name="fix",
            final_result="Pipeline fixed",
            error_context="Connection refused",
        )
        assert result["category"] == "debugging"

    def test_workflow_build_sets_workflow_category(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="builder",
            task_description="Build the project",
            workflow_name="build",
            final_result="Built successfully",
        )
        assert result["category"] == "workflow"

    def test_workflow_refactor_sets_workflow_category(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="refactorer",
            task_description="Refactor legacy code",
            workflow_name="refactor",
            final_result="Code refactored",
        )
        assert result["category"] == "workflow"

    def test_workflow_test_sets_workflow_category(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="tester",
            task_description="Run tests",
            workflow_name="test",
            final_result="Tests passed",
        )
        assert result["category"] == "workflow"

    def test_key_steps_included(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="agent",
            task_description="Deploy application",
            workflow_name="deploy",
            final_result="Deployed",
            key_steps=["Step 1", "Step 2"],
        )
        assert "Step 1" in result["body"]
        assert "Step 2" in result["body"]

    def test_error_context_appended_to_body(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="agent",
            task_description="Handle error",
            workflow_name="fix",
            final_result="Handled",
            error_context="NullPointerException",
        )
        assert "NullPointerException" in result["body"]

    def test_triggers_filter_common_words(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="agent",
            task_description="the and for with from database error",
            workflow_name="fix",
            final_result="Fixed",
        )
        # Common words (len<3 or stopwords) should be filtered out of triggers
        assert "the" not in result["triggers"]
        assert "and" not in result["triggers"]

    def test_triggers_max_5(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="agent",
            task_description="python docker kubernetes redis postgres nginx",
            workflow_name="deploy",
            final_result="Done",
        )
        assert len(result["triggers"]) <= 5

    def test_name_truncated_to_48(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="a" * 50,
            task_description="x",
            workflow_name="w" * 50,
            final_result="r",
        )
        assert len(result["name"]) <= 48

    def test_tags_include_workflow_and_agent(self):
        result = SkillManager.build_skill_from_execution(
            agent_name="builder",
            task_description="Build a thing",
            workflow_name="build",
            final_result="Built",
        )
        assert "build" in result["tags"]
        assert "builder" in result["tags"]
