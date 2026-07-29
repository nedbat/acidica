.PHONY: typecheck

typecheck:
	ty check src tests

.PHONY: mypy

mypy:
	mypy  src tests

.PHONY: test

test:
	python -m pytest --cov=src --cov=tests --cov-context=test --cov-report=
	coverage report --show-missing --skip-covered
	coverage html --show-contexts

.PHONY: clean

clean:
	rm -rf .coverage .coverage.* htmlcov
	rm -rf build
	rm -rf src/acidica.egg-info
