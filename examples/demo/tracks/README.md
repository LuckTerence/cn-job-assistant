# 分赛道样例（看得见的差异）

同一产品，**互联网**与**国企**产出气质不同——这是差异化卖点，不是同一套话术换皮。

| 赛道 | 目录 | 简历气质 | 开场形态 |
|------|------|----------|----------|
| 互联网 | `internet/` | 量化业绩、技术栈、高并发 | Boss 短打招呼 |
| 国企央企 | `soe/` | 规范、党员、等保/信创、文档 | 正式求职信 |

## 一键对比打分

在仓库根目录：

```bash
# 互联网样例
python tools/match_resume.py report --zh-only \
  --resume examples/demo/tracks/internet/resume.md \
  --jd examples/demo/tracks/internet/jd.md \
  --cover examples/demo/tracks/internet/da-zhaohu.md

# 国企样例
python tools/match_resume.py report --zh-only \
  --resume examples/demo/tracks/soe/resume.md \
  --jd examples/demo/tracks/soe/jd.md \
  --cover examples/demo/tracks/soe/cover.md
```

或跑总 demo（含赛道对比）：

```bash
bash scripts/demo.sh
```

模板规范见 `templates/zh/resume_internet.md` 与 `templates/zh/resume_soe.md`。
