#!/bin/bash
# Script to update version numbers across all relevant files

NEW_VERSION="$1"

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: ./scripts/update_version.sh YYYY.M.D.B"
    echo "Example: ./scripts/update_version.sh 2025.9.2.1"
    exit 1
fi

echo "🔄 Updating version to $NEW_VERSION..."

# Update manifest.json
if [ -f "custom_components/openai_conversation_plus/manifest.json" ]; then
    sed -i '' "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" custom_components/openai_conversation_plus/manifest.json
    echo "✅ Updated manifest.json"
else
    echo "❌ manifest.json not found"
fi

# Update setup.py
if [ -f "setup.py" ]; then
    sed -i '' "s/version=\".*\"/version=\"$NEW_VERSION\"/" setup.py
    echo "✅ Updated setup.py"
else
    echo "❌ setup.py not found"
fi

echo ""
echo "📋 Version update complete! Files updated:"
echo "  - custom_components/openai_conversation_plus/manifest.json"
echo "  - setup.py"
echo ""
echo "Next steps:"
echo "  1. git add -A"
echo "  2. git commit -m 'Bump version to $NEW_VERSION'"
echo "  3. git push origin dev"
echo "  4. Merge to main when ready"
echo "  5. Create release: git tag v$NEW_VERSION && git push origin v$NEW_VERSION"
