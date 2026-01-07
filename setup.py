
from setuptools import setup, find_packages

setup(
    name="orchestration-system",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "psutil>=5.9.0",
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-json-report>=1.5.0",
        "pytest-metadata>=3.0.0",
        "pylint>=3.0.0",
        "flake8>=6.1.0",
        "mypy>=1.7.0",
        "bandit>=1.7.5",
        "safety>=2.3.5",
    ],
)
