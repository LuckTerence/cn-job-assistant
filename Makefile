# CN Job Assistant — convenience targets
.PHONY: demo test lint gif help

help:
	@echo "make demo  - run offline product demo (match + tracker dashboard)"
	@echo "make gif   - regenerate docs/assets/demo-loop.gif"
	@echo "make test  - unit tests"
	@echo "make lint  - skill / zh / surface linters"

demo:
	bash scripts/demo.sh

gif:
	python3 scripts/generate_demo_gif.py

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

lint:
	python3 tools/lint_skills.py
	python3 tools/lint_zh_refs.py
	python3 tools/lint_skill_surface.py
