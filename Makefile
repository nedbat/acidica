.PHONY: typecheck

typecheck:
	ty check src tests

.PHONY: test

test:
	coverage run --branch -m pytest
	coverage report --show-missing --skip-covered
	coverage html
