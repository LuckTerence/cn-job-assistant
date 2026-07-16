# CN Job Assistant — convenience targets
.PHONY: demo test lint smoke check quick release-ready package help

help:
	@echo "make demo          - offline product demo"
	@echo "make test          - unit tests"
	@echo "make lint          - skill / zh / surface linters"
	@echo "make smoke         - 1.0 product-path offline smoke (no network)"
	@echo "make check         - test + smoke (release gate)"
	@echo "make release-ready - version/docs packaging assert"
	@echo "make package       - Red Skill zip (scripts/package_for_redskill.sh)"
	@echo "make quick         - print 15-min path pointer"

demo:
	bash scripts/demo.sh

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

lint:
	python3 tools/lint_skills.py
	python3 tools/lint_zh_refs.py
	python3 tools/lint_skill_surface.py

smoke:
	bash scripts/smoke_cn.sh

check: release-ready test smoke
	@echo "check OK ✓"

release-ready:
	python3 tools/check_release_ready.py

package:
	bash scripts/package_for_redskill.sh

quick:
	@echo "→ docs/QUICKSTART.zh.md"
	@echo "→ make check && open examples/demo/output/job_search_tracker.html"
	@echo "→ Agent: /setup-zh then /apply-zh  (or docs/AGENT_PROMPT.zh.md)"
	@echo "→ Release: bash scripts/publish_github_release.sh  (needs gh auth login)"
