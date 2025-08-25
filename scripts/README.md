# Development Scripts

This folder contains development and utility scripts for the OpenAI Conversation Plus project.

## Scripts

### `merge_to_main.sh`
**Purpose**: Merges the `dev` branch into `main` while keeping only Home Assistant integration files.

**What it does**:
- Creates a temporary branch for the merge
- Merges `dev` into the temporary branch
- Removes development-only files (documentation, tests, scripts, etc.)
- Commits the cleaned version to `main`
- Keeps only essential integration files

**Usage**:
```bash
./scripts/merge_to_main.sh
```

**Files removed from main**:
- Development documentation (ai_agent_task_list.md, agent.md, etc.)
- Testing framework (tests/, pytest.ini, requirements_test.txt)
- Development tools (scripts/, Makefile, .pre-commit-config.yaml)
- CI/CD workflows (.github/)
- Development environment files (venv_test/, cache files)

### `show_main_files.sh`
**Purpose**: Shows what files will be kept in the `main` branch after cleaning.

**What it shows**:
- Core integration files that will remain
- Configuration files that will remain
- User documentation that will remain
- Development files that will be removed

**Usage**:
```bash
./scripts/show_main_files.sh
```

## When to Use

- **`show_main_files.sh`**: Before merging to see what will be kept/removed
- **`merge_to_main.sh`**: When ready to create a clean release in main branch

## Important Notes

- These scripts should only be run from the `dev` branch
- The `main` branch will always contain only the essential Home Assistant integration files
- Development files remain available in the `dev` branch
- Always review the changes before pushing to main

## Workflow

1. Develop in `dev` branch
2. Run `show_main_files.sh` to review what will be kept
3. Run `merge_to_main.sh` when ready to release
4. Push `main` branch to create a clean release
5. Continue development in `dev` branch
