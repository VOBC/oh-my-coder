# Changelog

All notable changes to this project will be documented in this file.


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Documentation Updates
- Update README coverage badge: 87% → 96% (2026-08-16)

---

## [0.2.1] - 2026-08-01

### Fixed
- Fix mypy type errors in cli.py (commit 1dbc576)
- Fix `leave_team` returns False when user is not a member of any team (commit e14ab6c)
- Replace deprecated Pydantic class Config with model_config (commit 119fab9)

### Changed / Refactored
- Add return type annotations to cli_cost.py (commit 0690d4f)
- Add type hints to server_api.py public functions (commit 8be0542)

### Documentation Updates
- Add docstrings to cli.py public functions (commit 12938f8)

