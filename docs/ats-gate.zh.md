# 投前质量门禁与 AI/ATS 过筛（1.2）

> 国内「AI 筛简历」通常是三层：**解析 → 关键词/规则 → 人/强模型二筛**。  
> 本仓库用**本地工具**应对前两层，第三层靠真实量化与去 AI 腔——不自研商业 Jobscan。

---

## 一键门禁

```bash
# 匹配 + 画像诚信 + ATS 文本层（有 PDF / pdftotext 时）
python tools/quality_gate.py \
  --resume documents/zh/resume_公司.md \
  --jd documents/zh/jd_公司_岗位.md \
  --cover documents/zh/da-zhaohu_公司_岗位.md \
  --profile CLAUDE.zh.md \
  --pdf documents/zh/resume_公司.pdf \
  --out documents/zh/gate_公司.json

# 尚无 PDF 时一并导出
python tools/quality_gate.py --resume r.md --jd j.md --export-pdf --template classic

# 薄封装
python tools/flow.py gate --resume r.md --jd j.md --pdf r.pdf
```

| 状态 | 退出码 | 含义 |
|------|--------|------|
| PASS | 0 | 默认可投 |
| SOFT_FAIL | 1 | 匹配弱 / 覆盖低 / ATS 警告 → 先「改这 3 条」；确认后 `--force` |
| HARD_FAIL | 2 | 诚信高严重度 → 先修；仅知情后 `--force-hard` |

门槛默认：`score ≥ 40`、`coverage ≥ 25%`；可用 `--min-score` / `--min-coverage` 调整。

---

## 双格式交付

| 文件 | 用途 |
|------|------|
| `resume_*.md` | **粘贴稿**（站内表单、IM、可复制纯文本） |
| `resume_*.pdf` | **上传稿**（附件；单栏 classic / compact） |

版式「简约」是刻意的：单栏 + 真文字层，比多栏炫技更利于解析。

```bash
python tools/export_resume_pdf.py -i resume.md --ats-checklist
# 可选：brew install poppler   # 提供 pdftotext
```

---

## 「改这 3 条」与 JD 对齐

```bash
python tools/match_resume.py report --resume … --jd … --zh-only
python tools/match_resume.py align  --resume … --jd …   # 只要行动清单
```

规则：

1. 只会的技能才写进 bullet；不会的保持 **真缺口** 可见  
2. 优先补 **核心硬技能** miss，再考虑 nice-to-have  
3. 同义词已对齐时，空间允许可再写 **JD 原词**（机筛更稳）  
4. **禁止**为刷分虚构经历（`check_profile_resume` / 门禁 HARD）

---

## 结果归因（质量飞轮）

投递时把门禁分数写入 tracker：

```bash
python tools/tracker.py add … \
  --match-score 72 --match-coverage 55 --match-verdict moderate_match

# 或批打分回写
python tools/tracker.py rank --write-fit

# 一段时间后
python tools/tracker.py match-outcome
python tools/tracker.py skip-stats
```

看 high / mid / low 带的进面率，而不是迷信单次分数。

---

## 和竞品边界

| 做 | 不做 |
|----|------|
| 本地 TF–IDF + 同义词 + 诚信 + 文本层 | 默认 embedding / 云端 ATS 打分 |
| 强制门禁进 `/apply-zh` | 自动灌词到 95 分 |
| 单栏 Typst + md 粘贴 | 花哨多栏「显高级」模板 |
| 手动 / semi 投递 | 默认海投代点 |

详见 [COMMAND_MAP.zh.md](./COMMAND_MAP.zh.md)、[resume-pdf-reuse.zh.md](./resume-pdf-reuse.zh.md)。
