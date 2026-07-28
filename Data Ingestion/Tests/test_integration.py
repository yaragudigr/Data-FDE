import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connectors import (
    ConnectorConfig,
    RESTAPIConnector,
    DatabaseConnector,
    StorageConnector
)


class TestIntegration(unittest.TestCase):
    """Integration tests for all connectors."""
    
    def test_import_all_connectors(self):
        """Test that all connectors can be imported."""
        self.assertIsNotNone(RESTAPIConnector)
        self.assertIsNotNone(DatabaseConnector)
        self.assertIsNotNone(StorageConnector)
        self.assertIsNotNone(ConnectorConfig)
    
    def test_rest_api_connector_workflow(self):
        """Test complete workflow with REST API connector."""
        # This is a basic workflow test without actual API calls
        config = ConnectorConfig(
            base_url="https://jsonplaceholder.typicode.com",
            timeout=30
        )
        
        connector = RESTAPIConnector(config)
        
        # Test basic properties
        self.assertEqual(connector.base_url, "https://jsonplaceholder.typicode.com")
        self.assertFalse(connector._connected)
        
        # Test metadata
        metadata = connector.get_metadata()
        self.assertEqual(metadata['connector_type'], 'RESTAPIConnector')
        self.assertFalse(metadata['is_connected'])
    
    def test_database_connector_sqlite_workflow(self):
        """Test complete workflow with SQLite database connector."""
        config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        # Use context manager for automatic connection management
        with DatabaseConnector(config) as connector:
            # Create a test table
            connector.execute_query(
                "CREATE TABLE test_users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
            )
            
            # Insert test data
            affected = connector.execute_query(
                "INSERT INTO test_users (id, name, email) VALUES (?, ?, ?)",
                params=(1, 'Alice', 'alice@example.com')
            )
            self.assertEqual(affected, 1)
            
            # Insert more data
            connector.execute_query(
                "INSERT INTO test_users (id, name, email) VALUES (?, ?, ?)",
                params=(2, 'Bob', 'bob@example.com')
            )
            
            # Query data
            results = connector.fetch_data(sql="SELECT * FROM test_users ORDER BY id")
            
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]['name'], 'Alice')
            self.assertEqual(results[0]['email'], 'alice@example.com')
            self.assertEqual(results[1]['name'], 'Bob')
            
            # Test parameterized query
            filtered = connector.fetch_data(
                sql="SELECT * FROM test_users WHERE id = ?",
                params=(1,)
            )
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0]['name'], 'Alice')
            
            # Validate connection
            status = connector.validate_connection()
            self.assertTrue(status.is_connected)
            
            # Get tables
            tables = connector.get_tables()
            self.assertIn('test_users', tables)
        
        # After exiting context, connection should be closed
        self.assertFalse(connector._connected)
    
    def test_config_management(self):
        """Test configuration management across connectors."""
        # Create config with various settings
        config = ConnectorConfig(
            base_url="https://api.example.com",
            api_key="secret_key",
            timeout=60,
            max_retries=5
        )
        
        # Test get method
        self.assertEqual(config.get('base_url'), 'https://api.example.com')
        self.assertEqual(config.get('timeout'), 60)
        self.assertIsNone(config.get('nonexistent'))
        self.assertEqual(config.get('nonexistent', 'default'), 'default')
        
        # Test set method
        config.set('new_param', 'new_value')
        self.assertEqual(config.get('new_param'), 'new_value')
        
        # Test to_dict method
        config_dict = config.to_dict()
        self.assertIsInstance(config_dict, dict)
        self.assertIn('base_url', config_dict)
        self.assertIn('new_param', config_dict)
    
    def test_connection_status(self):
        """Test ConnectionStatus object."""
        from connectors.base_connector import ConnectionStatus
        from datetime import datetime
        
        # Test successful connection status
        status = ConnectionStatus(
            is_connected=True,
            message="Connected successfully",
            metadata={'host': 'localhost', 'port': 5432}
        )
        
        self.assertTrue(status.is_connected)
        self.assertEqual(status.message, "Connected successfully")
        self.assertIn('host', status.metadata)
        self.assertIsInstance(status.timestamp, datetime)
        
        # Test failed connection status
        failed_status = ConnectionStatus(
            is_connected=False,
            message="Connection timeout"
        )
        
        self.assertFalse(failed_status.is_connected)
        self.assertEqual(failed_status.message, "Connection timeout")
        
        # Test __repr__
        repr_str = repr(status)
        self.assertIn('ConnectionStatus', repr_str)
        self.assertIn('True', repr_str)
    
    def test_multiple_connector_types(self):
        """Test working with multiple connector types simultaneously."""
        # Create configs for different connector types
        rest_config = ConnectorConfig(
            base_url="https://api.example.com",
            auth_type="bearer",
            token="test_token"
        )
        
        db_config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        # Create connectors
        rest_connector = RESTAPIConnector(rest_config)
        db_connector = DatabaseConnector(db_config)
        
        # Test they are independent
        self.assertNotEqual(rest_connector.config, db_connector.config)
        self.assertEqual(rest_connector.__class__.__name__, 'RESTAPIConnector')
        self.assertEqual(db_connector.__class__.__name__, 'DatabaseConnector')
        
        # Test metadata is different
        rest_metadata = rest_connector.get_metadata()
        db_metadata = db_connector.get_metadata()
        
        self.assertEqual(rest_metadata['connector_type'], 'RESTAPIConnector')
        self.assertEqual(db_metadata['connector_type'], 'DatabaseConnector')
        
        # Sensitive data should be filtered out
        self.assertNotIn('token', rest_metadata['config'])
    
    def test_error_handling(self):
        """Test error handling across connectors."""
        # Test REST connector with missing required config
        with self.assertRaises(ValueError):
            RESTAPIConnector(ConnectorConfig())
        
        # Test database connector with invalid type
        with self.assertRaises(ValueError):
            DatabaseConnector(ConnectorConfig(db_type='unsupported', database='test'))
        
        # Test storage connector with invalid type
        with self.assertRaises(ValueError):
            StorageConnector(ConnectorConfig(storage_type='unsupported', bucket='test'))
    
    def test_sqlite_advanced_operations(self):
        """Test advanced database operations with SQLite."""
        config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        with DatabaseConnector(config) as connector:
            # Create tables with relationships
            connector.execute_query("""
                CREATE TABLE departments (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
            
            connector.execute_query("""
                CREATE TABLE employees (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    department_id INTEGER,
                    salary REAL,
                    FOREIGN KEY (department_id) REFERENCES departments (id)
                )
            """)
            
            # Insert departments
            connector.execute_query(
                "INSERT INTO departments (id, name) VALUES (1, 'Engineering'), (2, 'Sales')"
            )
            
            # Insert employees
            connector.execute_query("""
                INSERT INTO employees (id, name, department_id, salary) VALUES
                (1, 'Alice', 1, 100000),
                (2, 'Bob', 1, 120000),
                (3, 'Carol', 2, 90000)
            """)
            
            # Test JOIN query
            results = connector.fetch_data(sql="""
                SELECT e.name, e.salary, d.name as department
                FROM employees e
                JOIN departments d ON e.department_id = d.id
                WHERE d.name = 'Engineering'
                ORDER BY e.salary DESC
            """)
            
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]['name'], 'Bob')
            self.assertEqual(results[0]['salary'], 120000.0)
            self.assertEqual(results[0]['department'], 'Engineering')
            
            # Test aggregate query
            agg_results = connector.fetch_data(sql="""
                SELECT d.name, COUNT(*) as employee_count, AVG(e.salary) as avg_salary
                FROM employees e
                JOIN departments d ON e.department_id = d.id
                GROUP BY d.name
            """)
            
            self.assertEqual(len(agg_results), 2)
            eng_dept = [r for r in agg_results if r['name'] == 'Engineering'][0]
            self.assertEqual(eng_dept['employee_count'], 2)
            self.assertEqual(eng_dept['avg_salary'], 110000.0)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
