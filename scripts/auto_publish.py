#!/usr/bin/env python3
"""
Auto publish script for GitHub Actions.
Generates article and publishes to WeChat.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fetch_skills import fetch_all_skills, log
from select_daily import select_daily_skill, load_json, SELECTED_FILE
from generate_article import generate_article, call_openrouter_api, OPENROUTER_API_KEY

# WeChat publish configuration (微绿流量宝 API)
WECHAT_API_KEY = os.environ.get("WECHAT_API_KEY") or os.environ.get("SANGENG_API_KEY", "")
WECHAT_APPID = "wx5c5f1c55d02d1354"  # 三更AI
WECHAT_API_BASE = "https://wx.limyai.com/api/openapi"


def get_image_base64(image_path: str) -> str:
    """Convert image to base64 data URL."""
    try:
        import base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Return as data URL
        return f"data:image/png;base64,{image_data}"
    except Exception as e:
        log(f"Error converting image to base64: {e}")
        return None


def upload_to_imgbb(image_path: str) -> str:
    """Upload image to imgbb and return URL."""
    imgbb_api_key = os.environ.get("IMGBB_API_KEY", "")
    if not imgbb_api_key:
        log("IMGBB_API_KEY not set, using base64 data URL instead")
        return get_image_base64(image_path)

    try:
        import base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        cmd = [
            "curl", "-s", "-X", "POST",
            f"https://api.imgbb.com/1/upload?key={imgbb_api_key}",
            "-F", f"image={image_data}"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        response = json.loads(result.stdout)

        if response.get("success"):
            url = response.get("data", {}).get("url", "")
            log(f"Image uploaded to imgbb: {url}")
            return url
        else:
            log(f"imgbb upload failed, using base64 fallback")
            return get_image_base64(image_path)
    except Exception as e:
        log(f"Image upload error, using base64 fallback: {e}")
        return get_image_base64(image_path)


def publish_to_wechat(title: str, content: str, author: str = "三更AI", cover_image: str = None) -> dict:
    """Publish article to WeChat Official Account using curl."""
    if not WECHAT_API_KEY:
        log("WECHAT_API_KEY/SANGENG_API_KEY not set, skipping WeChat publish")
        return {"success": False, "error": "API key not set"}

    url = f"{WECHAT_API_BASE}/wechat-publish"

    data = {
        "wechatAppid": WECHAT_APPID,
        "title": title,
        "content": content,
        "contentFormat": "markdown",
        "author": author
    }

    # Add cover image if provided
    if cover_image:
        data["coverImage"] = cover_image
        log(f"Using cover image: {cover_image}")

    # Use curl to avoid SSL issues in GitHub Actions
    cmd = [
        "curl", "-s", "-X", "POST", url,
        "-H", f"X-API-Key: {WECHAT_API_KEY}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        response = json.loads(result.stdout)
        log(f"WeChat publish result: {json.dumps(response, ensure_ascii=False)}")
        return response
    except subprocess.TimeoutExpired:
        log("WeChat publish timeout")
        return {"success": False, "error": "Request timeout"}
    except json.JSONDecodeError:
        log(f"WeChat publish parse error: {result.stdout}")
        return {"success": False, "error": f"Parse error: {result.stdout}"}
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

    # Upload cover image to imgbb or use base64
    cover_url = None
    if cover_path:
        log(f"Cover image generated: {cover_path}")
        log("Processing cover image...")
        cover_url = upload_to_imgbb(cover_path)
        if cover_url:
            if cover_url.startswith("data:"):
                log("Using base64 data URL for cover image")
            else:
                log(f"Cover image uploaded: {cover_url}")
        else:
            log("Warning: Failed to process cover image, publishing without cover")

    # Step 3: Publish to WeChat
    log("Step 3: Publishing to WeChat...")
    title = f"每日Skill精选：{skill_name}"

    result = publish_to_wechat(title, article, cover_image=cover_url)

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
