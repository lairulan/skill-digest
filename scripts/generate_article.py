#!/usr/bin/env python3
"""
Generate a review article for a selected Claude Skill.
Uses OpenRouter API for content generation and image generation.
"""

import base64
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
SELECTED_FILE = DATA_DIR / "selected_skill.json"
LOG_FILE = SCRIPT_DIR.parent / "logs" / "daily.log"
OUTPUT_DIR = Path.home() / "Documents" / "Obsidian" / "ai自动生成" / "skill-digest"
COVER_DIR = OUTPUT_DIR / "covers"

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# 使用 Qwen 2.5 72B 进行中文文章生成（性价比高，中文效果好）
TEXT_MODEL = "qwen/qwen-2.5-72b-instruct"
# 备选模型
BACKUP_TEXT_MODEL = "google/gemini-2.0-flash-001"

# 图像生成模型 (GPT-5 Image)
IMAGE_MODEL = "openai/gpt-5-image"


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


def call_openrouter_api(prompt: str, system_prompt: str = None, model: str = None) -> str:
    """Call OpenRouter API for content generation."""
    if not OPENROUTER_API_KEY:
        log("OPENROUTER_API_KEY not set, using template-based generation")
        return None

    if model is None:
        model = TEXT_MODEL

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 3000
    }

    try:
        request = Request(
            OPENROUTER_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/anthropics/skills",
                "X-Title": "Claude Skill Digest"
            }
        )
        with urlopen(request, timeout=120, context=SSL_CONTEXT) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                log(f"Successfully generated content with {model}")
            return content
    except Exception as e:
        log(f"OpenRouter API error with {model}: {e}")
        # Try backup model
        if model == TEXT_MODEL:
            log(f"Trying backup model: {BACKUP_TEXT_MODEL}")
            return call_openrouter_api(prompt, system_prompt, BACKUP_TEXT_MODEL)
        return None


def generate_cover_image(skill_name: str, skill_description: str) -> str:
    """Generate a cover image using OpenRouter's GPT-5 Image model."""
    if not OPENROUTER_API_KEY:
        log("OPENROUTER_API_KEY not set, skipping cover image generation")
        return None

    # Create a prompt for the cover image - 明确是 Claude Code Skill
    image_prompt = f"""Generate a professional cover image for "每日Skill精选" - a daily Claude Code Skill recommendation.

Theme: Claude Code Skill "{skill_name}"
Description: {skill_description[:100] if skill_description else 'AI coding assistant skill'}

Design requirements:
- Modern, clean tech illustration style
- Purple and blue gradient as main colors (Claude's brand colors)
- Include abstract elements representing: AI assistant, coding, automation, productivity
- Geometric patterns, code symbols, or circuit-like designs
- Professional and polished look suitable for WeChat Official Account
- 16:9 aspect ratio
- NO text, NO letters, NO words in the image
- Style: flat design, modern UI, tech illustration"""

    payload = {
        "model": IMAGE_MODEL,
        "messages": [
            {
                "role": "user",
                "content": image_prompt
            }
        ]
    }

    try:
        log(f"Generating cover image with {IMAGE_MODEL}...")
        request = Request(
            OPENROUTER_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/anthropics/skills",
                "X-Title": "Claude Skill Digest"
            }
        )
        with urlopen(request, timeout=180, context=SSL_CONTEXT) as response:
            result = json.loads(response.read().decode("utf-8"))

            # Extract image from response
            choices = result.get("choices", [])
            if choices:
                message = choices[0].get("message", {})

                # GPT-5 Image returns images in the "images" field
                images = message.get("images", [])
                if images:
                    for img in images:
                        if img.get("type") == "image_url":
                            image_url = img.get("image_url", {}).get("url", "")
                            if image_url:
                                log(f"Generated cover image via {IMAGE_MODEL}")
                                return save_cover_image_from_base64(image_url, skill_name)

                # Fallback: check content array
                content = message.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "image_url":
                            image_url = item.get("image_url", {}).get("url", "")
                            if image_url:
                                log(f"Generated cover image via {IMAGE_MODEL}")
                                return save_cover_image_from_base64(image_url, skill_name)

            log(f"No image found in response")
            return None

    except Exception as e:
        log(f"Image generation error: {e}")
        return None


def save_cover_image_from_base64(data_url: str, skill_name: str) -> str:
    """Save a base64 data URL image to file."""
    try:
        COVER_DIR.mkdir(parents=True, exist_ok=True)

        # Generate filename
        date_str = datetime.now().strftime("%Y-%m-%d")
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', skill_name.replace(" ", "-"))
        filename = f"{date_str}-{safe_name}.png"
        filepath = COVER_DIR / filename

        # Handle base64 data URL
        if data_url.startswith("data:"):
            # Extract base64 data from data URL
            # Format: data:image/png;base64,xxxxx
            header, base64_data = data_url.split(",", 1)
            image_data = base64.b64decode(base64_data)
        elif data_url.startswith("http"):
            # It's a regular URL, download it
            request = Request(data_url, headers={"User-Agent": "Claude-Skill-Digest/1.0"})
            with urlopen(request, timeout=60, context=SSL_CONTEXT) as response:
                image_data = response.read()
        else:
            # Assume it's raw base64
            image_data = base64.b64decode(data_url)

        with open(filepath, "wb") as f:
            f.write(image_data)

        log(f"Cover image saved to: {filepath}")
        return str(filepath)
    except Exception as e:
        log(f"Error saving cover image: {e}")
        return None


def save_cover_image(image_url: str, skill_name: str) -> str:
    """Download and save the cover image."""
    try:
        COVER_DIR.mkdir(parents=True, exist_ok=True)

        # Generate filename
        date_str = datetime.now().strftime("%Y-%m-%d")
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', skill_name.replace(" ", "-"))
        filename = f"{date_str}-{safe_name}.png"
        filepath = COVER_DIR / filename

        # Download image
        request = Request(image_url, headers={"User-Agent": "Claude-Skill-Digest/1.0"})
        with urlopen(request, timeout=60, context=SSL_CONTEXT) as response:
            image_data = response.read()
            with open(filepath, "wb") as f:
                f.write(image_data)

        log(f"Cover image saved to: {filepath}")
        return str(filepath)
    except Exception as e:
        log(f"Error saving cover image: {e}")
        return None


def fetch_skill_details(skill: dict) -> dict:
    """Fetch additional details about the skill from its URL."""
    url = skill.get("url", "")
    if not url:
        return skill

    # If it's a GitHub URL, try to fetch README
    if "github.com" in url:
        # Handle different GitHub URL patterns
        # Pattern 1: https://github.com/user/repo
        # Pattern 2: https://github.com/user/repo/tree/main/path

        # Try to extract user and repo
        match = re.match(r"https://github\.com/([^/]+)/([^/]+)", url)
        if match:
            user, repo = match.groups()

            # Check if it's a subdirectory path
            subdir_match = re.match(r"https://github\.com/[^/]+/[^/]+/tree/[^/]+/(.+)", url)
            if subdir_match:
                subdir = subdir_match.group(1)
                readme_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/{subdir}/README.md"
            else:
                readme_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/README.md"

            try:
                request = Request(readme_url, headers={"User-Agent": "Claude-Skill-Digest/1.0"})
                with urlopen(request, timeout=15, context=SSL_CONTEXT) as response:
                    readme_content = response.read().decode("utf-8")
                    # Truncate if too long
                    if len(readme_content) > 4000:
                        readme_content = readme_content[:4000] + "\n\n[内容已截断]"
                    skill["readme"] = readme_content
                    log(f"Fetched README for {skill.get('name')}")
            except Exception as e:
                log(f"Could not fetch README: {e}")
                # Try without subdirectory
                if subdir_match:
                    try:
                        readme_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/README.md"
                        request = Request(readme_url, headers={"User-Agent": "Claude-Skill-Digest/1.0"})
                        with urlopen(request, timeout=15, context=SSL_CONTEXT) as response:
                            readme_content = response.read().decode("utf-8")
                            if len(readme_content) > 4000:
                                readme_content = readme_content[:4000] + "\n\n[内容已截断]"
                            skill["readme"] = readme_content
                            log(f"Fetched main README for {skill.get('name')}")
                    except Exception:
                        pass

    return skill


def generate_article_template(skill: dict) -> str:
    """Generate article using template (fallback when API not available)."""
    name = skill.get("name", "Unknown Skill")
    description = skill.get("description", "一个有用的Claude技能")
    url = skill.get("url", "")
    category = skill.get("category", "通用")
    readme = skill.get("readme", "")

    # Extract features from readme if available
    features = []
    if readme:
        # Look for list items that might be features
        feature_matches = re.findall(r"[-*]\s+\*?\*?([^*\n]+)\*?\*?", readme)
        features = [f.strip() for f in feature_matches[:5] if len(f.strip()) > 10]

    if not features:
        features = [
            "自动化工作流程",
            "提升开发效率",
            "简化复杂任务"
        ]

    article = f"""# 每日Skill精选：{name} - {description[:30] if description else '提升你的AI编程效率'}

> 类别：{category}
> 推荐日期：{datetime.now().strftime('%Y年%m月%d日')}

## 这是什么？

{name} 是一个 Claude Code Skill（技能插件）。{description}

Claude Code 是 Anthropic 官方推出的 AI 编程助手，而 Skill 是它的扩展插件，可以增强 Claude 的能力，帮助开发者更高效地完成各种任务。

## 核心能力

"""
    for i, feature in enumerate(features[:4], 1):
        article += f"- **能力{i}**：{feature}\n"

    article += f"""
## 使用场景

### 场景一：日常开发工作
在日常编码过程中，{name} 可以帮助你快速完成常见任务，无需记忆复杂的命令或步骤。

### 场景二：团队协作
当与团队成员协作时，统一使用这个技能可以确保工作流程的一致性，减少沟通成本。

### 场景三：学习探索
对于正在学习 Claude Code 的用户，这个技能提供了很好的参考示例，帮助理解如何构建自己的技能。

## 快速上手

1. 访问技能仓库：[{name}]({url})
2. 按照 README 中的说明进行安装
3. 在 Claude Code 中使用相应的触发命令
4. 开始体验自动化的便利

## 优缺点评估

### ✅ 优点
- 易于安装和配置
- 文档清晰，上手简单
- 功能实用，解决实际问题
- 开源免费，可自定义扩展

### ⚠️ 不足
- 可能需要一定的技术背景才能充分利用
- 部分高级功能需要额外配置

## 推荐指数

⭐⭐⭐⭐ (4/5)

{name} 是一个值得尝试的 Claude 技能。无论你是开发者还是日常用户，都能从中获得便利。建议有兴趣的朋友去试试看！

## 获取方式

- **GitHub**: [{url}]({url})
- **安装方式**: 克隆仓库到 `~/.claude/skills/` 目录

---

*本文由「每日Skill精选」自动生成，每日为你推荐一款优质 Claude Code Skill。*
"""
    return article


def generate_article_with_ai(skill: dict) -> str:
    """Generate article using OpenRouter AI."""
    name = skill.get("name", "Unknown Skill")
    description = skill.get("description", "")
    url = skill.get("url", "")
    category = skill.get("category", "通用")
    readme = skill.get("readme", "")

    system_prompt = """你是「每日Skill精选」栏目的专业编辑，专门撰写 Claude Code Skill 的评测推荐文章。

Claude Code Skill 是什么：
- Claude Code 是 Anthropic 官方推出的 AI 编程助手 CLI 工具
- Skill 是 Claude Code 的扩展插件，可以增强 Claude 的能力
- 用户可以安装各种 Skill 来自动化工作流程、提升效率

你的写作风格：
- 客观专业，有理有据
- 语言流畅，通俗易懂
- 善于发现 Skill 的实用价值
- 能够给出具体的使用建议
- 文章结构清晰，层次分明"""

    user_prompt = f"""请为以下 Claude Code Skill 撰写一篇800-1200字的「每日Skill精选」推荐文章。

Skill 信息：
- 名称：{name}
- 描述：{description}
- 类别：{category}
- GitHub 链接：{url}

{"README内容：" + readme[:3000] if readme else ""}

请按照以下结构撰写：

1. **标题**：每日Skill精选：[Skill名称] - [一句话亮点]

2. **简介**（50-80字）：这是一个什么样的 Claude Code Skill，能帮助用户解决什么问题

3. **核心能力**：列出3-4个主要功能点，说明这个 Skill 能做什么

4. **使用场景**（150-200字）：描述2-3个具体的使用场景，让读者明白什么时候需要用这个 Skill

5. **快速上手**（100-150字）：
   - 如何安装这个 Skill（通常是克隆到 ~/.claude/skills/ 目录）
   - 如何在 Claude Code 中使用

6. **优缺点评估**：
   - 优点：3-4点（基于实际功能）
   - 不足：1-2点（客观真实）

7. **推荐指数**：⭐评分（1-5星）和一句话总结

8. **获取方式**：GitHub 链接

写作要求：
- 始终强调这是 Claude Code Skill，不是普通的软件工具
- 保持客观专业，不过度吹捧
- 使用中文撰写
- 适当使用 Markdown 格式"""

    content = call_openrouter_api(user_prompt, system_prompt)
    if content:
        # Add footer
        content += f"\n\n---\n\n*本文由「每日Skill精选」自动生成，每日为你推荐一款优质 Claude Code Skill。*"
        return content
    return None


def generate_article(skill: dict = None, generate_cover: bool = True) -> tuple:
    """
    Generate article for the selected skill.
    Returns (article_content, cover_image_path)
    """

    # Load selected skill if not provided
    if skill is None:
        selected_data = load_json(SELECTED_FILE)
        skill = selected_data.get("skill")

    if not skill:
        log("No skill selected for article generation")
        return None, None

    log(f"Generating article for: {skill.get('name')}")

    # Fetch additional details
    skill = fetch_skill_details(skill)

    # Try AI generation first
    article = generate_article_with_ai(skill)

    # Fallback to template
    if not article:
        log("Using template-based generation")
        article = generate_article_template(skill)

    # Generate cover image
    cover_path = None
    if generate_cover and OPENROUTER_API_KEY:
        log("Generating cover image...")
        cover_path = generate_cover_image(skill.get("name", "skill"), skill.get("description", ""))

    return article, cover_path


def save_article(article: str, skill: dict) -> Path:
    """Save article to output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    name = skill.get("name", "skill").replace(" ", "-").replace("/", "-")
    name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
    filename = f"{date_str}-{name}.md"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(article)

    log(f"Article saved to: {filepath}")
    return filepath


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Generate article for selected skill")
    parser.add_argument("--skill", "-s", help="Skill JSON file or JSON string")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--no-save", action="store_true", help="Don't save to default location")
    parser.add_argument("--no-cover", action="store_true", help="Don't generate cover image")
    args = parser.parse_args()

    # Load skill
    skill = None
    if args.skill:
        if os.path.exists(args.skill):
            with open(args.skill) as f:
                skill = json.load(f)
        else:
            try:
                skill = json.loads(args.skill)
            except json.JSONDecodeError:
                log(f"Invalid skill JSON: {args.skill}")
                return 1

    # Generate article
    article, cover_path = generate_article(skill, generate_cover=not args.no_cover)

    if not article:
        log("Failed to generate article")
        return 1

    # Get skill info for filename
    if skill is None:
        selected_data = load_json(SELECTED_FILE)
        skill = selected_data.get("skill", {})

    # Save article
    if not args.no_save:
        filepath = save_article(article, skill)
        if cover_path:
            log(f"Cover image: {cover_path}")

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(article)
        log(f"Article written to: {args.output}")
    else:
        print(article)

    return 0


if __name__ == "__main__":
    sys.exit(main())
