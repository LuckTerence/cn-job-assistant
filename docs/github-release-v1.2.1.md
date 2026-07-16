# CN Job Assistant v1.2.1

## Highlights

- **投前质量门禁** `quality_gate`（1.2.0）：匹配 + 诚信 + ATS
- **1.2.1 修复**：量化数字不再误杀真实简历；serve 精确改状态；打分缓存；看板匹配卡片；demo 全接线

## Install

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
git checkout v1.2.1
make check
```

## Quick commands

```bash
python tools/quality_gate.py --resume r.md --jd j.md --pdf r.pdf
python tools/match_resume.py align --resume r.md --jd j.md
python tools/tracker.py match-outcome
python tools/tracker.py serve
```

See `docs/ats-gate.zh.md` · `CHANGELOG.md` · `docs/COMMAND_MAP.zh.md`.

## Notes

- Default remains **manual apply** (no mass auto-submit).
- Match score is local keyword alignment, not an offer predictor.
- GitHub Release UI: after `gh auth login`,  
  `gh release create v1.2.1 -F docs/github-release-v1.2.1.md --title "v1.2.1"`
