# CN Job Assistant — convenience targets
.PHONY: demo test lint help

help:
	@echo "make demo  - run offline product demo (match + tracker dashboard)"
	@echo "make test  - unit tests"
	@echo "make lint  - skill / zh / surface linters"

demo:
	bash scripts/demo.sh

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

lint:
	python3 tools/lint_skills.py
	python3 tools/lint_zh_refs.py
	python3 tools/lint_skill_surface.py
