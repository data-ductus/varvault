.PHONY: dependencies
dependencies:
	@echo "Installing dependencies for building and uploading a package to PyPi"
	@python3 -m pip install --upgrade build
	@python3 -m pip install --upgrade twine

.PHONY: clean
clean:
	@rm -rf dist/*
	@rm -rf build/*

.PHONY: build
build: clean
	@python3 -m build
	@tar tzf dist/varvault-*.tar.gz

.PHONY: upload
upload: test dependencies build
	@python3 -m twine upload dist/*

.PHONY: update-pip
update-pip:
	@python3 -m pip install -r requirements.txt

.PHONY: clear-logs
clear-logs:
	@rm -rf logs

.PHONY: test
test: clear-logs
	@coverage run --source=varvault -m pytest --tb=short --junitxml ./logs/test-report.xml -vvv --full-trace -p no:cacheprovider --html=./logs/test-report.html --self-contained-html $(shell ls tests/test_*.py)
	@coverage html -d ./logs/coverage-report
	@coverage json -o ./logs/coverage-report/coverage.json --pretty-print
	@python3 -c "import json; assert json.load(open('./logs/coverage-report/coverage.json'))['totals']['percent_covered'] == 100.0, 'Coverage is not 100%'" && echo "Coverage is 100%"

