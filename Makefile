setup:setup.py
	pip install -e .

setup-dev:setup.py
	pip install package_name[dev]

synth:
	cdk synth -o ./templates

deploy:
	cdk deploy --all --require-approval never

# sdist is the source distribution
bundle:
	rm -f dist/*
	python setup.py sdist bdist_wheel

review-bundle:
	tar tzf dist/*.gz

publish:
	twine upload --repository pypi --verbose dist/*