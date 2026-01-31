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
    """Upload image to imgbb and return URL using multipart form-data."""
    imgbb_api_key = os.environ.get("IMGBB_API_KEY", "")
    if not imgbb_api_key:
        log("IMGBB_API_KEY not set, skipping image upload")
        return None

    try:
        # 检查文件大小（imgbb限制32MB）
        file_size = os.path.getsize(image_path)
        if file_size > 32 * 1024 * 1024:
            log(f"Image file too large ({file_size} bytes), skipping upload")
            return None

        log(f"Uploading image to imgbb (size: {file_size} bytes)...")

        # 使用curl的multipart form-data上传，使用@file语法避免命令行参数过长
        cmd = [
            "curl", "-s", "-X", "POST",
            f"https://api.imgbb.com/1/upload?key={imgbb_api_key}",
            "-F", f"image=@{image_path}"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            log(f"❌ curl command failed with code {result.returncode}")
            if result.stderr:
                log(f"Error: {result.stderr[:200]}")
            return None

        response = json.loads(result.stdout)

        if response.get("success"):
            url = response.get("data", {}).get("url", "")
            log(f"✅ Image uploaded to imgbb: {url}")
            return url
        else:
            error_msg = response.get("error", {}).get("message", "Unknown error")
            log(f"❌ imgbb upload failed: {error_msg}")
            return None
    except subprocess.TimeoutExpired:
        log("❌ imgbb upload timeout")
        return None
    except json.JSONDecodeError as e:
        log(f"❌ imgbb response parse error: {e}")
        log(f"Response: {result.stdout[:500]}")
        return None
    except Exception as e:
        log(f"❌ Image upload error: {type(e).__name__}: {e}")
        return None


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
        log(f"Sending request to: {url}")
        log(f"Request data: {json.dumps(data, ensure_ascii=False)[:500]}...")  # 只显示前500字符

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        log(f"HTTP Status Code: {result.returncode}")
        log(f"Response stdout: {result.stdout[:1000]}")  # 显示前1000字符
        if result.stderr:
            log(f"Response stderr: {result.stderr[:500]}")

        response = json.loads(result.stdout)
        log(f"WeChat publish result: {json.dumps(response, ensure_ascii=False)}")
        return response
    except subprocess.TimeoutExpired:
        log("❌ WeChat publish timeout (60s)")
        return {"success": False, "error": "Request timeout"}
    except json.JSONDecodeError as e:
        log(f"❌ WeChat publish JSON parse error: {e}")
        log(f"Raw response: {result.stdout}")
        return {"success": False, "error": f"Parse error: {result.stdout}"}
    except Exception as e:
        log(f"❌ WeChat publish exception: {type(e).__name__}: {e}")
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

    # Upload cover image to imgbb (不使用base64 fallback，因为太大会导致curl失败)
    cover_url = None
    if cover_path:
        log(f"Cover image generated: {cover_path}")
        log("Uploading cover image to imgbb...")
        cover_url = upload_to_imgbb(cover_path)
        if cover_url:
            if cover_url.startswith("data:"):
                # Base64图片太大，不使用
                log("⚠️ Base64 image too large, skipping cover image")
                cover_url = None
            elif cover_url.startswith("http"):
                log(f"✅ Cover image uploaded: {cover_url}")
            else:
                log(f"⚠️ Invalid cover URL: {cover_url}, skipping")
                cover_url = None
        else:
            log("⚠️ Failed to upload cover image, publishing without cover")

    # Step 3: Publish to WeChat
    log("Step 3: Publishing to WeChat...")
    title = f"每日Skill精选：{skill_name}"

    result = publish_to_wechat(title, article, cover_image=cover_url)

    if result.get("success"):
        log("✅ Successfully published to WeChat!")
        log(f"Publication ID: {result.get('data', {}).get('publicationId', 'N/A')}")
        log("=" * 50)
        log("Skill Digest Auto Publish completed successfully")
        log("=" * 50)
        return 0
    else:
        log(f"❌ WeChat publish FAILED: {result.get('error', 'Unknown error')}")
        log(f"Full response: {json.dumps(result, ensure_ascii=False)}")
        log("=" * 50)
        log("Skill Digest Auto Publish FAILED - WeChat publish error")
        log("=" * 50)
        return 1


if __name__ == "__main__":
    sys.exit(main())
