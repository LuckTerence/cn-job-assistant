# Demo 产出预览（预生成，可直接看）

> 由 `bash scripts/demo.sh` 生成。数字随算法微调可能变化；以你本地重跑结果为准。

## 匹配质量（强匹配简历）

典型结果量级：

| 指标 | 约值 |
|------|------|
| 综合分 combined_score | ~50–60 / 100 |
| 关键词覆盖 | ~70–85% |
| verdict | moderate_match |
| 弱匹配对照分 | ~0–5 |

**命中示例：** Java、Go、Spring Boot、Kafka、Redis、MySQL、Docker、K8s、微服务、高并发…  
**仍缺示例：** 大模型 / LLM、英语…（演示候选人未写，报告会诚实列出，**勿虚构补全**）

详见同目录文件（勿加 `./` 前缀，避免被文档扫描误判）：

- `examples/demo/output/match_report.txt` — 人类可读  
- `examples/demo/output/match_report.json` — 机器可读  

## 投递看板

打开 `examples/demo/output/job_search_tracker.html` 可见 3 条演示记录：

| 公司 | 状态 | 渠道 |
|------|------|------|
| 星云科技 | applied | Boss直聘 |
| 青梧数据 | interview | 智联 |
| 北岸出行 | rejected | 猎聘 |

## 重跑

```bash
# 仓库根目录
bash scripts/demo.sh
# 或
make demo
```
