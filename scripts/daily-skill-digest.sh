#!/bin/bash
#
# Daily Skill Digest - Main Script
# Runs the complete workflow: fetch -> select -> generate -> publish
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$SKILL_DIR/data"
LOG_DIR="$SKILL_DIR/logs"
LOG_FILE="$LOG_DIR/daily.log"

# Output directory
OUTPUT_DIR="$HOME/Documents/Obsidian/ai自动生成/skill-digest"

# Ensure directories exist
mkdir -p "$DATA_DIR" "$LOG_DIR" "$OUTPUT_DIR"

# Logging function
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "Starting Daily Skill Digest"
log "=========================================="

# Step 1: Fetch skills from sources
log "Step 1: Fetching skills from sources..."
python3 "$SCRIPT_DIR/fetch_skills.py" --refresh > /dev/null 2>&1 || {
    log "Warning: Failed to refresh skills, using cached data"
}

# Check if we have skills
SKILL_COUNT=$(python3 -c "import json; f=open('$DATA_DIR/skill_cache.json'); d=json.load(f); print(len(d.get('skills',[])))" 2>/dev/null || echo "0")
log "Available skills: $SKILL_COUNT"

if [ "$SKILL_COUNT" -eq "0" ]; then
    log "Error: No skills available. Exiting."
    exit 1
fi

# Step 2: Select today's skill
log "Step 2: Selecting today's skill..."
# Run selection and save to temp file for parsing
TEMP_JSON=$(mktemp)
python3 "$SCRIPT_DIR/select_daily.py" 2>&1 | tee "$TEMP_JSON" | grep -E "^\[" >> "$LOG_FILE" || true

# Extract JSON from output (everything from first { to last })
SELECTED=$(sed -n '/^{/,/^}/p' "$TEMP_JSON")

if [ -z "$SELECTED" ]; then
    log "Error: Failed to select skill"
    cat "$TEMP_JSON" >> "$LOG_FILE"
    rm -f "$TEMP_JSON"
    exit 1
fi

# Get skill name from selection
SKILL_NAME=$(echo "$SELECTED" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name','Unknown'))" 2>/dev/null || echo "Unknown")
rm -f "$TEMP_JSON"

if [ "$SKILL_NAME" = "Unknown" ] || [ -z "$SKILL_NAME" ]; then
    log "Error: Could not parse skill name"
    exit 1
fi
log "Selected skill: $SKILL_NAME"

# Step 3: Generate article
log "Step 3: Generating article..."
# Sanitize filename
SAFE_SKILL_NAME=$(echo "$SKILL_NAME" | sed 's/ /-/g' | sed 's/\//-/g' | sed 's/[^a-zA-Z0-9_-]//g')
ARTICLE_FILE="$OUTPUT_DIR/$(date '+%Y-%m-%d')-${SAFE_SKILL_NAME}.md"

python3 "$SCRIPT_DIR/generate_article.py" --output "$ARTICLE_FILE" 2>&1 | tee -a "$LOG_FILE"

if [ ! -f "$ARTICLE_FILE" ]; then
    log "Error: Failed to generate article"
    exit 1
fi

log "Article saved to: $ARTICLE_FILE"

# Step 4: Mark skill as published
log "Step 4: Marking skill as published..."
python3 "$SCRIPT_DIR/select_daily.py" --mark-published > /dev/null 2>&1

# Step 5: Publish to WeChat (optional)
log "Step 5: Publishing to WeChat..."

# Check if wechat-publish skill is available
WECHAT_PUBLISH_DIR="$HOME/.claude/skills/wechat-publish"
if [ -d "$WECHAT_PUBLISH_DIR" ]; then
    # Use the wechat-publish skill's publish.py
    PUBLISH_SCRIPT="$WECHAT_PUBLISH_DIR/scripts/publish.py"
    if [ -f "$PUBLISH_SCRIPT" ]; then
        log "Found wechat-publish skill, attempting to publish..."

        # Check for required environment variable
        if [ -z "$SANGENG_API_KEY" ]; then
            log "Warning: SANGENG_API_KEY not set, skipping WeChat publish"
        else
            # AppID for 三更AI
            WECHAT_APPID="wx5c5f1c55d02d1354"

            # Run publish script with correct subcommand format
            python3 "$PUBLISH_SCRIPT" publish \
                --appid "$WECHAT_APPID" \
                --title "每日Skill精选：$SKILL_NAME" \
                --content-file "$ARTICLE_FILE" \
                --author "三更AI" \
                2>&1 | tee -a "$LOG_FILE" || {
                    log "Warning: WeChat publish failed, article saved locally"
                }
        fi
    else
        log "Warning: wechat-publish script not found at $PUBLISH_SCRIPT"
    fi
else
    log "Note: wechat-publish skill not installed, skipping WeChat publish"
    log "To enable auto-publish, install the wechat-publish skill"
fi

log "=========================================="
log "Daily Skill Digest completed successfully"
log "=========================================="
log "Article: $ARTICLE_FILE"
log "Skill: $SKILL_NAME"
log ""

exit 0
