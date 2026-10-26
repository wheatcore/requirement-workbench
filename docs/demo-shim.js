// GitHub Pages demo adapter. It never contacts an AI provider or a local filesystem.
(() => {
  const defaultSkills = [
    {id: 'builtin-frontend-dev-workflow', role: 'frontend', name: 'frontend-dev-workflow', content: '先创建本地 feature 分支，再逐项实现、验证并提交。', default: true},
    {id: 'builtin-project-conventions', role: 'frontend', name: 'project-conventions', content: '遵守项目现有规范，运行相关检查。', default: false},
    {id: 'builtin-auto-commit-push', role: 'frontend', name: 'auto-commit-push', content: '逐项提交，不自动推送。', default: false},
    {id: 'builtin-backend-dev-workflow', role: 'backend', name: 'backend-dev-workflow', content: '按后端范围拆解、验证并提交。', default: true}
  ];
  let config;
  try {
    config = JSON.parse(localStorage.getItem('rw-public-demo-config') || 'null');
    if (!config || !Array.isArray(config.skills)) throw Error('empty');
  } catch {
    config = {version: 4, skills: defaultSkills};
  }
  const jobs = new Map();
  let nextJob = 0;
  const nativeFetch = window.fetch.bind(window);
  const project = '/demo/sample-web-app';

  function reply(data, status = 200) {
    return Promise.resolve(new Response(JSON.stringify(data), {
      status, headers: {'Content-Type': 'application/json; charset=utf-8'}
    }));
  }

  function planFor(payload) {
    const requirement = (payload.note || payload.url || payload.attachment?.name || '示例需求').trim();
    const headline = requirement.split(/[\n。！？]/)[0].slice(0, 46) || '示例需求';
    const frontend = payload.role !== 'backend';
    const parts = frontend ? [
      ['实现页面与基础交互', `根据“${headline}”搭建页面结构和主要交互。`, '页面可访问，主要控件响应正常。', 'feat: add page interaction'],
      ['接入数据与状态', '按已有接口或模拟数据处理加载、空状态和错误状态。', '列表与状态展示符合需求，异常提示清晰。', 'feat: handle data states'],
      ['补充验证', '针对关键路径补充适合项目的检查，并整理使用说明。', '相关检查通过，使用说明可复现。', 'test: cover main flow']
    ] : [
      ['定义接口与数据契约', `根据“${headline}”明确输入、输出和错误处理。`, '接口契约覆盖成功与异常情况。', 'feat: define api contract'],
      ['实现服务逻辑', '按现有架构实现业务逻辑与必要的数据变更。', '主流程及错误路径可用。', 'feat: implement service flow'],
      ['补充测试', '覆盖关键输入、权限与边界条件。', '相关测试通过。', 'test: cover service flow']
    ];
    return {summary: `在线演示计划：${headline}`, risks: ['本页仅模拟任务拆解；实际执行需要下载并在本机运行工作台。'],
      tasks: parts.map(([title, description, acceptance, commit_message]) => ({
        title, description, acceptance, commit_message,
        skills: [frontend ? 'frontend-dev-workflow' : 'backend-dev-workflow']
      }))};
  }

  window.fetch = (input, options = {}) => {
    const url = typeof input === 'string' ? input : input.url;
    if (!url.startsWith('/api/')) return nativeFetch(input, options);
    const body = options.body ? JSON.parse(options.body) : {};
    if (url === '/api/health') return reply({ok: true, providers: {codex: {installed: true}, claude: {installed: true, authenticated: true}}});
    if (url === '/api/config') {
      if (options.method === 'POST') {
        config = body;
        localStorage.setItem('rw-public-demo-config', JSON.stringify(config));
      }
      return reply(config);
    }
    if (url.startsWith('/api/project')) {
      const path = new URL(url, location.href).searchParams.get('path') || project;
      return reply({path, branch: 'main', clean: true, status: '', guidance: []});
    }
    if (url === '/api/browse-folders') {
      const path = body.path || '/demo';
      return reply({path, parent: path === '/demo' ? '' : '/demo', directories: path === '/demo' ?
        [{name: 'sample-web-app', path: project, git: true}] : [], more: false});
    }
    if (url === '/api/plan' || url === '/api/run') {
      const id = `demo-${++nextJob}`;
      const planning = url === '/api/plan';
      const job = {kind: planning ? 'plan' : 'run', state: 'running', stage: planning ? '模拟拆解任务' : '模拟调用 Skills',
        logs: ['在线演示模式：没有请求 AI，也没有读取或修改本机文件。'], result: null, error: null};
      jobs.set(id, job);
      setTimeout(() => {
        if (job.state !== 'running') return;
        if (planning) {
          job.stage = '模拟计划已生成';
          job.logs.push('已生成可编辑的示例任务。');
          job.result = {project: body.project || project, plan: planFor(body)};
        } else {
          job.stage = '模拟执行已完成';
          const branch = 'feature/demo-workflow';
          const commits = (body.plan?.tasks || []).map((task, i) => ({task: task.title,
            sha: `demo${String(i + 1).padStart(3, '0')}`, message: task.commit_message,
            summary: '模拟记录，未修改代码或创建真实 Git commit'}));
          job.logs.push(`模拟创建并切换到 ${branch}`, '按编辑后的顺序逐项展示提交记录。', '演示结束：所有分支、文件与 commit 均为模拟。');
          job.result = {project: body.project || project, provider: body.provider, branch, commits};
        }
        job.state = 'done';
      }, planning ? 350 : 950);
      return reply({job_id: id}, 202);
    }
    const match = url.match(/^\/api\/jobs\/([^/]+)(\/cancel)?$/);
    if (match) {
      const job = jobs.get(match[1]);
      if (!job) return reply({error: '任务不存在'}, 404);
      if (match[2]) {job.state = 'error'; job.error = '已停止模拟'; return reply({ok: true});}
      return reply(job);
    }
    return reply({error: '此功能只在本地版可用'}, 404);
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('.topline > span:first-child').textContent = 'INTERACTIVE DEMO / 01';
    document.getElementById('hero-eyebrow').textContent = '浏览器内交互演示';
    document.getElementById('hero-title').innerHTML = '把需求拆成任务，<br><em>预演交付流程。</em>';
    document.getElementById('hero-description').textContent = '体验需求输入、任务编辑、Skills 选择和模拟提交。真实 AI 执行与 Git 修改需在自己的电脑上运行开源版。';
    document.getElementById('rail-foot-text').textContent = '本页仅模拟，不访问本机项目';
    document.getElementById('flow-3').textContent = '模拟 Skill、分支和逐项提交';
    document.getElementById('plan-button').textContent = '模拟拆解任务 →';
    document.getElementById('run-button').textContent = '模拟执行并查看提交 →';
    document.getElementById('url').placeholder = '演示页不会读取 URL 正文，可在下方粘贴需求';
    document.querySelector('#url + .hint').textContent = '演示页只使用你输入的文字或 URL 字符串，不访问目标网页。真实读取需求请使用本地版。';
    document.querySelector('label[for="project"]').textContent = '演示项目（虚拟）';
    document.querySelector('label[for="verify-command"]').textContent = '验证命令（演示中禁用）';
    document.querySelector('#verify-command + .hint').textContent = '真实版会在每项提交前运行你填写的验证命令。';
    document.querySelector('#run-section .section-head h2').textContent = '03 / 模拟执行与提交';
    document.querySelector('#run-section .section-head small').textContent = '没有真实文件或 Git 操作';
    document.getElementById('verify-command').disabled = true;
    document.getElementById('verify-command').placeholder = '在线演示不运行验证命令';
    document.getElementById('note').value = '实现一个任务列表：支持关键词筛选、分页、空状态，以及加载失败时的提示。';
    const input = document.getElementById('project');
    input.value = project;
    input.dispatchEvent(new Event('input', {bubbles: true}));
    const banner = document.createElement('div');
    banner.className = 'demo-banner';
    banner.innerHTML = '<strong>在线演示 · 所有 AI 与 Git 操作均为模拟</strong><span>输入内容只在当前浏览器处理。想用自己的 Codex / Claude 和 Git 仓库，请下载并运行本地版。</span><a href="https://github.com/wheatcore/requirement-workbench">查看开源代码 ↗</a>';
    document.querySelector('main').prepend(banner);
  });
})();
