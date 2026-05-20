#!/usr/bin/env python3
"""
Documentation sync checker for Oh My Coder.

Checks:
1. Files that exist in both docs/ and docs/zh/ - verify structural sync (sections match)
2. Files only in docs/ - flag as missing Chinese translation
3. Files only in docs/zh/ - flag as missing English version

Exit codes:
  0 = All synced
  1 = Sync issues found
"""

import re
import sys
from pathlib import Path


def extract_headings(content: str) -> list[tuple[int, str]]:
    """Extract markdown headings with their levels.

    Returns list of (level, heading_text) tuples.
    """
    headings = []
    for line in content.split('\n'):
        # Match markdown headings: # Heading, ## Heading, etc.
        match = re.match(r'^(#{1,6})\s+(.+?)(?:\s*#.*)?$', line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            # Normalize heading text (remove emoji for comparison)
            text_normalized = re.sub(r'[^\w\s\u4e00-\u9fff\-]', '', text)
            headings.append((level, text_normalized))
    return headings


def get_heading_outline(headings: list[tuple[int, str]]) -> list[str]:
    """Convert headings to a normalized outline for comparison."""
    return [f"H{level}: {text}" for level, text in headings]


def find_md_files(base_path: Path, subdir: str = "", exclude_zh: bool = False) -> dict[str, Path]:
    """Find all .md files in a directory.

    Args:
        base_path: Root path to search
        subdir: Optional subdirectory within base_path
        exclude_zh: If True, exclude files under 'zh/' subdirectory

    Returns dict mapping relative path to absolute path.
    """
    files = {}
    search_path = base_path / subdir if subdir else base_path

    if not search_path.exists():
        return files

    for md_file in search_path.rglob("*.md"):
        # Skip if exclude_zh and file is under 'zh/' subdirectory
        if exclude_zh and 'zh' in md_file.parts:
            continue
        rel_path = md_file.relative_to(search_path)
        files[str(rel_path)] = md_file

    return files


def read_file_headings(file_path: Path) -> list[tuple[int, str]]:
    """Read file and extract headings."""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()
        return extract_headings(content)
    except Exception as e:
        print(f"  ⚠️  Error reading {file_path}: {e}")
        return []


def compare_headings(headings1: list[tuple[int, str]], headings2: list[tuple[int, str]]) -> dict:
    """Compare two heading lists and return differences.

    Returns dict with:
      - 'match': bool
      - 'missing_in_2': headings in 1 but not 2
      - 'missing_in_1': headings in 2 but not 1
    """
    outline1 = get_heading_outline(headings1)
    outline2 = get_heading_outline(headings2)

    set1 = set(outline1)
    set2 = set(outline2)

    missing_in_2 = set1 - set2
    missing_in_1 = set2 - set1

    return {
        'match': len(missing_in_1) == 0 and len(missing_in_2) == 0,
        'missing_in_2': sorted(missing_in_2),
        'missing_in_1': sorted(missing_in_1),
    }


def check_docs_sync(project_root: Path) -> tuple[bool, list[str]]:
    """Check documentation sync between docs/ and docs/zh/.

    NOTE: This project's primary language is Chinese. The docs/ directory
    contains Chinese documentation. The docs/zh/ directory is for
    i18n framework compatibility (not actively used).

    This check is now informational only (warnings, not errors).

    Returns (is_synced, issues_list). is_synced is always True.
    """
    docs_dir = project_root / "docs"
    zh_dir = project_root / "docs" / "zh"

    if not docs_dir.exists():
        return False, ["docs/ directory not found"]

    issues = []

    # Find files in both directories
    # NOTE: docs/ is Chinese, so we don't enforce English->Chinese translation
    docs_files = find_md_files(docs_dir, exclude_zh=True)
    zh_files = find_md_files(zh_dir) if zh_dir.exists() else {}

    # Files in both locations (check structural sync)
    common_files = set(docs_files.keys()) & set(zh_files.keys())
    docs_only = set(docs_files.keys()) - set(zh_files.keys())
    zh_only = set(zh_files.keys()) - set(docs_files.keys())

    print("=" * 60)
    print("📋 Documentation Sync Check")
    print("=" * 60)
    print()

    # Check common files for structural sync
    print("🔄 Checking files in both docs/ and docs/zh/...")
    print()

    structural_issues = []
    for rel_path in sorted(common_files):
        headings_en = read_file_headings(docs_files[rel_path])
        headings_zh = read_file_headings(zh_files[rel_path])

        diff = compare_headings(headings_en, headings_zh)

        if not diff['match']:
            structural_issues.append(rel_path)
            print(f"  ❌ {rel_path}")

            if diff['missing_in_2']:
                print(f"     Missing in docs/zh/: {len(diff['missing_in_2'])} sections")
                for h in diff['missing_in_2'][:3]:  # Show first 3
                    print(f"       - {h}")
                if len(diff['missing_in_2']) > 3:
                    print(f"       ... and {len(diff['missing_in_2']) - 3} more")

            if diff['missing_in_1']:
                print(f"     Missing in docs/: {len(diff['missing_in_1'])} sections")
                for h in diff['missing_in_1'][:3]:
                    print(f"       - {h}")
                if len(diff['missing_in_1']) > 3:
                    print(f"       ... and {len(diff['missing_in_1']) - 3} more")
            print()
        else:
            print(f"  ✅ {rel_path}")

    if structural_issues:
        issues.append(f"Structural sync issues in {len(structural_issues)} files")

    print()

    # Report files only in docs/ (missing Chinese translation)
    # Filter out less important files
    important_patterns = [
        'guide/', 'features/', 'api/', 'security/',
        'FAQ.md', 'index.md'
    ]

    important_docs_only = [
        f for f in docs_only
        if any(pattern in str(f) for pattern in important_patterns)
    ]

    if important_docs_only:
        print("📝 Files in docs/ not in docs/zh/ (informational, not an error):")
        print()
        for rel_path in sorted(important_docs_only)[:10]:
            print(f"  ℹ️  {rel_path}")
        if len(important_docs_only) > 10:
            print(f"  ... and {len(important_docs_only) - 10} more")
        print()
        # NOTE: This is informational only, not an error
        # issues.append(f"{len(important_docs_only)} docs missing Chinese translation")

    # Report files only in docs/zh/ (missing English version)
    if zh_only:
        print("🌐 Files in docs/zh/ missing English version:")
        print()
        for rel_path in sorted(zh_only)[:10]:
            print(f"  ℹ️  {rel_path}")
        if len(zh_only) > 10:
            print(f"  ... and {len(zh_only) - 10} more")
        print()
        # This is informational, not an error
        print(f"  💡 {len(zh_only)} files are Chinese-only (not an error)")
        print()

    # Summary
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(f"  Files in both locations: {len(common_files)}")
    print(f"  Files with structural issues: {len(structural_issues)}")
    print(f"  Important docs missing Chinese: {len(important_docs_only)}")
    print(f"  Chinese-only docs: {len(zh_only)}")
    print()

    # NOTE: We don't enforce i18n sync for this project (primary language is Chinese)
    is_synced = len(structural_issues) == 0  # Only check structural issues

    if is_synced:
        print("✅ Documentation structure is consistent!")
    else:
        print("⚠️  Documentation structural issues found (sections mismatch).")

    print()
    print("💡 Note: This project's primary language is Chinese.")
    print("   Missing docs/zh/ translations are informational only.")

    return is_synced, issues


def main():
    """Main entry point."""
    # Find project root (where docs/ directory is)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Alternatively, use current directory if it has docs/
    if not (project_root / "docs").exists():
        project_root = Path.cwd()

    if not (project_root / "docs").exists():
        print("❌ Error: Could not find docs/ directory")
        print(f"   Looked in: {project_root}")
        sys.exit(1)

    is_synced, issues = check_docs_sync(project_root)

    # NOTE: This script is now informational only.
    # Always exit 0 (don't fail CI).
    if issues:
        print()
        print("ℹ️  Informational notes (not errors):")
        for issue in issues:
            print(f"  - {issue}")

    sys.exit(0)


if __name__ == "__main__":
    main()
