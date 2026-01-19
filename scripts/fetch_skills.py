#!/usr/bin/env python3
"""
Fetch Claude Skills from aggregation websites.
Primary source: GitHub awesome-claude-skills
Secondary sources: skillsmp.com, oneskill.dev
"""

import json
import os
import re
import ssl
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Create SSL context that doesn't verify certificates (for macOS compatibility)
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CACHE_FILE = DATA_DIR / "skill_cache.json"
LOG_FILE = SCRIPT_DIR.parent / "logs" / "daily.log"

# Data sources
GITHUB_RAW_URL = "https://raw.githubusercontent.com/travisvn/awesome-claude-skills/main/README.md"
GITHUB_API_URL = "https://api.github.com/repos/travisvn/awesome-claude-skills/contents"


def log(message: str):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_line + "\n")
    except Exception:
        pass


def fetch_url(url: str, headers: dict = None) -> str:
    """Fetch URL content with error handling."""
    try:
        req_headers = {"User-Agent": "Claude-Skill-Digest/1.0"}
        if headers:
            req_headers.update(headers)
        request = Request(url, headers=req_headers)
        with urlopen(request, timeout=30, context=SSL_CONTEXT) as response:
            return response.read().decode("utf-8")
    except HTTPError as e:
        log(f"HTTP Error {e.code} fetching {url}")
        return None
    except URLError as e:
        log(f"URL Error fetching {url}: {e.reason}")
        return None
    except Exception as e:
        log(f"Error fetching {url}: {e}")
        return None


def parse_awesome_list(content: str) -> list:
    """Parse the awesome-claude-skills README.md to extract skills."""
    skills = []

    # Pattern to match skill entries like:
    # - [Skill Name](url) - Description
    # or
    # - **[Skill Name](url)** - Description
    pattern = r'-\s+\*?\*?\[([^\]]+)\]\(([^)]+)\)\*?\*?\s*[-–:]\s*(.+?)(?=\n|$)'

    matches = re.findall(pattern, content)

    current_category = "General"

    # Also try to detect categories from headers
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Match headers like ## Category or ### Category
        header_match = re.match(r'^#{2,3}\s+(.+)$', line)
        if header_match:
            current_category = header_match.group(1).strip()
            continue

        # Match skill entries
        skill_match = re.match(r'-\s+\*?\*?\[([^\]]+)\]\(([^)]+)\)\*?\*?\s*[-–:]?\s*(.+)?', line)
        if skill_match:
            name = skill_match.group(1).strip()
            url = skill_match.group(2).strip()
            description = skill_match.group(3).strip() if skill_match.group(3) else ""

            # Skip non-skill links (like badges, social links)
            if any(skip in url.lower() for skip in ['badge', 'shield', 'twitter', 'linkedin', 'discord']):
                continue

            skill = {
                "name": name,
                "url": url,
                "description": description,
                "category": current_category,
                "source": "github-awesome",
                "fetched_at": datetime.now().isoformat()
            }
            skills.append(skill)

    return skills


def fetch_from_github() -> list:
    """Fetch skills from GitHub awesome-claude-skills."""
    log("Fetching from GitHub awesome-claude-skills...")
    content = fetch_url(GITHUB_RAW_URL)
    if not content:
        log("Failed to fetch GitHub awesome list")
        return []

    skills = parse_awesome_list(content)
    log(f"Found {len(skills)} skills from GitHub")
    return skills


def fetch_from_skillsmp() -> list:
    """Fetch skills from skillsmp.com (placeholder for future implementation)."""
    # This would require more complex scraping or API access
    # For now, return empty list
    log("SkillsMP scraping not implemented yet")
    return []


def fetch_from_oneskill() -> list:
    """Fetch skills from oneskill.dev (placeholder for future implementation)."""
    # This would require more complex scraping or API access
    # For now, return empty list
    log("OneSkill scraping not implemented yet")
    return []


def load_cache() -> dict:
    """Load cached skills data."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading cache: {e}")
    return {"skills": [], "last_updated": None}


def save_cache(data: dict):
    """Save skills data to cache."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log(f"Cache saved with {len(data.get('skills', []))} skills")
    except Exception as e:
        log(f"Error saving cache: {e}")


def merge_skills(existing: list, new: list) -> list:
    """Merge new skills with existing, avoiding duplicates."""
    # Create a set of existing URLs for quick lookup
    existing_urls = {s.get("url") for s in existing}

    merged = existing.copy()
    added = 0

    for skill in new:
        if skill.get("url") not in existing_urls:
            merged.append(skill)
            existing_urls.add(skill.get("url"))
            added += 1

    log(f"Added {added} new skills, total: {len(merged)}")
    return merged


def fetch_all_skills(force_refresh: bool = False) -> list:
    """Fetch skills from all sources and merge with cache."""
    cache = load_cache()
    existing_skills = cache.get("skills", [])

    # Check if cache is fresh (less than 24 hours old)
    if not force_refresh and cache.get("last_updated"):
        try:
            last_updated = datetime.fromisoformat(cache["last_updated"])
            age_hours = (datetime.now() - last_updated).total_seconds() / 3600
            if age_hours < 24:
                log(f"Using cached data (updated {age_hours:.1f} hours ago)")
                return existing_skills
        except Exception:
            pass

    log("Refreshing skills from all sources...")

    # Fetch from all sources
    github_skills = fetch_from_github()
    skillsmp_skills = fetch_from_skillsmp()
    oneskill_skills = fetch_from_oneskill()

    # Merge all skills
    all_new = github_skills + skillsmp_skills + oneskill_skills
    merged = merge_skills(existing_skills, all_new)

    # Save updated cache
    save_cache({
        "skills": merged,
        "last_updated": datetime.now().isoformat()
    })

    return merged


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Fetch Claude Skills from aggregation sites")
    parser.add_argument("--refresh", "-r", action="store_true", help="Force refresh from sources")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    args = parser.parse_args()

    skills = fetch_all_skills(force_refresh=args.refresh)

    output = json.dumps(skills, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        log(f"Skills written to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
