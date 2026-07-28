import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connectors.rest_api_connector import RESTAPIConnector
from connectors.base_connector import ConnectorConfig


class TestRESTAPIConnector(unittest.TestCase):
    """Test cases for REST API Connector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ConnectorConfig(
            base_url="https://api.example.com",
            auth_type="bearer",
            token="test_token_123",
            timeout=30
        )
        self.connector = RESTAPIConnector(self.config)
    
    def tearDown(self):
        """Clean up after tests."""
        if self.connector._connected:
            self.connector.disconnect()
    
    def test_initialization(self):
        """Test connector initialization."""
        self.assertEqual(self.connector.base_url, "https://api.example.com")
        self.assertIsNotNone(self.connector.session)
        self.assertFalse(self.connector._connected)
    
    def test_initialization_without_base_url(self):
        """Test that initialization fails without base_url."""
        config = ConnectorConfig()
        with self.assertRaises(ValueError) as context:
            RESTAPIConnector(config)
        self.assertIn("base_url is required", str(context.exception))
    
    def test_bearer_auth_setup(self):
        """Test Bearer token authentication setup."""
        self.assertIn('Authorization', self.connector.session.headers)
        self.assertEqual(self.connector.session.headers['Authorization'], 'Bearer test_token_123')
    
    def test_api_key_auth_setup(self):
        """Test API key authentication setup."""
        config = ConnectorConfig(
            base_url="https://api.example.com",
            auth_type="api_key",
            api_key="test_api_key",
            api_key_header="X-API-Key"
        )
        connector = RESTAPIConnector(config)
        self.assertIn('X-API-Key', connector.session.headers)
        self.assertEqual(connector.session.headers['X-API-Key'], 'test_api_key')
    
    def test_basic_auth_setup(self):
        """Test basic authentication setup."""
        config = ConnectorConfig(
            base_url="https://api.example.com",
            auth_type="basic",
            username="testuser",
            password="testpass"
        )
        connector = RESTAPIConnector(config)
        self.assertIsNotNone(connector.session.auth)
        self.assertEqual(connector.session.auth, ('testuser', 'testpass'))
    
    @patch('connectors.rest_api_connector.requests.Session.get')
    def test_connect_success(self, mock_get):
        """Test successful connection."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        status = self.connector.connect()
        
        self.assertTrue(status.is_connected)
        self.assertTrue(self.connector._connected)
        self.assertEqual(status.message, "Connection successful")
        mock_get.assert_called_once()
    
    @patch('connectors.rest_api_connector.requests.Session.get')
    def test_connect_failure(self, mock_get):
        """Test connection failure."""
        mock_get.side_effect = Exception("Connection timeout")
        
        status = self.connector.connect()
        
        self.assertFalse(status.is_connected)
        self.assertFalse(self.connector._connected)
        self.assertIn("Connection failed", status.message)
    
    def test_disconnect(self):
        """Test disconnect."""
        self.connector._connected = True
        result = self.connector.disconnect()
        
        self.assertTrue(result)
        self.assertFalse(self.connector._connected)
    
    @patch('connectors.rest_api_connector.requests.Session.request')
    def test_fetch_data_get_request(self, mock_request):
        """Test fetch_data with GET request."""
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1, "name": "Test"}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        self.connector._connected = True
        data = self.connector.fetch_data(endpoint="/users", method="GET")
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], 1)
        mock_request.assert_called_once()
    
    @patch('connectors.rest_api_connector.requests.Session.request')
    def test_fetch_data_with_pagination_wrapper(self, mock_request):
        """Test fetch_data handles paginated responses."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"id": 1}, {"id": 2}],
            "pagination": {"page": 1}
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        self.connector._connected = True
        data = self.connector.fetch_data(endpoint="/users")
        
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], 1)
    
    @patch('connectors.rest_api_connector.requests.Session.request')
    def test_fetch_data_with_retry(self, mock_request):
        """Test fetch_data retries on failure."""
        # First two calls fail, third succeeds
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1}]
        mock_response.raise_for_status = Mock()
        
        mock_request.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            mock_response
        ]
        
        self.connector._connected = True
        self.connector.config.set('max_retries', 3)
        self.connector.config.set('retry_delay', 0.1)
        
        data = self.connector.fetch_data(endpoint="/users")
        
        self.assertEqual(len(data), 1)
        self.assertEqual(mock_request.call_count, 3)
    
    @patch('connectors.rest_api_connector.requests.Session.request')
    def test_fetch_data_all_retries_fail(self, mock_request):
        """Test fetch_data when all retries fail."""
        mock_request.side_effect = Exception("Connection error")
        
        self.connector._connected = True
        self.connector.config.set('max_retries', 2)
        self.connector.config.set('retry_delay', 0.1)
        
        with self.assertRaises(Exception):
            self.connector.fetch_data(endpoint="/users")
        
        self.assertEqual(mock_request.call_count, 2)
    
    @patch('connectors.rest_api_connector.requests.Session.request')
    def test_paginated_fetch(self, mock_request):
        """Test paginated_fetch method."""
        # Mock three pages of data
        mock_responses = [
            Mock(json=lambda: [{"id": i} for i in range(1, 3)], raise_for_status=Mock()),
            Mock(json=lambda: [{"id": i} for i in range(3, 5)], raise_for_status=Mock()),
            Mock(json=lambda: [], raise_for_status=Mock())
        ]
        mock_request.side_effect = mock_responses
        
        self.connector._connected = True
        data = self.connector.paginated_fetch(
            endpoint="/users",
            page_param="page",
            page_size_param="limit",
            page_size=2
        )
        
        self.assertEqual(len(data), 4)
        self.assertEqual(mock_request.call_count, 3)
    
    @patch('connectors.rest_api_connector.requests.Session.get')
    def test_validate_connection_when_connected(self, mock_get):
        """Test validate_connection when connected."""
        mock_response = Mock(status_code=200)
        mock_get.return_value = mock_response
        
        self.connector._connected = True
        status = self.connector.validate_connection()
        
        self.assertTrue(status.is_connected)
    
    def test_validate_connection_when_not_connected(self):
        """Test validate_connection when not connected."""
        status = self.connector.validate_connection()
        
        self.assertFalse(status.is_connected)
        self.assertEqual(status.message, "Not connected")
    
    def test_get_metadata(self):
        """Test get_metadata method."""
        metadata = self.connector.get_metadata()
        
        self.assertEqual(metadata["connector_type"], "RESTAPIConnector")
        self.assertFalse(metadata["is_connected"])
        self.assertIn("base_url", metadata["config"])
        self.assertNotIn("token", metadata["config"])  # Sensitive data should be excluded
    
    @patch('connectors.rest_api_connector.requests.Session.get')
    def test_context_manager(self, mock_get):
        """Test connector as context manager."""
        mock_response = Mock(status_code=200)
        mock_get.return_value = mock_response
        
        with RESTAPIConnector(self.config) as connector:
            self.assertTrue(connector._connected)
        
        # Connection should be closed after exiting context
        self.assertFalse(connector._connected)
    
    @patch('connectors.rest_api_connector.requests.Session.request')
    def test_post_request_with_json(self, mock_request):
        """Test POST request with JSON payload."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": 1, "status": "created"}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        self.connector._connected = True
        data = self.connector.fetch_data(
            endpoint="/users",
            method="POST",
            json_data={"name": "Test User"}
        )
        
        self.assertEqual(data[0]["status"], "created")
        mock_request.assert_called_once()
        
        # Verify JSON was passed
        call_kwargs = mock_request.call_args[1]
        self.assertIn('json', call_kwargs)
        self.assertEqual(call_kwargs['json'], {"name": "Test User"})


if __name__ == '__main__':
    unittest.main()
