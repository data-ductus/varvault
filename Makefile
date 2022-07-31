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

.PHONY: test
test:
	pytest --tb=short --junitxml ./logs/test-report.xml -vvv --full-trace -p no:cacheprovider --html=./logs/test-report.html --self-contained-html $(shell ls tests/test_*.py)

