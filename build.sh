#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

PROJECT_DIR=$(pwd)
DIST_DIR="$PROJECT_DIR/dist"
DATE_SUFFIX=$(date +%Y%m%d)
SKILL_NAME="mail-skill"

echo "========================================="
echo " mail-skill build - $(date +%Y-%m-%d)"
echo "========================================="

# -------------------------------------------------------------------
# STEP 0: KEY LEAK CHECK
# -------------------------------------------------------------------
echo ""
echo "[0/4] Scanning for leaked credentials..."

LEAKED=0
SCAN_DIRS=("$PROJECT_DIR/scripts" "$PROJECT_DIR/references" "$PROJECT_DIR/assets")

# Patterns to match: API keys, passwords, tokens
PATTERNS=(
    "sk-[a-zA-Z0-9]{20,}"         # OpenAI/DeepSeek API keys
    "AKIA[0-9A-Z]{16}"             # AWS access keys
    "ghp_[a-zA-Z0-9]{36}"          # GitHub tokens
    "xox[baprs]-[a-zA-Z0-9-]+"     # Slack tokens
)

for dir in "${SCAN_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then continue; fi
    for pattern in "${PATTERNS[@]}"; do
        matches=$(grep -rno "$pattern" "$dir" 2>/dev/null || true)
        if [ -n "$matches" ]; then
            echo "  ❌ LEAK DETECTED: $pattern"
            echo "$matches" | while read -r line; do
                echo "     $line"
            done
            LEAKED=1
        fi
    done
done

# Also check password patterns (less precise, flag for review)
PWD_MATCHES=$(grep -rn 'PASSWORD=.\{4,\}' "$PROJECT_DIR/scripts" 2>/dev/null | grep -v 'your_app_password\|your_password\|example' || true)
if [ -n "$PWD_MATCHES" ]; then
    echo "  ⚠️  POTENTIAL PASSWORD LEAK (review manually):"
    echo "$PWD_MATCHES" | while read -r line; do
        echo "     $line"
    done
fi

if [ "$LEAKED" -eq 1 ]; then
    echo ""
    echo "❌ BUILD ABORTED: Credentials leaked in source files!"
    echo "   Remove secrets before packaging or add to .gitignore."
    exit 1
fi
echo "  ✅ No leaked keys detected in source files"

# Verify config.txt is NOT being packaged
if grep -qrP 'sk-[a-zA-Z0-9]{20,}' "$PROJECT_DIR/scripts/" 2>/dev/null; then
    echo "  ❌ BUILD ABORTED: API key found in script files"
    exit 1
fi
# Check for passwords (4+ chars, exclude placeholders)
if grep -rPn '\bPASSWORD\s*=\s*(?!.*(your_app|your_password|example|app_password))[^\s]{4,}' "$PROJECT_DIR/scripts/" 2>/dev/null; then
    echo "  ❌ BUILD ABORTED: Hardcoded password in script files"
    exit 1
fi
echo "  ✅ No hardcoded keys in source"

# -------------------------------------------------------------------
# STEP 1: Prepare dist directory
# -------------------------------------------------------------------
echo ""
echo "[1/4] Preparing dist directory..."
mkdir -p "$DIST_DIR"
rm -f "$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.skill"
rm -f "$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.zip"

# -------------------------------------------------------------------
# STEP 2: Build .skill file
# -------------------------------------------------------------------
echo "[2/4] Building .skill package..."
BUILD_TEMP=$(mktemp -d)
cp -r "$PROJECT_DIR"/* "$BUILD_TEMP/" 2>/dev/null || true
cp "$PROJECT_DIR/.gitignore" "$BUILD_TEMP/" 2>/dev/null || true

# Remove sensitive / unwanted files from build
rm -f "$BUILD_TEMP/config.txt"
rm -f "$BUILD_TEMP/163邮箱故障排查指南.md" 2>/dev/null || true
rm -f "$BUILD_TEMP/idea.md" 2>/dev/null || true
rm -rf "$BUILD_TEMP/dist"
rm -rf "$BUILD_TEMP/mail_data"
rm -f "$BUILD_TEMP/mail-skill.skill" 2>/dev/null || true

SKILL_CREATOR="${SKILL_CREATOR_PATH:-$HOME/.trae/skills/skill-creator}"
if [ -f "$SKILL_CREATOR/scripts/package_skill.py" ]; then
    PYTHONPATH="$SKILL_CREATOR" python "$SKILL_CREATOR/scripts/package_skill.py" "$BUILD_TEMP" "$DIST_DIR"
    SKILL_FILE=$(find "$DIST_DIR" -maxdepth 1 -name "*.skill" | head -n 1)
    if [ -n "$SKILL_FILE" ]; then
        mv "$SKILL_FILE" "$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.skill"
        echo "  ✅ ${SKILL_NAME}-${DATE_SUFFIX}.skill"
    fi
else
    echo "  ⚠️  skill-creator not found at $SKILL_CREATOR, skipping .skill"
fi
rm -rf "$BUILD_TEMP"

# -------------------------------------------------------------------
# STEP 3: Build .zip distribution
# -------------------------------------------------------------------
echo "[3/4] Building .zip distribution..."
TEMP_DIR=$(mktemp -d)
PKG_DIR="$TEMP_DIR/$SKILL_NAME"
mkdir -p "$PKG_DIR"

# Copy only what's needed for distribution
cp -r SKILL.md README.md scripts references assets requirements.txt example.config.txt "$PKG_DIR/" 2>/dev/null || true
rm -f "$PKG_DIR/163邮箱故障排查指南.md" 2>/dev/null || true
rm -f "$PKG_DIR/idea.md" 2>/dev/null || true
# Triple-check: absolutely no config.txt in the package
rm -f "$PKG_DIR/config.txt"

cd "$TEMP_DIR"
zip -r "$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.zip" "$SKILL_NAME" > /dev/null
cd "$PROJECT_DIR"
rm -rf "$TEMP_DIR"
echo "  ✅ ${SKILL_NAME}-${DATE_SUFFIX}.zip"

# -------------------------------------------------------------------
# STEP 4: Verify the package
# -------------------------------------------------------------------
echo ""
echo "[4/4] Verifying package..."
ZIP_FILE="$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.zip"
if [ -f "$ZIP_FILE" ]; then
    # Check no config.txt leaked into zip
    if unzip -l "$ZIP_FILE" 2>/dev/null | grep -q "config.txt"; then
        echo "  ❌ LEAK: config.txt found in zip package!"
        exit 1
    fi
    # Check no API keys in zip content
    if unzip -p "$ZIP_FILE" 2>/dev/null | grep -q "sk-[a-zA-Z0-9]\{20,\}"; then
        echo "  ❌ LEAK: API key pattern found in zip package!"
        exit 1
    fi
    echo "  ✅ No secrets leaked in zip package"
fi

SKILL_FILE="$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}.skill"
if [ -f "$SKILL_FILE" ]; then
    if unzip -l "$SKILL_FILE" 2>/dev/null | grep -q "config.txt"; then
        echo "  ❌ LEAK: config.txt found in .skill package!"
        exit 1
    fi
    echo "  ✅ No secrets leaked in .skill package"
fi

# -------------------------------------------------------------------
# DONE
# -------------------------------------------------------------------
echo ""
echo "========================================="
echo " Build complete"
echo " Output: $DIST_DIR/"
ls -lh "$DIST_DIR/${SKILL_NAME}-${DATE_SUFFIX}."* 2>/dev/null || true
echo "========================================="
