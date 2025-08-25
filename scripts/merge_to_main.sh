#!/bin/bash
# Script to merge dev branch to main while keeping only Home Assistant integration files

set -e

echo "🚀 Merging dev to main (keeping only HA integration files)..."

# Ensure we're on dev branch
if [[ $(git branch --show-current) != "dev" ]]; then
    echo "❌ Error: Must be on dev branch to merge"
    echo "Current branch: $(git branch --show-current)"
    exit 1
fi

# Check if working directory is clean
if [[ -n $(git status --porcelain) ]]; then
    echo "❌ Error: Working directory is not clean"
    echo "Please commit or stash your changes first"
    git status --short
    exit 1
fi

# Create a temporary branch for the merge
TEMP_BRANCH="temp-merge-$(date +%s)"
echo "📝 Creating temporary branch: $TEMP_BRANCH"

# Switch to main and create temp branch
git checkout main
git checkout -b "$TEMP_BRANCH"

# Merge dev into temp branch
echo "🔄 Merging dev into temporary branch..."
git merge dev --no-edit

# Remove development files from the merge
echo "🧹 Removing development files from main branch..."

# Files to remove (development only)
DEV_FILES=(
    # Development documentation
    "ai_agent_task_list.md"
    "agent.md"
    "README_TESTING.md"
    "SETUP_COMPLETE.md"
    "TROUBLESHOOTING.md"
    "QUICK_FIX.md"

    # Development scripts and configs
    "scripts/"
    "tests/"
    "requirements_test.txt"
    "pytest.ini"
    "pyproject.toml"
    "setup.py"
    "Makefile"
    ".pre-commit-config.yaml"
    "safari-fix.js"
    "frontend_dev_setup.sh"

    # Development workflows
    ".github/"

    # Development environment
    "venv_test/"
    ".pytest_cache/"
    ".mypy_cache/"
    ".ruff_cache/"
    "htmlcov/"
    "coverage.xml"
    ".coverage"
)

# Remove each development file/directory
for file in "${DEV_FILES[@]}"; do
    if [[ -e "$file" ]]; then
        echo "🗑️  Removing: $file"
        git rm -rf "$file" 2>/dev/null || true
    fi
done

# Commit the removal
if [[ -n $(git status --porcelain) ]]; then
    echo "💾 Committing development file removal..."
    git commit -m "Clean main branch for Home Assistant integration

Removed development files to keep only essential integration files:
- Development documentation (ai_agent_task_list.md, agent.md, etc.)
- Testing framework (tests/, pytest.ini, requirements_test.txt)
- Development tools (scripts/, Makefile, .pre-commit-config.yaml)
- CI/CD workflows (.github/)
- Development environment files (venv_test/, cache files)

These files remain in dev branch for development purposes.
Main branch now contains only the essential Home Assistant integration files."
fi

# Switch back to main
git checkout main

# Merge temp branch into main
echo "🔄 Merging temporary branch to main..."
git merge "$TEMP_BRANCH" --no-edit

# Delete temporary branch
echo "🧹 Cleaning up temporary branch..."
git branch -D "$TEMP_BRANCH"

# Push to origin
echo "📤 Pushing to origin/main..."
git push origin main

echo "✅ Successfully merged dev to main (only HA integration files kept)"
echo ""
echo "📋 Summary:"
echo "- Dev branch changes merged to main"
echo "- Development files excluded from main branch"
echo "- Main branch now contains only essential integration files"
echo ""
echo "📁 Files kept in main:"
echo "  - __init__.py (core integration)"
echo "  - const.py (constants)"
echo "  - config_flow.py (configuration)"
echo "  - services.py (services)"
echo "  - helpers.py (helper functions)"
echo "  - exceptions.py (custom exceptions)"
echo "  - entity.py (entity base class)"
echo "  - ai_task.py (AI task platform)"
echo "  - manifest.json (integration manifest)"
echo "  - strings.json (UI strings)"
echo "  - translations/ (localization)"
echo "  - README.md (user documentation)"
echo ""
echo "🔄 To continue development:"
echo "  git checkout dev"
