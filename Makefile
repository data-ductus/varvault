PYTHON_REPOSITORY = testpypi

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

.PHONY: upload
upload:
	@python3 -m twine upload --repository $(PYTHON_REPOSITORY) dist/*

.PHONY: update-pip
update-pip:
	@python3 -m pip install -r requirements.txt

.PHONY: test-vault
test-vault:
	pytest --tb=short --junitxml ./logs/test-vault-report.xml -vvv --full-trace -p no:cacheprovider --html=./logs/test-vault-report.html --self-contained-html test/test_vault.py test/test_large_scale_vault.py
