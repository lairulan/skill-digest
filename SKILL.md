---
name: skill-digest
description: 每日 Claude Skill 精选推送。自动从 Claude Skill 聚合网站精选技能，生成评测推荐文章，发布到微信公众号。
triggers:
  - skill digest
  - 技能精选
  - 推送技能
  - skill推荐
  - 每日技能
---

# Skill Digest - 每日 Claude Skill 精选推送

## 功能概述

自动化工作流，每天从 Claude Skill 聚合网站精选 1 条优质技能，生成 800-1200 字的评测推荐型文章，并推送到「三更AI」公众号。

## 数据源

- GitHub Awesome Claude Skills: `https://github.com/travisvn/awesome-claude-skills`
- SkillsMP: `https://skillsmp.com`
- OneSkill: `https://oneskill.dev`

## 文章模板

生成的评测文章包含以下结构：

1. **标题**: 今日发现：[Skill名称] - [一句话亮点]
2. **简介**: 50-80字说明技能用途
3. **核心能力**: 3-4个主要功能点
4. **使用场景**: 2-3个具体使用场景
5. **快速上手**: 安装和使用步骤
6. **优缺点评估**: 客观分析
7. **推荐指数**: ⭐ 评分和总结
8. **获取方式**: GitHub 链接或安装命令

## 使用方式

### 手动触发

```bash
# 运行完整的每日精选流程
~/.claude/skills/skill-digest/scripts/daily-skill-digest.sh

# 仅获取技能列表
python3 ~/.claude/skills/skill-digest/scripts/fetch_skills.py

# 仅选择今日精选
python3 ~/.claude/skills/skill-digest/scripts/select_daily.py

# 仅生成文章（需要先选择技能）
python3 ~/.claude/skills/skill-digest/scripts/generate_article.py
```

### 定时任务

已配置 LaunchAgent 在每天中午 12:00 自动执行：
- 配置文件: `~/Library/LaunchAgents/com.claude.skill-digest.plist`

```bash
# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.claude.skill-digest.plist

# 卸载定时任务
launchctl unload ~/Library/LaunchAgents/com.claude.skill-digest.plist

# 查看任务状态
launchctl list | grep skill-digest
```

## 去重机制

系统会记录已发布的技能，避免重复推荐：
- 记录文件: `~/.claude/skills/skill-digest/data/published_skills.json`

选择策略：
1. 排除已发布的技能
2. 优先选择最近更新的技能
3. 多样化分类（避免连续推荐同类型）

## 文件说明

| 文件 | 说明 |
|------|------|
| `scripts/fetch_skills.py` | 从聚合网站获取技能列表 |
| `scripts/select_daily.py` | 智能选择今日精选 |
| `scripts/generate_article.py` | 生成评测文章 |
| `scripts/daily-skill-digest.sh` | 定时任务主脚本 |
| `data/published_skills.json` | 已发布技能记录 |
| `data/skill_cache.json` | 技能缓存 |
| `logs/daily.log` | 执行日志 |

## 依赖配置

需要以下环境变量：
- `DOUBAO_API_KEY`: 豆包 API 密钥（用于文章润色和封面图生成）
- `SANGENG_API_KEY`: 微绿流量宝 API 密钥（用于公众号发布）

## 输出位置

- 生成的文章: `~/Documents/Obsidian/ai自动生成/skill-digest/`
- 日志文件: `~/.claude/skills/skill-digest/logs/`

## 日志查看

```bash
# 查看最新日志
tail -f ~/.claude/skills/skill-digest/logs/daily.log

# 查看标准输出
tail -f ~/.claude/skills/skill-digest/logs/stdout.log

# 查看错误日志
tail -f ~/.claude/skills/skill-digest/logs/stderr.log
```
