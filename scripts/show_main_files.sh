#!/bin/bash
# Script to show what files will be kept in main branch

echo "📁 Files that will be kept in main branch (Home Assistant integration):"
echo "=================================================================="
echo ""

# Core integration files
echo "🔧 Core Integration Files:"
echo "  __init__.py          - Main integration logic"
echo "  const.py             - Constants and configuration"
echo "  config_flow.py       - Configuration flow"
echo "  services.py          - Custom services"
echo "  helpers.py           - Helper functions"
echo "  exceptions.py        - Custom exceptions"
echo "  entity.py            - Entity base class"
echo "  ai_task.py           - AI task platform"
echo ""

# Configuration files
echo "⚙️  Configuration Files:"
echo "  manifest.json        - Integration manifest"
echo "  strings.json         - UI strings"
echo "  translations/        - Localization files"
echo ""

# Documentation
echo "📚 User Documentation:"
echo "  README.md            - User guide and installation"
echo ""

# Files that will be removed from main
echo "🗑️  Files that will be removed from main (development only):"
echo "=================================================================="
echo ""

echo "📝 Development Documentation:"
echo "  ai_agent_task_list.md"
echo "  agent.md"
echo "  README_TESTING.md"
echo "  SETUP_COMPLETE.md"
echo "  TROUBLESHOOTING.md"
echo "  QUICK_FIX.md"
echo ""

echo "🧪 Testing Framework:"
echo "  tests/"
echo "  requirements_test.txt"
echo "  pytest.ini"
echo "  pyproject.toml"
echo "  setup.py"
echo ""

echo "🛠️  Development Tools:"
echo "  scripts/"
echo "  Makefile"
echo "  .pre-commit-config.yaml"
echo "  .github/"
echo ""

echo "🌐 Development Utilities:"
echo "  safari-fix.js"
echo "  frontend_dev_setup.sh"
echo ""

echo "💡 To merge dev to main (keeping only integration files):"
echo "  ./scripts/merge_to_main.sh"
echo ""
echo "💡 To continue development:"
echo "  git checkout dev"
