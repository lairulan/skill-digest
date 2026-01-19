# Cloudflare Worker 部署指南

## 每日 Skill 精选 - 定时触发器

### 功能
每天北京时间 12:00 自动触发 GitHub Actions workflow，执行每日 Skill 精选推送。

### Cron 表达式
```
0 4 * * *
```
(UTC 04:00 = 北京时间 12:00)

### 部署步骤

#### 1. 创建 GitHub Personal Access Token

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选权限：
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows)
4. 生成并复制 token

#### 2. 创建 Cloudflare Worker

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 进入 **Workers & Pages**
3. 点击 **Create Worker**
4. 将 `worker.js` 的内容粘贴到编辑器
5. 点击 **Save and Deploy**

#### 3. 配置环境变量

1. 在 Worker 设置页面，找到 **Settings** > **Variables**
2. 添加环境变量：
   - 名称: `GITHUB_TOKEN`
   - 值: 第 1 步创建的 GitHub Token
3. 点击 **Encrypt** 加密保存

#### 4. 添加 Cron Trigger

1. 在 Worker 设置页面，找到 **Triggers** > **Cron Triggers**
2. 点击 **Add Cron Trigger**
3. 输入 Cron 表达式: `0 4 * * *`
4. 保存

### 测试

#### 手动测试 Worker
访问 Worker URL 的 `/trigger` 路径：
```
https://your-worker.your-subdomain.workers.dev/trigger
```

#### 查看 GitHub Actions
```bash
gh run list --repo lairulan/skill-digest --limit 5
```

### 监控

#### 查看 Worker 日志
在 Cloudflare Dashboard 的 Worker 页面查看 **Logs**

#### 查看 GitHub Actions 日志
```bash
gh run view <run-id> --repo lairulan/skill-digest --log
```

### 故障排除

| 问题 | 解决方案 |
|------|---------|
| 401 Unauthorized | 检查 GITHUB_TOKEN 是否正确 |
| 404 Not Found | 检查仓库名称是否正确 |
| Workflow 未触发 | 确认 workflow 支持 repository_dispatch |
