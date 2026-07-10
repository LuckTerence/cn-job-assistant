# Demo 样例

不用填自己简历，也不用登录 Boss。在仓库根目录：

```bash
bash scripts/demo.sh
# 或 make demo
```

会生成匹配摘要和本地投递表。浏览器打开：

`examples/demo/output/job_search_tracker.html`

## 这里有什么

| 文件 | 是啥 |
|------|------|
| `profile_snippet.md` | 假的候选人简介 |
| `jd_星云科技_后端.md` | 假的岗位描述（文件名带 `jd_` 只是习惯） |
| `resume_星云科技.md` | 假的定制简历 |
| `da-zhaohu_星云科技_后端.md` | 假的打招呼 |
| `resume_弱匹配.md` | 故意不对口的简历，用来对比分数 |
| `tracks/internet` / `tracks/soe` | 互联网 vs 国企各一套 |

## 真用时

`/setup-zh` → `/apply-zh`（贴岗位全文）→ 自己去 App 投 → `python tools/tracker.py add …`

更多见根目录 README。
