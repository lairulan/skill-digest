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
        req_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
        }
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


def _is_valid_skill_url(url: str) -> bool:
    """Validate if URL points to a valid Claude Code Skill repository."""
    # 必须是 GitHub 链接
    if 'github.com' not in url:
        return False

    # 排除非 skill 路径
    invalid_patterns = [
        '/issues', '/discussions', '/pulls', '/wiki', '/releases',
        '/actions', '/projects', '/security', '/pulse', '/graphs',
        'support.', 'docs.', 'blog.', '.ai/blog', '.com/blog'
    ]

    for pattern in invalid_patterns:
        if pattern in url.lower():
            return False

    # GitHub skill 通常包含这些路径之一
    valid_patterns = [
        '/tree/main/skills/',
        '/tree/master/skills/',
        '/blob/main/SKILL.md',
        '/blob/master/SKILL.md',
        'anthropics/skills',  # Anthropic 官方 skills 仓库
    ]

    # 检查是否匹配有效模式
    for pattern in valid_patterns:
        if pattern in url:
            return True

    # 如果是指向仓库根目录，检查是否可能是单个 skill 仓库
    # 格式: github.com/user/repo (没有 /tree/ 等子路径)
    repo_root_pattern = r'^https?://github\.com/[^/]+/[^/]+/?$'
    if re.match(repo_root_pattern, url):
        # 可能是单个 skill 的仓库，暂时接受
        return True

    return False


def parse_awesome_list(content: str) -> list:
    """Parse the awesome-claude-skills README.md to extract skills."""
    skills = []
    current_category = "General"

    # 跳过的链接类型
    skip_patterns = ['badge', 'shield', 'twitter', 'linkedin', 'discord',
                     'buymeacoffee', 'ko-fi', 'sponsor', 'paypal', 'patreon']

    # 只保留真正的 Skill 分类（白名单）
    valid_categories = [
        'Document Skills', 'Design & Creative', 'Development', 'Testing',
        'Communication', 'Productivity', 'Data Analysis', 'DevOps',
        'Security', 'AI & ML', 'Database', 'Web Development',
        'Mobile Development', 'Game Development', 'Blockchain',
        'Official Skills', 'Community Skills', 'Enterprise Skills',
        # 包含这些关键词的分类也接受
        'Skills'
    ]

    # 排除非 Skill 分类（黑名单）
    skip_categories = [
        'Written Tutorials', 'Video Tutorials', 'Documentation',
        'Articles & Blog Posts', 'Getting Help', 'Community',
        'Resources', 'Learning Resources', 'Guides', 'Templates',
        'Getting Started', 'Skill Creation', 'Creating Your First Skill',
        'Recent Updates', 'Troubleshooting', 'FAQ', 'Contributing',
        'Security & Best Practices', 'Known Issues'
    ]

    # 排除关键词（用于链接和描述）
    skip_keywords = ['tutorial', 'guide', 'documentation', 'article', 'blog',
                     'support.claude.com', 'docs.anthropic.com', '/issues',
                     '/discussions', 'how to', 'how-to', 'learn', 'course']

    lines = content.split('\n')
    for line in lines:
        # 匹配标题（## 或 ###）来确定分类
        header_match = re.match(r'^#{2,4}\s+(.+)$', line)
        if header_match:
            current_category = header_match.group(1).strip()
            # 移除 emoji 前缀
            current_category = re.sub(r'^[\U0001F300-\U0001F9FF\s]+', '', current_category).strip()
            continue

        # 检查当前分类是否有效
        # 跳过黑名单分类
        if any(skip_cat.lower() in current_category.lower() for skip_cat in skip_categories):
            continue

        # 支持多种列表格式：-, *, •, 数字列表
        # 支持可选的粗体 ** 包裹
        # 支持多种分隔符：-, –, :, 或直接空格
        skill_patterns = [
            # 格式1: - [Name](url) - Description
            r'^[-*•]\s+\*?\*?\[([^\]]+)\]\(([^)]+)\)\*?\*?\s*[-–:]?\s*(.*)$',
            # 格式2: - **[Name](url)**: Description
            r'^[-*•]\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*:?\s*(.*)$',
            # 格式3: 1. [Name](url) - Description (数字列表)
            r'^\d+\.\s+\*?\*?\[([^\]]+)\]\(([^)]+)\)\*?\*?\s*[-–:]?\s*(.*)$',
            # 格式4: [Name](url) (无列表符号但在列表上下文中)
            r'^\s{2,}[-*]\s+\[([^\]]+)\]\(([^)]+)\)\s*[-–:]?\s*(.*)$',
        ]

        for pattern in skill_patterns:
            skill_match = re.match(pattern, line)
            if skill_match:
                name = skill_match.group(1).strip()
                url = skill_match.group(2).strip()
                description = skill_match.group(3).strip() if skill_match.group(3) else ""

                # 跳过非技能链接
                if any(skip in url.lower() for skip in skip_patterns):
                    break

                # 跳过锚点链接（目录）
                if url.startswith('#'):
                    break

                # 跳过非 GitHub skill 链接
                if not _is_valid_skill_url(url):
                    break

                # 跳过包含黑名单关键词的内容
                combined_text = (name + ' ' + url + ' ' + description).lower()
                if any(keyword in combined_text for keyword in skip_keywords):
                    break

                # 清理描述中的尾随标点和空白
                description = description.rstrip('.,;:')

                skill = {
                    "name": name,
                    "url": url,
                    "description": description,
                    "category": current_category,
                    "source": "github-awesome",
                    "fetched_at": datetime.now().isoformat()
                }
                skills.append(skill)
                break  # 匹配到一个格式就停止

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
    """Fetch skills from skillsmp.com API."""
    log("Fetching from SkillsMP...")

    # SkillsMP 提供 JSON API
    api_url = "https://skillsmp.com/api/skills"

    try:
        content = fetch_url(api_url)
        if not content:
            # 尝试备用 URL
            backup_url = "https://skillsmp.com/skills.json"
            content = fetch_url(backup_url)

        if not content:
            log("Could not fetch from SkillsMP API")
            return []

        data = json.loads(content)
        skills = []

        # 根据 API 响应格式解析
        items = data if isinstance(data, list) else data.get("skills", data.get("data", []))

        for item in items:
            if isinstance(item, dict):
                skill = {
                    "name": item.get("name", item.get("title", "")),
                    "url": item.get("url", item.get("github_url", item.get("link", ""))),
                    "description": item.get("description", item.get("summary", "")),
                    "category": item.get("category", item.get("tags", ["General"])[0] if item.get("tags") else "General"),
                    "source": "skillsmp",
                    "fetched_at": datetime.now().isoformat()
                }
                if skill["name"] and skill["url"]:
                    skills.append(skill)

        log(f"Found {len(skills)} skills from SkillsMP")
        return skills

    except json.JSONDecodeError:
        log("SkillsMP returned non-JSON response, trying HTML scraping...")
        return _scrape_skillsmp_html()
    except Exception as e:
        log(f"SkillsMP fetch error: {e}")
        return []


def _scrape_skillsmp_html() -> list:
    """Scrape SkillsMP website HTML as fallback."""
    url = "https://skillsmp.com"
    content = fetch_url(url)
    if not content:
        return []

    skills = []

    # 尝试提取技能卡片
    # 常见的 HTML 结构模式
    patterns = [
        # 模式1: <a href="url"><h3>Name</h3></a><p>Description</p>
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>\s*<h[23][^>]*>([^<]+)</h[23]>\s*</a>\s*<p[^>]*>([^<]+)</p>',
        # 模式2: data-skill 属性
        r'data-skill=["\']([^"\']+)["\'][^>]*>.*?<a[^>]*href=["\']([^"\']+)["\']',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        for match in matches:
            if len(match) >= 2:
                skill = {
                    "name": match[1] if len(match) > 1 else match[0],
                    "url": match[0] if match[0].startswith('http') else f"https://skillsmp.com{match[0]}",
                    "description": match[2] if len(match) > 2 else "",
                    "category": "General",
                    "source": "skillsmp",
                    "fetched_at": datetime.now().isoformat()
                }
                if skill["name"] and skill["url"]:
                    skills.append(skill)

    log(f"Scraped {len(skills)} skills from SkillsMP HTML")
    return skills


def fetch_from_oneskill() -> list:
    """Fetch skills from oneskill.dev."""
    log("Fetching from OneSkill...")

    # 尝试 API
    api_url = "https://oneskill.dev/api/skills"

    try:
        content = fetch_url(api_url)
        if content:
            data = json.loads(content)
            skills = []

            items = data if isinstance(data, list) else data.get("skills", data.get("data", []))

            for item in items:
                if isinstance(item, dict):
                    skill = {
                        "name": item.get("name", item.get("title", "")),
                        "url": item.get("url", item.get("github_url", item.get("link", ""))),
                        "description": item.get("description", item.get("summary", "")),
                        "category": item.get("category", "General"),
                        "source": "oneskill",
                        "fetched_at": datetime.now().isoformat()
                    }
                    if skill["name"] and skill["url"]:
                        skills.append(skill)

            log(f"Found {len(skills)} skills from OneSkill API")
            return skills

    except json.JSONDecodeError:
        pass
    except Exception as e:
        log(f"OneSkill API error: {e}")

    # 备用：抓取 HTML
    return _scrape_oneskill_html()


def _scrape_oneskill_html() -> list:
    """Scrape OneSkill website HTML as fallback."""
    url = "https://oneskill.dev"
    content = fetch_url(url)
    if not content:
        return []

    skills = []

    # 尝试提取技能列表
    patterns = [
        r'<a[^>]*href=["\']([^"\']+github[^"\']+)["\'][^>]*>\s*<[^>]*>([^<]+)<',
        r'class=["\']skill[^"\']*["\'][^>]*>\s*<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        for match in matches:
            if len(match) >= 2:
                skill = {
                    "name": match[1].strip(),
                    "url": match[0] if match[0].startswith('http') else f"https://oneskill.dev{match[0]}",
                    "description": "",
                    "category": "General",
                    "source": "oneskill",
                    "fetched_at": datetime.now().isoformat()
                }
                if skill["name"] and 'github' in skill["url"].lower():
                    skills.append(skill)

    log(f"Scraped {len(skills)} skills from OneSkill HTML")
    return skills


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
