from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="data-ai-scaffold",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A unified data connector framework for AI/ML workflows",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/data-ai-scaffold",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "databricks": ["databricks-sql-connector>=2.9.0"],
        "postgres": ["psycopg2-binary>=2.9.0"],
        "mysql": ["mysql-connector-python>=8.0.0"],
        "s3": ["boto3>=1.26.0"],
        "azure": ["azure-storage-blob>=12.0.0"],
        "gcs": ["google-cloud-storage>=2.0.0"],
        "dbfs": ["databricks-sdk>=0.12.0"],
        "all": [
            "databricks-sql-connector>=2.9.0",
            "psycopg2-binary>=2.9.0",
            "mysql-connector-python>=8.0.0",
            "boto3>=1.26.0",
            "azure-storage-blob>=12.0.0",
            "google-cloud-storage>=2.0.0",
            "databricks-sdk>=0.12.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "flake8>=6.0.0",
            "mypy>=1.4.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "bandit>=1.7.5",
        ],
    },
)
