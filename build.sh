#!/bin/bash

# Ensure we are in the project root
cd "$(dirname "$0")"

# Define variables
PROJECT_DIR=$(pwd)
DIST_DIR="$PROJECT_DIR/dist"
DATE_SUFFIX=$(date +%Y%m%d)
SKILL_NAME="mail-skill"

# Create dist directory if it doesn't exist
mkdir -p "$DIST_DIR"

# Clean up any existing packages with the same name/date
rm -f "$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.skill"
rm -f "$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.zip"

echo "Packaging skill into dist directory..."

# Create a clean temp directory for building the .skill file to avoid including .env
BUILD_TEMP=$(mktemp -d)
cp -r "$PROJECT_DIR"/* "$BUILD_TEMP/"
cp "$PROJECT_DIR/.gitignore" "$BUILD_TEMP/" 2>/dev/null || true
rm -f "$BUILD_TEMP/.env"
rm -f "$BUILD_TEMP/163邮箱故障排查指南.md"
rm -f "$BUILD_TEMP/idea.md"
rm -rf "$BUILD_TEMP/dist"
rm -rf "$BUILD_TEMP/mail_data"

# 1. Package the .skill file using the skill-creator script from the clean temp dir
python /Users/wuliang/.trae/skills/skill-creator/scripts/package_skill.py "$BUILD_TEMP" "$DIST_DIR"

# Clean up build temp
rm -rf "$BUILD_TEMP"

# Check if the .skill file was created successfully (it will be named after the temp dir name, so we need to find it)
SKILL_FILE=$(find "$DIST_DIR" -name "*.skill" | head -n 1)
if [ -n "$SKILL_FILE" ]; then
    # Rename it to include the date suffix
    mv "$SKILL_FILE" "$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.skill"
    echo "✅ Successfully created $DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.skill"
else
    echo "❌ Failed to create .skill file"
    exit 1
fi

# 2. Package the project into a .zip file
# We'll create a temporary directory to structure the zip file properly
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/$SKILL_NAME"

# Copy files to temp dir, excluding unnecessary ones
cp -r SKILL.md README.md scripts references assets requirements.txt example.env "$TEMP_DIR/$SKILL_NAME/" 2>/dev/null || true
rm -f "$TEMP_DIR/$SKILL_NAME/163邮箱故障排查指南.md" 2>/dev/null || true
rm -f "$TEMP_DIR/$SKILL_NAME/idea.md" 2>/dev/null || true

# Explicitly ensure .env is not in the zip folder (just in case)
rm -f "$TEMP_DIR/$SKILL_NAME/.env"

# Go to temp dir and zip
cd "$TEMP_DIR"
zip -r "$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.zip" "$SKILL_NAME" > /dev/null

# Clean up
rm -rf "$TEMP_DIR"
cd "$PROJECT_DIR"

echo "✅ Successfully created $DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.zip"
echo "All packaging complete!"
