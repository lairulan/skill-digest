# Skill Digest - 每日 Claude Skill 精选推送

自动化工作流，每天从 Claude Skill 聚合网站精选 1 条优质技能，生成 800-1200 字的评测推荐型文章，并推送到微信公众号。

## 功能特点

- **自动获取技能**：从 GitHub awesome-claude-skills 获取最新技能列表
- **智能选择**：去重、多样化分类，避免重复推荐
- **AI 文章生成**：使用 Qwen 2.5 72B 生成高质量中文评测文章
- **AI 封面配图**：使用 GPT-5 Image 生成精美封面图
- **自动发布**：发布到微信公众号草稿箱

## 技术栈

| 功能 | 技术 |
|------|------|
| 文章生成 | OpenRouter API + Qwen 2.5 72B |
| 封面配图 | OpenRouter API + GPT-5 Image |
| 定时触发 | Cloudflare Workers Cron Triggers |
| CI/CD | GitHub Actions |
| 发布渠道 | 微绿流量宝 API → 微信公众号 |

## 目录结构

```
skill-digest/
├── .github/workflows/
│   └── daily-skill-digest.yml  # GitHub Actions 工作流
├── scripts/
│   ├── fetch_skills.py         # 获取技能列表
│   ├── select_daily.py         # 智能选择今日精选
│   ├── generate_article.py     # 生成评测文章
│   ├── auto_publish.py         # 自动发布脚本
│   └── daily-skill-digest.sh   # 本地执行脚本
├── data/
│   └── published_skills.json   # 已发布技能记录
├── SKILL.md                    # Claude Code 技能配置
└── README.md
```

## 配置

### GitHub Secrets

需要在 GitHub 仓库设置以下 Secrets：

| Secret | 说明 |
|--------|------|
| `OPENROUTER_API_KEY` | OpenRouter API 密钥（用于文章和封面生成） |
| `SANGENG_API_KEY` | 微绿流量宝 API 密钥（用于微信发布） |

### Cloudflare Workers

参考 daily-tech-news 的 Cloudflare Workers 配置，设置 Cron Trigger：

```javascript
// 每天中午 12:00 北京时间 (UTC 04:00)
export default {
  async scheduled(event, env, ctx) {
    const response = await fetch(
      'https://api.github.com/repos/YOUR_USERNAME/skill-digest/dispatches',
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
          'Accept': 'application/vnd.github.v3+json',
          'User-Agent': 'Cloudflare-Worker'
        },
        body: JSON.stringify({ event_type: 'daily-skill-digest' })
      }
    );
    return new Response('OK');
  }
}
```

Cron 表达式：`0 4 * * *` (UTC 时间，对应北京时间 12:00)

## 本地使用

### 手动执行

```bash
# 设置环境变量
export OPENROUTER_API_KEY="your-api-key"
export SANGENG_API_KEY="your-api-key"

# 运行完整流程
~/.claude/skills/skill-digest/scripts/daily-skill-digest.sh
```

### 单独执行各步骤

```bash
# 1. 获取技能列表
python3 scripts/fetch_skills.py --refresh

# 2. 选择今日精选
python3 scripts/select_daily.py

# 3. 生成文章
python3 scripts/generate_article.py

# 4. 标记已发布
python3 scripts/select_daily.py --mark-published
```

## 数据源

- [awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) - GitHub 技能聚合列表

## 输出示例

生成的文章结构：

1. **标题**：今日发现：[技能名] - [一句话亮点]
2. **简介**：50-80字说明
3. **核心能力**：3-4个主要功能点
4. **使用场景**：2-3个具体场景
5. **快速上手**：安装和使用步骤
6. **优缺点评估**：客观分析
7. **推荐指数**：⭐ 评分
8. **获取方式**：GitHub 链接

## License

MIT
