# Skill Registry — zanovix-crm

**Project**: zanovix-crm
**Generated**: 2026-05-01
**Status**: bootstrap (greenfield)

## Project Conventions

None yet — greenfield repo. Stack and conventions will be inherited from msi-a template clone (see `sdd-init/zanovix-crm` engram observation).

## User Skills (auto-loaded by trigger)

| Skill | Trigger | Path |
|-------|---------|------|
| chatwoot-api | Chatwoot integration work | ~/.claude/skills/chatwoot-api/SKILL.md |
| go-testing | Go tests, Bubbletea TUI testing | ~/.claude/skills/go-testing/SKILL.md |
| graphify | `/graphify` — input to knowledge graph | ~/.claude/skills/graphify/SKILL.md |
| skill-creator | Creating new AI skills | ~/.claude/skills/skill-creator/SKILL.md |
| issue-creation | GitHub issue creation flow | ~/.claude/skills/issue-creation/SKILL.md |
| branch-pr | Branch + PR workflow | ~/.claude/skills/branch-pr/SKILL.md |
| framework-selection | Choosing frameworks/libs | ~/.claude/skills/framework-selection/SKILL.md |
| judgment-day | Conflict resolution / mem_judge | ~/.claude/skills/judgment-day/SKILL.md |

## Compact Rules (auto-resolved)

### Global rules (from ~/.claude/CLAUDE.md)
- Use bat/rg/fd/sd/eza, never cat/grep/find/sed/ls
- Never add Co-Authored-By to commits — conventional commits only
- Never build after changes
- Engram mem_save proactively after decisions/bugfixes/discoveries
- mem_session_summary mandatory before "done"

### SDD rules (this project)
- Persistence backend: **engram** (no openspec/ directory)
- Mode: **interactive** — pause between phases for user review
- Strict TDD Mode: **disabled** until test runner present (re-run sdd-init after msi-a clone)

## Refresh

Re-run `/sdd-init` after:
- Cloning msi-a template (will detect Python 3.11 / FastAPI / pytest stack)
- Adding new skills to the project
