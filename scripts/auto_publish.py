#!/usr/bin/env python3
"""
Auto publish script for GitHub Actions.
Generates article and publishes to WeChat.
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fetch_skills import fetch_all_skills, log
from select_daily import select_daily_skill, load_json, SELECTED_FILE
from generate_article import generate_article, call_openrouter_api, OPENROUTER_API_KEY

# WeChat publish configuration
SANGENG_API_KEY = os.environ.get("SANGENG_API_KEY", "")
WECHAT_APPID = "wx5c5f1c55d02d1354"
WECHAT_API_URL = "https://api.weilvb.com/api/ma/article/publish"


def publish_to_wechat(title: str, content: str, author: str = "三更AI") -> dict:
    """Publish article to WeChat Official Account."""
    import ssl
    from urllib.request import urlopen, Request

    if not SANGENG_API_KEY:
        log("SANGENG_API_KEY not set, skipping WeChat publish")
        return {"success": False, "error": "API key not set"}

    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    payload = {
        "appId": WECHAT_APPID,
        "title": title,
        "content": content,
        "author": author
    }

    try:
        request = Request(
            WECHAT_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SANGENG_API_KEY}"
            }
        )
        with urlopen(request, timeout=60, context=ssl_context) as response:
            result = json.loads(response.read().decode("utf-8"))
            log(f"WeChat publish result: {json.dumps(result, ensure_ascii=False)}")
            return result
    except Exception as e:
        log(f"WeChat publish error: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Main entry point for GitHub Actions."""
    log("=" * 50)
    log("Starting Skill Digest Auto Publish")
    log("=" * 50)

    # Check API key
    if not OPENROUTER_API_KEY:
        log("ERROR: OPENROUTER_API_KEY not set")
        return 1

    # Step 1: Load selected skill
    log("Step 1: Loading selected skill...")
    selected_data = load_json(SELECTED_FILE)
    skill = selected_data.get("skill")

    if not skill:
        log("ERROR: No skill selected. Run select_daily.py first.")
        return 1

    skill_name = skill.get("name", "Unknown")
    log(f"Selected skill: {skill_name}")

    # Step 2: Generate article
    log("Step 2: Generating article...")
    article, cover_path = generate_article(skill, generate_cover=True)

    if not article:
        log("ERROR: Failed to generate article")
        return 1

    log(f"Article generated: {len(article)} characters")
    if cover_path:
        log(f"Cover image: {cover_path}")

    # Step 3: Publish to WeChat
    log("Step 3: Publishing to WeChat...")
    title = f"每日Skill精选：{skill_name}"

    result = publish_to_wechat(title, article)

    if result.get("success"):
        log("✅ Successfully published to WeChat!")
        log(f"Publication ID: {result.get('data', {}).get('publicationId', 'N/A')}")
    else:
        log(f"⚠️ WeChat publish failed: {result.get('error', 'Unknown error')}")
        # Don't fail the workflow if only WeChat publish fails
        # The article was still generated successfully

    log("=" * 50)
    log("Skill Digest Auto Publish completed")
    log("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
