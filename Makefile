# CN Job Assistant — convenience targets
.PHONY: demo test lint smoke help

help:
	@echo "make demo   - offline product demo"
	@echo "make test   - unit tests"
	@echo "make lint   - skill / zh / surface linters"
	@echo "make smoke  - 1.0 product-path offline smoke (no network)"
	@echo "make check  - test + smoke (release gate)"

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

check: test smoke
	@echo "check OK ✓"
