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
upload: dependencies build
	@python3 -m twine upload dist/*

.PHONY: update-pip
update-pip:
	@python3 -m pip install -r requirements.txt

.PHONY: test-vault
test-vault:
	pytest --tb=short --junitxml ./logs/test-vault-report.xml -vvv --full-trace -p no:cacheprovider --html=./logs/test-vault-report.html --self-contained-html tests/test_vault.py tests/test_large_scale_vault.py
