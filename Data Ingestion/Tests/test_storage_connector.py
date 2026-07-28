import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connectors.storage_connector import StorageConnector
from connectors.base_connector import ConnectorConfig


class TestStorageConnector(unittest.TestCase):
    """Test cases for Storage Connector."""
    
    def test_initialization_invalid_type(self):
        """Test initialization with invalid storage type."""
        config = ConnectorConfig(
            storage_type='invalid_storage',
            bucket='test-bucket'
        )
        
        with self.assertRaises(ValueError) as context:
            StorageConnector(config)
        
        self.assertIn("Unsupported storage type", str(context.exception))
    
    @patch('connectors.storage_connector.boto3')
    def test_s3_initialization(self, mock_boto3):
        """Test S3 connector initialization."""
        config = ConnectorConfig(
            storage_type='s3',
            bucket='test-bucket',
            aws_access_key_id='test_key',
            aws_secret_access_key='test_secret',
            region_name='us-east-1'
        )
        
        try:
            connector = StorageConnector(config)
            self.assertEqual(connector.storage_type, 's3')
            self.assertEqual(connector.bucket, 'test-bucket')
        except ImportError:
            # Expected if boto3 not installed
            pass
    
    @patch('connectors.storage_connector.boto3')
    def test_s3_connect(self, mock_boto3):
        """Test S3 connection."""
        mock_client = Mock()
        mock_client.list_objects_v2.return_value = {'Contents': []}
        mock_boto3.client.return_value = mock_client
        
        config = ConnectorConfig(
            storage_type='s3',
            bucket='test-bucket',
            aws_access_key_id='test_key',
            aws_secret_access_key='test_secret'
        )
        
        connector = StorageConnector(config)
        status = connector.connect()
        
        self.assertTrue(status.is_connected)
        mock_boto3.client.assert_called_once_with(
            's3',
            aws_access_key_id='test_key',
            aws_secret_access_key='test_secret',
            region_name=None
        )
    
    @patch('connectors.storage_connector.boto3')
    def test_s3_list_objects(self, mock_boto3):
        """Test listing S3 objects."""
        from datetime import datetime
        
        mock_client = Mock()
        mock_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'file1.txt',
                    'Size': 1024,
                    'LastModified': datetime(2024, 1, 1),
                    'StorageClass': 'STANDARD'
                },
                {
                    'Key': 'file2.txt',
                    'Size': 2048,
                    'LastModified': datetime(2024, 1, 2),
                    'StorageClass': 'GLACIER'
                }
            ]
        }
        mock_boto3.client.return_value = mock_client
        
        config = ConnectorConfig(
            storage_type='s3',
            bucket='test-bucket'
        )
        
        connector = StorageConnector(config)
        connector.connect()
        
        data = connector.fetch_data(prefix='data/', max_keys=100)
        
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['key'], 'file1.txt')
        self.assertEqual(data[0]['size'], 1024)
        self.assertEqual(data[1]['storage_class'], 'GLACIER')
    
    @patch('connectors.storage_connector.boto3')
    def test_s3_download_file(self, mock_boto3):
        """Test downloading file from S3."""
        mock_body = Mock()
        mock_body.read.return_value = b'test content'
        
        mock_client = Mock()
        mock_client.get_object.return_value = {'Body': mock_body}
        mock_client.list_objects_v2.return_value = {'Contents': []}
        mock_boto3.client.return_value = mock_client
        
        config = ConnectorConfig(
            storage_type='s3',
            bucket='test-bucket'
        )
        
        connector = StorageConnector(config)
        connector.connect()
        
        content = connector.download_file('test.txt')
        
        self.assertEqual(content, b'test content')
        mock_client.get_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='test.txt'
        )
    
    @patch('connectors.storage_connector.boto3')
    def test_s3_upload_file(self, mock_boto3):
        """Test uploading file to S3."""
        mock_client = Mock()
        mock_client.list_objects_v2.return_value = {'Contents': []}
        mock_boto3.client.return_value = mock_client
        
        config = ConnectorConfig(
            storage_type='s3',
            bucket='test-bucket'
        )
        
        connector = StorageConnector(config)
        connector.connect()
        
        result = connector.upload_file('test.txt', b'test content')
        
        self.assertTrue(result)
        mock_client.put_object.assert_called_once()
    
    @patch('connectors.storage_connector.BlobServiceClient')
    def test_azure_connect(self, mock_blob_service):
        """Test Azure Blob Storage connection."""
        mock_client = Mock()
        mock_container_client = Mock()
        mock_container_client.get_container_properties.return_value = {}
        mock_client.get_container_client.return_value = mock_container_client
        mock_blob_service.from_connection_string.return_value = mock_client
        
        config = ConnectorConfig(
            storage_type='azure_blob',
            bucket='test-container',
            connection_string='DefaultEndpointsProtocol=https;...'
        )
        
        connector = StorageConnector(config)
        status = connector.connect()
        
        self.assertTrue(status.is_connected)
    
    @patch('connectors.storage_connector.gcs')
    def test_gcs_connect(self, mock_gcs):
        """Test GCS connection."""
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.get_bucket.return_value = mock_bucket
        mock_gcs.Client.return_value = mock_client
        
        config = ConnectorConfig(
            storage_type='gcs',
            bucket='test-bucket',
            project_id='test-project'
        )
        
        connector = StorageConnector(config)
        status = connector.connect()
        
        self.assertTrue(status.is_connected)
        mock_client.get_bucket.assert_called_once_with('test-bucket')
    
    @patch('connectors.storage_connector.boto3')
    def test_validate_connection(self, mock_boto3):
        """Test validate_connection method."""
        mock_client = Mock()
        mock_client.list_objects_v2.return_value = {'Contents': []}
        mock_boto3.client.return_value = mock_client
        
        config = ConnectorConfig(
            storage_type='s3',
            bucket='test-bucket'
        )
        
        connector = StorageConnector(config)
        connector.connect()
        
        status = connector.validate_connection()
        
        self.assertTrue(status.is_connected)
    
    @patch('connectors.storage_connector.boto3')
    def test_disconnect(self, mock_boto3):
        """Test disconnect method."""
        mock_client = Mock()
        mock_client.list_objects_v2.return_value = {'Contents': []}
        mock_boto3.client.return_value = mock_client
        
        config = ConnectorConfig(
            storage_type='s3',
            bucket='test-bucket'
        )
        
        connector = StorageConnector(config)
        connector.connect()
        result = connector.disconnect()
        
        self.assertTrue(result)
        self.assertFalse(connector._connected)
    
    @patch('connectors.storage_connector.boto3')
    def test_context_manager(self, mock_boto3):
        """Test connector as context manager."""
        mock_client = Mock()
        mock_client.list_objects_v2.return_value = {'Contents': []}
        mock_boto3.client.return_value = mock_client
        
        config = ConnectorConfig(
            storage_type='s3',
            bucket='test-bucket'
        )
        
        with StorageConnector(config) as connector:
            self.assertTrue(connector._connected)
        
        self.assertFalse(connector._connected)


if __name__ == '__main__':
    unittest.main()
