#!/usr/bin/env python3
"""
Select a skill for daily digest.
Implements smart selection to avoid duplicates and ensure variety.
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CACHE_FILE = DATA_DIR / "skill_cache.json"
PUBLISHED_FILE = DATA_DIR / "published_skills.json"
SELECTED_FILE = DATA_DIR / "selected_skill.json"
LOG_FILE = SCRIPT_DIR.parent / "logs" / "daily.log"


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


def load_json(filepath: Path) -> dict:
    """Load JSON file with error handling."""
    if filepath.exists():
        try:
            with open(filepath) as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading {filepath}: {e}")
    return {}


def save_json(filepath: Path, data: dict):
    """Save data to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"Error saving {filepath}: {e}")


def get_published_skills() -> set:
    """Get set of URLs for already published skills."""
    data = load_json(PUBLISHED_FILE)
    published = data.get("published", [])
    return {item.get("url") for item in published if item.get("url")}


def get_recent_categories(days: int = 7) -> list:
    """Get categories published in the last N days."""
    data = load_json(PUBLISHED_FILE)
    published = data.get("published", [])
    cutoff = datetime.now() - timedelta(days=days)

    recent_categories = []
    for item in published:
        try:
            pub_date = datetime.fromisoformat(item.get("date", ""))
            if pub_date > cutoff:
                category = item.get("category", "")
                if category:
                    recent_categories.append(category)
        except Exception:
            pass

    return recent_categories


def score_skill(skill: dict, published_urls: set, recent_categories: list) -> float:
    """
    Score a skill for selection priority.
    Higher score = better candidate.
    """
    score = 100.0

    # Exclude already published
    if skill.get("url") in published_urls:
        return -1

    # Penalize recently used categories (variety)
    category = skill.get("category", "")
    category_count = recent_categories.count(category)
    score -= category_count * 20

    # Boost skills with good descriptions
    description = skill.get("description", "")
    if len(description) > 50:
        score += 10
    elif len(description) < 10:
        score -= 10

    # Boost GitHub source (more reliable)
    if skill.get("source") == "github-awesome":
        score += 5

    # Add some randomness to avoid predictability
    score += random.uniform(0, 20)

    return score


def select_daily_skill(skills: list = None) -> dict:
    """Select the best skill for today's digest."""

    # Load skills from cache if not provided
    if skills is None:
        cache = load_json(CACHE_FILE)
        skills = cache.get("skills", [])

    if not skills:
        log("No skills available for selection")
        return None

    log(f"Selecting from {len(skills)} skills...")

    # Get exclusion and preference data
    published_urls = get_published_skills()
    recent_categories = get_recent_categories(days=7)

    log(f"Already published: {len(published_urls)} skills")
    log(f"Recent categories: {recent_categories}")

    # Score all skills
    scored_skills = []
    for skill in skills:
        score = score_skill(skill, published_urls, recent_categories)
        if score >= 0:
            scored_skills.append((score, skill))

    if not scored_skills:
        log("All skills have been published! Resetting...")
        # Reset: allow re-publishing skills not published in last 30 days
        data = load_json(PUBLISHED_FILE)
        published = data.get("published", [])
        cutoff = datetime.now() - timedelta(days=30)

        recent_published = [
            item for item in published
            if datetime.fromisoformat(item.get("date", datetime.min.isoformat())) > cutoff
        ]
        data["published"] = recent_published
        save_json(PUBLISHED_FILE, data)

        # Retry selection
        published_urls = {item.get("url") for item in recent_published}
        for skill in skills:
            score = score_skill(skill, published_urls, recent_categories)
            if score >= 0:
                scored_skills.append((score, skill))

    if not scored_skills:
        log("Still no skills available after reset")
        return None

    # Sort by score and select top
    scored_skills.sort(key=lambda x: x[0], reverse=True)
    selected = scored_skills[0][1]

    log(f"Selected: {selected.get('name')} (score: {scored_skills[0][0]:.1f})")

    # Save selected skill
    selected_data = {
        "skill": selected,
        "selected_at": datetime.now().isoformat(),
        "score": scored_skills[0][0]
    }
    save_json(SELECTED_FILE, selected_data)

    return selected


def mark_as_published(skill: dict):
    """Mark a skill as published."""
    data = load_json(PUBLISHED_FILE)
    published = data.get("published", [])

    entry = {
        "name": skill.get("name"),
        "url": skill.get("url"),
        "category": skill.get("category"),
        "date": datetime.now().isoformat()
    }
    published.append(entry)

    data["published"] = published
    data["last_updated"] = datetime.now().isoformat()

    save_json(PUBLISHED_FILE, data)
    log(f"Marked as published: {skill.get('name')}")


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Select a skill for daily digest")
    parser.add_argument("--mark-published", "-m", action="store_true",
                       help="Mark the selected skill as published")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    selected = select_daily_skill()

    if not selected:
        log("No skill selected")
        return 1

    if args.mark_published:
        mark_as_published(selected)

    output = json.dumps(selected, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        log(f"Selected skill written to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
