# Task Summary: AI Coding Tool UI Research

**Task:** Research 8 AI coding tools' desktop/terminal UI design
**Completed:** 2026-04-21
**Output:**  (574 lines)

## What was researched

8 products analyzed across 5 dimensions (layout, visual style, key interactions, desktop-specific features, pros/cons):

1. **OpenCode → Crush** (Go/Bubble Tea TUI, primary reference)
2. **Cursor** (VS Code fork, AI editor benchmark)
3. **Windsurf** (VS Code fork, Cascade/Memories concept)
4. **Claude Code** (CLI + 5 runtimes, permission security)
5. **Aider** (CLI no-TUI, git integration)
6. **Cline** (VS Code extension, diff+permission UX)
7. **Roo Code** (Cline fork, multi-mode UX)
8. **Crush** (OpenCode successor, same TUI design)

## Key findings

- **Two main UI paradigms:** IDE-embedded (Cursor/Windsurf/Cline/Roo Code) vs Terminal TUI (OpenCode/Crush/Aider/Claude Code CLI)
- **OpenCode/Crush:** Best TUI design language (Bubble Tea, Charm style), Agent Skills ecosystem, Vim+VS Code hybrid shortcuts
- **Cursor:** Invented Cmd+K/Cmd+L dual-entry pattern, best codebase indexing
- **Windsurf:** Memories (persistent context), Flow Actions (task decomposition)
- **Cline:** Permission security + diff visualization best practices

## Key recommendations for Oh My Coder Desktop (prioritized)

### P0 (Must-have)
1. Adopt Bubble Tea TUI design language (Charm aesthetic)
2. Implement Cmd+K (inline) + Cmd+L (sidebar) dual-entry pattern (Cursor)
3. Add Memories/persistent context mechanism (Windsurf)

### P1 (Important)
1. Vim mode + traditional input mode coexistence (OpenCode)
2. Diff visualization + permission confirm (Cline)
3. MCP integration + provider switching panel (Crush/Windsurf)

### P2 (Enhancement)
1. Agent Skills support (.skills/ directory)
2. Session/Project management panel
3. Mode switching (Code/Architect/Ask/Debug)
4. Token/cost real-time tracking (Cline)

## Data sources
- GitHub README docs (opencode-ai/opencode, charmbracelet/crush, cline/cline, RooCodeInc/Roo-Code, Aider-AI/aider)
- Official docs (opencode.ai, cursor.com, windsurf.com, docs.anthropic.com)
- Chinese tech blogs (CSDN, 博客园) for UI screenshots and reviews
