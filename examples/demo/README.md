# Demo 样例包（无需真实简历 / 无需登录 Boss）

> 目标：clone 仓库后 **一条命令** 看到「匹配质量报告 + 投递看板」，理解产品产出长什么样。  
> 全部为**虚构脱敏**数据，仅供演示。

## 一键跑

在仓库根目录：

```bash
bash scripts/demo.sh
```

或：

```bash
make demo
```

## 你会看到什么

| 产物 | 路径 |
|------|------|
| 匹配质量报告（JSON） | `examples/demo/output/match_report.json` |
| 匹配摘要（终端也会打印） | 同上 + stdout |
| 投递 Tracker CSV | `examples/demo/output/job_search_tracker.csv` |
| HTML 看板 | `examples/demo/output/job_search_tracker.html` |

用浏览器打开 HTML 即可预览看板。

## 样例文件说明

| 文件 | 含义 |
|------|------|
| `examples/demo/profile_snippet.md` | 虚构候选人画像摘要（对应真实流程里的 `CLAUDE.zh.md`） |
| `examples/demo/jd_星云科技_后端.md` | 虚构岗位描述 |
| `examples/demo/resume_星云科技.md` | 按岗位描述定制后的中文简历草稿（`/apply-zh` 类产出） |
| `examples/demo/da-zhaohu_星云科技_后端.md` | Boss 风格打招呼话术 |
| `examples/demo/resume_弱匹配.md` | 对照用：弱匹配简历（分数应明显更低） |

## 和真实流程的对应

```text
demo 样例文件          真实使用时
─────────────────    ────────────────────────────
profile_snippet   →  /setup-zh → CLAUDE.zh.md
jd_*.md           →  搜岗后粘贴 / documents/zh/jd_*
resume_*.md       →  /apply-zh → documents/zh/resume_*
da-zhaohu_*.md    →  /apply-zh 或 /da-zhaohu
match_report.json →  tools/match_resume.py report
tracker csv/html  →  tools/tracker.py
```

## 下一步（真实求职）

1. `/setup-zh` 填自己的画像  
2. `python tools/install_domestic_search.py install-boss`（可选）  
3. `/apply-zh <你的岗位描述>`  
4. App 内手动投递 → `python tools/tracker.py add …`  

详见仓库根目录 [README.md](../../README.md)。
