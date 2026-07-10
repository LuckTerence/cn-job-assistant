# Demo 样例

不用填自己简历，也不用登录 Boss。在仓库根目录：

```bash
bash scripts/demo.sh
# 或 make demo
```

会生成 **可投递 PDF 简历**、匹配摘要和本地投递表。

- PDF：`examples/demo/output/resume_星云科技.pdf`
- 看板：`examples/demo/output/job_search_tracker.html`

## 这里有什么

| 文件 | 是啥 |
|------|------|
| `examples/demo/profile_snippet.md` | 假的候选人简介 |
| `examples/demo/jd_星云科技_后端.md` | 假的岗位描述（文件名带 `jd_` 只是习惯） |
| `examples/demo/resume_星云科技.md` | 假的定制简历 |
| `examples/demo/da-zhaohu_星云科技_后端.md` | 假的打招呼 |
| `examples/demo/resume_弱匹配.md` | 故意不对口的简历，用来对比分数 |
| `examples/demo/tracks/` | 互联网 vs 国企各一套 |

## 真用时

`/setup-zh` → `/apply-zh`（贴岗位全文 → 出 **PDF**）→ 用 PDF 去 App 投 → `python tools/tracker.py add …`

单独导出 PDF：

```bash
python tools/export_resume_pdf.py -i documents/zh/resume_公司.md
```

更多见根目录 README。
