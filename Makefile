.ONESHELL:

code_clean:
	isort .
	black -S -l120 *.py
	cd publish
	black -S -l120 *.py
	cd ..
