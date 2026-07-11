.PHONY: typecheck

typecheck:
	ty check src tests

.PHONY: test

test:
	coverage run -m pytest
	coverage report --show-missing
