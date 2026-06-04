.PHONY: requirements test quality build clean

requirements: ## Install runtime and test/quality dependencies
	pip install -r requirements-test.txt

quality: ## Run style/lint checks
	flake8 openedx_rest_api_client tests
	pylint openedx_rest_api_client

test: quality ## Run quality checks and the unit test suite
	pytest tests/ --cov=openedx_rest_api_client --cov-report=term-missing

build: ## Build the source distribution and wheel
	pip install build
	python -m build

clean: ## Remove build artifacts
	rm -rf build dist *.egg-info
