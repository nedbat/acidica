.PHONY: ty mypy

ty:
	ty check src tests

mypy:
	mypy --strict src tests

pyright:
	pyright

.PHONY: test

test:
	python -m pytest --cov=src --cov=tests --cov-context=test --cov-report= tests
	coverage report --show-missing --skip-covered
	coverage html --show-contexts

.PHONY: clean

clean:
	rm -rf .coverage .coverage.* htmlcov
	rm -rf build
	rm -rf src/acidica.egg-info
