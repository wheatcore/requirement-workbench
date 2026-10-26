"""Build the static GitHub Pages demo from the local workbench UI."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "requirement_workbench" / "index.html").read_text(encoding="utf-8")


def replace_once(before: str, after: str) -> None:
    global source
    if source.count(before) != 1:
        raise RuntimeError(f"Demo source marker missing or repeated: {before[:70]}")
    source = source.replace(before, after, 1)


replace_once("<script>\n  const $=id=>", '<script src="./demo-shim.js"></script>\n<script>\n  const DEMO_MODE=true;\n  const $=id=>')
replace_once("<title>需求工作台 · Requirement Workbench</title>", '<title>需求工作台 · 在线交互演示</title>\n  <meta name="description" content="在线体验需求拆解、任务编辑和逐项提交的模拟流程；真实 Codex 与 Claude 执行在本机完成。">')
replace_once("</style>", """.demo-banner{display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:#fff2de;border:1px solid #edc995;color:#614629;padding:13px 17px;border-radius:10px;font-size:12px;margin-bottom:18px;line-height:1.5}.demo-banner strong{font-weight:850}.demo-banner span{flex:1;min-width:220px}.demo-banner a{color:#8f4a2e;font-weight:800;white-space:nowrap;text-decoration:none}.demo-banner a:hover{text-decoration:underline}
  </style>""")
replace_once("$('cli-status').textContent=status;$('provider-hint').textContent=hint", "$('cli-status').textContent=DEMO_MODE?'● 在线演示':status;$('provider-hint').textContent=DEMO_MODE?'此页模拟流程；本地版可连接你的 Codex 或 Claude CLI。':hint")
replace_once("function requireProvider(){const info=", "function requireProvider(){if(DEMO_MODE)return;const info=")
replace_once("$('job-title').textContent='全部任务已完成'", "$('job-title').textContent='模拟执行已完成'")
replace_once("$('job-title').textContent=`${providerName()} 正在执行`", "$('job-title').textContent=`${providerName()} 模拟执行中`")
replace_once("$('plan-title').textContent=`${providerName()} 正在拆解任务`", "$('plan-title').textContent=`${providerName()} 模拟拆解中`")
replace_once("toast(`已在 ${job.result.branch||'当前分支'} 创建 ${job.result.commits.length} 个 commit`)", "toast(`模拟完成：${job.result.commits.length} 条提交记录，没有修改文件`)")
replace_once("box.textContent=`${data.branch} · ${data.clean?'工作区干净，可以逐项提交':'有未提交改动，执行前需要处理'}`", "box.textContent=DEMO_MODE?'main · 演示项目（虚拟）':`${data.branch} · ${data.clean?'工作区干净，可以逐项提交':'有未提交改动，执行前需要处理'}`")
replace_once("terminal.textContent=planning?`正在读取需求并连接 ${providerName()} CLI…`:`正在连接 ${providerName()} CLI…`", "terminal.textContent=planning?'正在模拟拆解需求…':'正在模拟执行…'")
source, count = re.subn(r"if\(!confirm\(`将使用 \$\{providerName\(\)\}.*?继续吗？`\)\)return;",
                        "if(!confirm('在线演示只生成模拟日志和提交记录，不修改任何文件。继续吗？'))return;", source, count=1)
if count != 1:
    raise RuntimeError("Demo confirmation marker missing")

target = ROOT / "docs" / "index.html"
target.write_text(source, encoding="utf-8")
print(target)
