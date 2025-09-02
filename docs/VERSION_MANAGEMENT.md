# Version Management Guide

## Overview
When creating a new version or release for OpenAI Conversation Plus, multiple files need to be updated with the new version number.

## Files That Need Version Updates

When releasing a new version, update the version number in these files:

1. **`custom_components/openai_conversation_plus/manifest.json`**
   - Key: `"version"`
   - Format: `"YYYY.M.D.B"` (Year.Month.Day.Build)
   - Example: `"2025.9.2.1"`

2. **`setup.py`**
   - Key: `version=`
   - Format: Same as manifest.json
   - Example: `version="2025.9.2.1"`

3. **`hacs.json`** (optional but recommended)
   - Key: `"homeassistant"`
   - Format: Minimum Home Assistant version required
   - Example: `"2025.8.1"`
   - Note: This is NOT the component version, but the minimum HA version

## Version Format

We use a date-based versioning scheme:
- **YYYY**: Year (4 digits)
- **M**: Month (1-2 digits, no leading zero)
- **D**: Day (1-2 digits, no leading zero)
- **B**: Build number for that day (starts at 1)

Examples:
- `2025.9.2.1` - First release on September 2, 2025
- `2025.9.2.2` - Second release on September 2, 2025
- `2025.10.15.1` - First release on October 15, 2025

## Release Checklist

When creating a new release:

1. **Update version numbers**:
   ```bash
   # Update manifest.json
   # Update setup.py
   # Optionally update hacs.json if minimum HA version changes
   ```

2. **Commit changes**:
   ```bash
   git add custom_components/openai_conversation_plus/manifest.json setup.py
   git commit -m "Bump version to YYYY.M.D.B"
   ```

3. **Push to dev branch**:
   ```bash
   git push origin dev
   ```

4. **Merge to main**:
   ```bash
   git checkout main
   git merge dev
   git push origin main
   ```

5. **Create GitHub release**:
   ```bash
   git tag vYYYY.M.D.B
   git push origin vYYYY.M.D.B
   ```

## Automated Version Update Script

You can create a script to update all version files at once:

```bash
#!/bin/bash
NEW_VERSION="$1"

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: ./update_version.sh YYYY.M.D.B"
    exit 1
fi

# Update manifest.json
sed -i '' "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" custom_components/openai_conversation_plus/manifest.json

# Update setup.py
sed -i '' "s/version=\".*\"/version=\"$NEW_VERSION\"/" setup.py

echo "Version updated to $NEW_VERSION in all files"
```

## Important Notes

- Always keep version numbers synchronized across all files
- The version in `hacs.json` is for minimum Home Assistant version, not the component version
- Use semantic versioning for clarity and consistency
- Test thoroughly before releasing a new version
- Document changes in a CHANGELOG or release notes
