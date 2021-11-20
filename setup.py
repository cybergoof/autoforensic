import setuptools
import pathlib
import pkg_resources

current_directory = pathlib.Path(__file__).parent.resolve()

long_description = (current_directory / 'README.md').read_text(encoding='utf-8')
VERSION = (current_directory / 'VERSION').read_text(encoding='utf-8')

setuptools.setup(
    name="auto_aws_forensics",
    version=VERSION,

    description="Automates the process of creating a forensics capture of an EC2",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Shaun McCullough",

    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        "": ["*.yml"]

    },

    install_requires=[
        "aws-cdk.core>=1.122.0",
        "aws-cdk.aws_ec2>=1.122.0",
        "aws-cdk.aws_lambda>=1.122.0",
        "aws-cdk.aws_stepfunctions>=1.22.0",
        "aws-cdk.aws-stepfunctions-tasks>=1.22.0",
        "aws-cdk.aws-events-targets>=1.22.0",
        "aws-cdk.aws-imagebuilder>=1.22.0",
        "aws-cdk.aws-s3>=1.22.0",
        "aws-cdk.aws-logs>=1.22.0",
        "aws-cdk.aws-logs>=1.22.0",
        "aws-cdk.aws-imagebuilder>=1.22.0",
        "aws-cdk.aws-s3-assets>=1.22.0",
        "aws-cdk.aws-iam>=1.22.0",
        "aws-cdk.aws-kms>=1.22.0",
        "aws-cdk.aws-events>=1.22.0",
        "aws-cdk.aws-events-targets>=1.22.0",

    ],
    extras_require={
        "dev": ["pytest", "pylint", "twine", "moto", "boto3", "botocore", "mock"],
    },
    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Framework :: AWS CDK",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)
