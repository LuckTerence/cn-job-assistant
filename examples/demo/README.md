# Demo 样例

不用填自己简历，也不用登录 Boss。在仓库根目录：

```bash
bash scripts/demo.sh
# 或 make demo
```

会生成 **可投递 PDF 简历**、匹配摘要、本地投递表，以及 **不投原因（skip）样例**。

- PDF：`examples/demo/output/resume_星云科技.pdf`
- 看板：`examples/demo/output/job_search_tracker.html`（含待办 + 不投信号卡片）
- 不投分布：`examples/demo/output/skip_stats.txt`

## 这里有什么

| 文件 | 是啥 |
|------|------|
| `examples/demo/profile_snippet.md` | 假的候选人简介 |
| `examples/demo/jd_星云科技_后端.md` | 假的岗位描述（文件名带 `jd_` 只是习惯） |
| `examples/demo/resume_星云科技.md` | 假的定制简历 |
| `examples/demo/da-zhaohu_星云科技_后端.md` | 假的打招呼 |
| `examples/demo/resume_弱匹配.md` | 故意不对口的简历，用来对比分数 |
| `examples/demo/tracks/` | 互联网 vs 国企各一套 |
| `examples/demo/output/skip_stats.txt` | demo 跑完后的不投原因分布（生成物） |
| `examples/demo/jobs_sample.json` | 搜岗结果样例 → `import-jobs` 批量入库 |
| `examples/demo/output/import_jobs.txt` | import 运行日志（生成物） |

Tracker 演示行大致包含：已投 / 面试中 / 已拒 + 3 条 `skipped`（`salary_low` / `location` / `low_match`）  
+ `import-jobs` 导入的若干 `to_apply` 短名单，用来展示 Phase 1 信号面与搜岗入库。

## 真用时

`/setup-zh` → `/apply-zh`（贴岗位全文 → 出 **PDF**）→ 用 PDF 去 App 投 **或** 不投记 `skipped` →  
`python tools/tracker.py add/update …` / `/outcome` 更新结果 → `skip-stats` / `today`

单独导出 PDF：

```bash
python tools/export_resume_pdf.py -i documents/zh/resume_公司.md
```

更多见根目录 README。
