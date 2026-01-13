.PHONY: install project lint format build publish package-install clean

install:
	poetry install

project:
	poetry run project

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

build:
	poetry build

publish:
	poetry publish --build

package-install:
	python -m pip install --upgrade pip
	python -m pip install --force-reinstall dist/*.whl

clean:
	rm -rf .ruff_cache .pytest_cache .mypy_cache dist build __pycache__
