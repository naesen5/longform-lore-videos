# Makefile for longform-lore-videos

.PHONY: test lint typecheck ci format ui

test:
	@pytest -v --tb=short --cov=longform_lore_videos --cov-report=term-missing --cov-fail-under=80

lint:
	@ruff check .

typecheck:
	@mypy longform_lore_videos/ --ignore-missing-imports

ci: test lint typecheck

format:
	@ruff check . --fix

ui:
	@python gradio_app.py
