from setuptools import setup, find_packages

setup(
    name="coderipple",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "gitpython>=3.1.0",
        "tree-sitter>=0.22.0",
        "click>=8.0.0",
        "pyyaml>=6.0"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "coderipple=cli.main:cli",
        ],
    },
)
