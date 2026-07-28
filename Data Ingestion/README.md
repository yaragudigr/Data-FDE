# Data AI Scaffold

[![CI Pipeline](https://github.com/yourusername/data-ai-scaffold/workflows/CI%20Pipeline/badge.svg)](https://github.com/yourusername/data-ai-scaffold/actions)
[![codecov](https://codecov.io/gh/yourusername/data-ai-scaffold/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/data-ai-scaffold)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A unified, production-ready data connector framework for AI/ML workflows in Databricks and beyond. This scaffold provides a consistent interface for connecting to REST APIs, databases, and cloud storage systems.

## 🚀 Features

* **Unified Interface**: Single API for all connector types
* **Multiple Connectors**: REST API, Databases (Databricks, PostgreSQL, MySQL, SQLite), Cloud Storage (S3, Azure Blob, GCS, DBFS)
* **Production Ready**: Comprehensive error handling, retry logic, and logging
* **Well Tested**: 80%+ code coverage with unit and integration tests
* **Type Safe**: Full type hints for better IDE support
* **Extensible**: Easy to add new connector types
* **Context Manager Support**: Clean resource management with `with` statements
* **CI/CD Ready**: GitHub Actions workflow included

## 📦 Installation

### Basic Installation

```bash
pip install -r requirements.txt
```

### Install with Specific Connectors

```bash
# Install with all connectors
pip install -e .[all]

# Install with specific connectors
pip install -e .[databricks,s3]  # Databricks and S3 only
pip install -e .[postgres,azure]  # PostgreSQL and Azure only
```

### Development Installation

```bash
pip install -r requirements-dev.txt
pip install -e .[dev]
```

## 🔧 Quick Start

### REST API Connector

```python
from connectors import RESTAPIConnector, ConnectorConfig

# Configure the connector
config = ConnectorConfig(
    base_url="https://api.example.com",
    auth_type="bearer",
    token="your_api_token"
)

# Use as context manager
with RESTAPIConnector(config) as connector:
    # Fetch data
    data = connector.fetch_data(endpoint="/users", method="GET")
    print(f"Retrieved {len(data)} users")
    
    # Fetch paginated data
    all_data = connector.paginated_fetch(
        endpoint="/users",
        page_size=100,
        max_pages=10
    )
```

### Database Connector

```python
from connectors import DatabaseConnector, ConnectorConfig

# SQLite example
config = ConnectorConfig(
    db_type='sqlite',
    database='my_database.db'
)

with DatabaseConnector(config) as connector:
    # Fetch data with SQL
    results = connector.fetch_data(
        sql="SELECT * FROM users WHERE active = ?",
        params=(True,)
    )
    
    # Execute write operations
    connector.execute_query(
        sql="INSERT INTO users (name, email) VALUES (?, ?)",
        params=("Alice", "alice@example.com")
    )
    
    # Get list of tables
    tables = connector.get_tables()
```

### Databricks SQL Connector

```python
from connectors import DatabaseConnector, ConnectorConfig

config = ConnectorConfig(
    db_type='databricks',
    host='your-workspace.cloud.databricks.com',
    http_path='/sql/1.0/warehouses/abc123',
    access_token='your_databricks_token',
    catalog='main',
    schema='default'
)

with DatabaseConnector(config) as connector:
    # Query Unity Catalog tables
    data = connector.fetch_data(
        sql="SELECT * FROM main.default.customers LIMIT 1000"
    )
```

### Storage Connector

```python
from connectors import StorageConnector, ConnectorConfig

# S3 example
config = ConnectorConfig(
    storage_type='s3',
    bucket='my-bucket',
    aws_access_key_id='your_key',
    aws_secret_access_key='your_secret',
    region_name='us-east-1'
)

with StorageConnector(config) as connector:
    # List objects
    objects = connector.fetch_data(prefix='data/', max_keys=100)
    
    # Download file
    content = connector.download_file('data/file.csv')
    
    # Upload file
    connector.upload_file('data/output.csv', b'CSV content here')
```

## 🏗️ Architecture

### Base Connector Pattern

All connectors inherit from `BaseConnector` which provides:

* `connect()` - Establish connection
* `disconnect()` - Close connection
* `fetch_data()` - Retrieve data
* `validate_connection()` - Check connection health
* `get_metadata()` - Get connector information
* Context manager support (`__enter__`, `__exit__`)

### Configuration Management

The `ConnectorConfig` class provides type-safe configuration:

```python
config = ConnectorConfig(
    param1="value1",
    param2="value2"
)

# Get values
value = config.get('param1')
value_with_default = config.get('param3', 'default')

# Set values
config.set('param3', 'value3')

# Convert to dict
config_dict = config.to_dict()
```

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suites

```bash
# REST API connector tests
pytest tests/test_rest_connector.py -v

# Database connector tests
pytest tests/test_database_connector.py -v

# Storage connector tests
pytest tests/test_storage_connector.py -v

# Integration tests
pytest tests/test_integration.py -v
```

### Run with Coverage

```bash
pytest tests/ -v --cov=connectors --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run specific connector tests
pytest -m rest
pytest -m database
pytest -m storage
```

## 🔍 Code Quality

### Linting

```bash
# Flake8 for style checking
flake8 connectors/ tests/

# Black for code formatting
black connectors/ tests/

# isort for import sorting
isort connectors/ tests/
```

### Type Checking

```bash
mypy connectors/
```

### Security Scanning

```bash
# Bandit for security issues
bandit -r connectors/

# Safety for dependency vulnerabilities
safety check
```

## 📊 CI/CD Pipeline

The project includes a comprehensive GitHub Actions workflow:

* **Multi-Python Testing**: Tests on Python 3.8, 3.9, 3.10, 3.11
* **Individual Connector Tests**: Separate jobs for each connector type
* **Integration Tests**: End-to-end workflow testing
* **Code Quality**: Black, isort, Flake8, MyPy, Bandit
* **Coverage**: Codecov integration
* **Build**: Package building and artifact upload

## 📝 Supported Connectors

### REST API Connector

* Authentication: Bearer, API Key, Basic Auth
* Automatic retries with exponential backoff
* Pagination support
* Custom headers
* Timeout configuration

### Database Connector

* **Databricks SQL**: Unity Catalog support
* **PostgreSQL**: Full feature support
* **MySQL**: Full feature support
* **SQLite**: Local database support
* Parameterized queries
* Transaction support
* Schema introspection

### Storage Connector

* **AWS S3**: Full S3 API support
* **Azure Blob Storage**: Container and blob operations
* **Google Cloud Storage**: Bucket and object operations
* **Databricks DBFS**: Native DBFS integration
* File upload/download
* Object listing with prefix filtering
* Metadata support

## 🛡️ Security Best Practices

1. **Never commit credentials**: Use environment variables or secret managers
2. **Sensitive data filtering**: Metadata automatically excludes passwords and secrets
3. **Connection validation**: Always validate connections before use
4. **Context managers**: Use `with` statements for automatic cleanup
5. **Parameterized queries**: Always use parameters for SQL queries

## 🔄 Adding New Connectors

1. Create a new file in `connectors/` (e.g., `connectors/new_connector.py`)
2. Inherit from `BaseConnector`
3. Implement abstract methods:
   * `connect()`
   * `disconnect()`
   * `fetch_data()`
   * `validate_connection()`
4. Add to `connectors/__init__.py`
5. Create tests in `tests/test_new_connector.py`
6. Update `README.md` and `requirements.txt`

## 📚 Documentation

For more examples, see:

* [Example_Usage Notebook](./Example_Usage.ipynb)
* [API Documentation](./docs/)
* [Contributing Guide](./CONTRIBUTING.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and quality checks
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

* Built for Databricks AI/ML workflows
* Inspired by best practices from various data engineering projects
* Thanks to all contributors

## 📞 Support

For issues, questions, or contributions:

* Open an issue on [GitHub Issues](https://github.com/yourusername/data-ai-scaffold/issues)
* Submit a pull request
* Contact the maintainers

---

**Happy Data Engineering! 🚀**
