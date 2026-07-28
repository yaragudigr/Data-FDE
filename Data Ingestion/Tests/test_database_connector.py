import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connectors.database_connector import DatabaseConnector
from connectors.base_connector import ConnectorConfig


class TestDatabaseConnector(unittest.TestCase):
    """Test cases for Database Connector."""
    
    def test_initialization_databricks(self):
        """Test Databricks connector initialization."""
        config = ConnectorConfig(
            db_type='databricks',
            host='example.cloud.databricks.com',
            http_path='/sql/1.0/warehouses/abc123',
            access_token='test_token',
            database='test_db'
        )
        
        # Should not raise error even if databricks-sql-connector not installed
        # Just checks config validation
        try:
            connector = DatabaseConnector(config)
            self.assertEqual(connector.db_type, 'databricks')
            self.assertEqual(connector.host, 'example.cloud.databricks.com')
        except ImportError as e:
            # Expected if databricks-sql-connector not installed
            self.assertIn('databricks-sql-connector', str(e))
    
    def test_initialization_invalid_type(self):
        """Test initialization with invalid database type."""
        config = ConnectorConfig(
            db_type='invalid_db',
            host='localhost',
            database='test'
        )
        
        with self.assertRaises(ValueError) as context:
            DatabaseConnector(config)
        
        self.assertIn("Unsupported database type", str(context.exception))
    
    @patch('connectors.database_connector.sqlite3')
    def test_sqlite_connection(self, mock_sqlite):
        """Test SQLite connection."""
        mock_connection = Mock()
        mock_sqlite.connect.return_value = mock_connection
        
        config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        connector = DatabaseConnector(config)
        status = connector.connect()
        
        self.assertTrue(status.is_connected)
        mock_sqlite.connect.assert_called_once_with(':memory:')
    
    @patch('connectors.database_connector.sqlite3')
    def test_fetch_data_sqlite(self, mock_sqlite):
        """Test fetch_data with SQLite."""
        # Setup mock cursor
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'name': 'Alice'},
            {'id': 2, 'name': 'Bob'}
        ]
        mock_cursor.description = [('id',), ('name',)]
        
        # Setup mock connection
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_sqlite.connect.return_value = mock_connection
        mock_sqlite.Row = dict
        
        config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        connector = DatabaseConnector(config)
        connector.connect()
        
        data = connector.fetch_data(sql="SELECT * FROM users")
        
        mock_cursor.execute.assert_called_with("SELECT * FROM users")
        self.assertEqual(len(data), 2)
    
    @patch('connectors.database_connector.sqlite3')
    def test_execute_query(self, mock_sqlite):
        """Test execute_query method."""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_sqlite.connect.return_value = mock_connection
        
        config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        connector = DatabaseConnector(config)
        connector.connect()
        
        affected = connector.execute_query("INSERT INTO users VALUES (1, 'Test')")
        
        self.assertEqual(affected, 1)
        mock_connection.commit.assert_called_once()
    
    @patch('connectors.database_connector.sqlite3')
    def test_validate_connection(self, mock_sqlite):
        """Test validate_connection method."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_sqlite.connect.return_value = mock_connection
        
        config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        connector = DatabaseConnector(config)
        connector.connect()
        
        status = connector.validate_connection()
        
        self.assertTrue(status.is_connected)
        mock_cursor.execute.assert_called_with("SELECT 1")
    
    @patch('connectors.database_connector.sqlite3')
    def test_disconnect(self, mock_sqlite):
        """Test disconnect method."""
        mock_connection = Mock()
        mock_sqlite.connect.return_value = mock_connection
        
        config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        connector = DatabaseConnector(config)
        connector.connect()
        result = connector.disconnect()
        
        self.assertTrue(result)
        mock_connection.close.assert_called_once()
    
    @patch('connectors.database_connector.sqlite3')
    def test_get_tables_sqlite(self, mock_sqlite):
        """Test get_tables method for SQLite."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {'name': 'users'},
            {'name': 'orders'}
        ]
        mock_cursor.description = [('name',)]
        
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_sqlite.connect.return_value = mock_connection
        mock_sqlite.Row = dict
        
        config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        connector = DatabaseConnector(config)
        connector.connect()
        
        tables = connector.get_tables()
        
        self.assertEqual(len(tables), 2)
        self.assertIn('users', tables)
        self.assertIn('orders', tables)
    
    @patch('connectors.database_connector.sqlite3')
    def test_context_manager(self, mock_sqlite):
        """Test connector as context manager."""
        mock_connection = Mock()
        mock_sqlite.connect.return_value = mock_connection
        
        config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        with DatabaseConnector(config) as connector:
            self.assertTrue(connector._connected)
        
        mock_connection.close.assert_called_once()
    
    def test_parameterized_query(self):
        """Test fetch_data with parameterized query."""
        # This test would use real SQLite since it's available
        import sqlite3
        
        config = ConnectorConfig(
            db_type='sqlite',
            database=':memory:'
        )
        
        connector = DatabaseConnector(config)
        connector.connect()
        
        # Create table
        connector.execute_query(
            "CREATE TABLE users (id INTEGER, name TEXT)"
        )
        connector.execute_query(
            "INSERT INTO users VALUES (?, ?)",
            params=(1, 'Alice')
        )
        
        # Fetch with parameterized query
        data = connector.fetch_data(
            sql="SELECT * FROM users WHERE id = ?",
            params=(1,)
        )
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Alice')
        
        connector.disconnect()


if __name__ == '__main__':
    unittest.main()
