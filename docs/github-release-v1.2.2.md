# CN Job Assistant v1.2.2

## Highlights (1.2.x)

- **投前质量门禁** `quality_gate`：匹配 + 诚信 + ATS；「改这 3 条」
- **1.2.1**：量化数字不再误杀；serve 精确改状态；打分缓存；看板匹配卡片
- **1.2.2**：投递后写 `match_score` 提示；`make release-gh`；`flow gate` 门槛透传

## Install

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
git checkout v1.2.2
make check
```

## Quick commands

```bash
python tools/quality_gate.py --resume r.md --jd j.md --pdf r.pdf
python tools/match_resume.py align --resume r.md --jd j.md
python tools/tracker.py match-outcome
python tools/tracker.py serve
make release-gh   # after: gh auth login
```

See `docs/ats-gate.zh.md` · `CHANGELOG.md` · `docs/COMMAND_MAP.zh.md`.

## Notes

- Default remains **manual apply** (no mass auto-submit).
- Match score is local keyword alignment, not an offer predictor.
