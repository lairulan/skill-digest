/**
 * Cloudflare Worker - 每日 Skill 精选定时触发器
 *
 * 功能：每天中午 12:00（北京时间）触发 GitHub Actions workflow
 *
 * Cron 表达式：0 4 * * * (UTC 04:00 = 北京时间 12:00)
 *
 * 部署步骤：
 * 1. 登录 Cloudflare Dashboard (https://dash.cloudflare.com)
 * 2. 进入 Workers & Pages
 * 3. 创建新 Worker，粘贴此代码
 * 4. 设置环境变量 GITHUB_TOKEN（需要 repo 和 workflow 权限）
 * 5. 添加 Cron Trigger: 0 4 * * *
 */

export default {
  // 定时任务处理
  async scheduled(event, env, ctx) {
    const result = await triggerWorkflow(env);
    console.log(`Skill Digest trigger result: ${JSON.stringify(result)}`);
  },

  // HTTP 请求处理（用于手动测试）
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/trigger') {
      const result = await triggerWorkflow(env);
      return new Response(JSON.stringify(result, null, 2), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({
      name: '每日 Skill 精选触发器',
      endpoints: {
        '/trigger': '手动触发 workflow'
      },
      cron: '0 4 * * * (每天北京时间 12:00)',
      repo: 'lairulan/skill-digest'
    }, null, 2), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
};

async function triggerWorkflow(env) {
  const GITHUB_TOKEN = env.GITHUB_TOKEN;
  const REPO = 'lairulan/skill-digest';

  if (!GITHUB_TOKEN) {
    return { success: false, error: 'GITHUB_TOKEN not configured' };
  }

  try {
    const response = await fetch(
      `https://api.github.com/repos/${REPO}/dispatches`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${GITHUB_TOKEN}`,
          'Accept': 'application/vnd.github.v3+json',
          'User-Agent': 'Cloudflare-Worker-Skill-Digest',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          event_type: 'daily-skill-digest'
        })
      }
    );

    if (response.status === 204) {
      return {
        success: true,
        message: 'Workflow triggered successfully',
        timestamp: new Date().toISOString()
      };
    } else {
      const text = await response.text();
      return {
        success: false,
        status: response.status,
        error: text
      };
    }
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}
