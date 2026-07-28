from typing import Dict, List, Optional, Any, BinaryIO
import io
import os

try:
    import boto3
    from botocore.exceptions import ClientError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

try:
    from azure.storage.blob import BlobServiceClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

try:
    from google.cloud import storage as gcs
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

from .base_connector import BaseConnector, ConnectorConfig, ConnectionStatus


class StorageConnector(BaseConnector):
    """Connector for cloud storage (S3, Azure Blob, GCS)."""
    
    SUPPORTED_TYPES = ['s3', 'azure_blob', 'gcs', 'dbfs']
    
    def __init__(self, config: ConnectorConfig):
        """
        Initialize storage connector.
        
        Required config:
            - storage_type: Type of storage ('s3', 'azure_blob', 'gcs', 'dbfs')
            - bucket: Bucket/container name (not needed for dbfs)
        
        Optional config (depending on storage_type):
            For S3:
                - aws_access_key_id: AWS access key
                - aws_secret_access_key: AWS secret key
                - region_name: AWS region
            For Azure:
                - connection_string: Azure connection string
                - account_name: Storage account name
                - account_key: Storage account key
            For GCS:
                - credentials_path: Path to service account JSON
                - project_id: GCP project ID
            For DBFS:
                - workspace_url: Databricks workspace URL
                - access_token: Databricks access token
        """
        super().__init__(config)
        
        self.storage_type = config.get('storage_type', '').lower()
        if self.storage_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported storage type: {self.storage_type}. Supported types: {self.SUPPORTED_TYPES}")
        
        self._validate_dependencies()
        
        self.bucket = config.get('bucket')
        self._client = None
    
    def _validate_dependencies(self):
        """Validate required dependencies are installed."""
        if self.storage_type == 's3' and not S3_AVAILABLE:
            raise ImportError("boto3 is required for S3. Install with: pip install boto3")
        elif self.storage_type == 'azure_blob' and not AZURE_AVAILABLE:
            raise ImportError("azure-storage-blob is required for Azure. Install with: pip install azure-storage-blob")
        elif self.storage_type == 'gcs' and not GCS_AVAILABLE:
            raise ImportError("google-cloud-storage is required for GCS. Install with: pip install google-cloud-storage")
    
    def connect(self) -> ConnectionStatus:
        """
        Establish storage connection.
        
        Returns:
            ConnectionStatus object
        """
        try:
            if self.storage_type == 's3':
                self._connect_s3()
            elif self.storage_type == 'azure_blob':
                self._connect_azure()
            elif self.storage_type == 'gcs':
                self._connect_gcs()
            elif self.storage_type == 'dbfs':
                self._connect_dbfs()
            
            self._connected = True
            self.logger.info(f"Successfully connected to {self.storage_type}")
            
            return ConnectionStatus(
                is_connected=True,
                message="Storage connection successful",
                metadata={"storage_type": self.storage_type, "bucket": self.bucket}
            )
        
        except Exception as e:
            self.logger.error(f"Storage connection failed: {str(e)}")
            return ConnectionStatus(
                is_connected=False,
                message=f"Connection failed: {str(e)}"
            )
    
    def _connect_s3(self):
        """Connect to AWS S3."""
        self._client = boto3.client(
            's3',
            aws_access_key_id=self.config.get('aws_access_key_id'),
            aws_secret_access_key=self.config.get('aws_secret_access_key'),
            region_name=self.config.get('region_name')
        )
        # Validate connection by listing objects
        self._client.list_objects_v2(Bucket=self.bucket, MaxKeys=1)
    
    def _connect_azure(self):
        """Connect to Azure Blob Storage."""
        connection_string = self.config.get('connection_string')
        if connection_string:
            self._client = BlobServiceClient.from_connection_string(connection_string)
        else:
            account_name = self.config.get('account_name')
            account_key = self.config.get('account_key')
            self._client = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=account_key
            )
        # Validate connection
        self._client.get_container_client(self.bucket).get_container_properties()
    
    def _connect_gcs(self):
        """Connect to Google Cloud Storage."""
        credentials_path = self.config.get('credentials_path')
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        self._client = gcs.Client(project=self.config.get('project_id'))
        # Validate connection
        self._client.get_bucket(self.bucket)
    
    def _connect_dbfs(self):
        """Connect to Databricks File System."""
        try:
            from databricks.sdk import WorkspaceClient
            workspace_url = self.config.get('workspace_url')
            access_token = self.config.get('access_token')
            self._client = WorkspaceClient(host=workspace_url, token=access_token)
        except ImportError:
            raise ImportError("databricks-sdk is required for DBFS. Install with: pip install databricks-sdk")
    
    def disconnect(self) -> bool:
        """
        Close storage connection.
        
        Returns:
            True if successful
        """
        try:
            self._connected = False
            self._client = None
            self.logger.info("Storage connection closed")
            return True
        except Exception as e:
            self.logger.error(f"Error closing connection: {str(e)}")
            return False
    
    def fetch_data(
        self,
        query: Optional[Dict] = None,
        prefix: str = "",
        max_keys: int = 1000,
        **kwargs
    ) -> List[Dict]:
        """
        List objects in storage.
        
        Args:
            query: Dict with 'prefix' key (legacy parameter)
            prefix: Path prefix to filter objects
            max_keys: Maximum number of objects to return
            **kwargs: Additional arguments
            
        Returns:
            List of object metadata
        """
        if not self._connected:
            self.connect()
        
        # Handle legacy query parameter
        if query and not prefix:
            prefix = query.get('prefix', '')
        
        try:
            if self.storage_type == 's3':
                return self._list_s3_objects(prefix, max_keys)
            elif self.storage_type == 'azure_blob':
                return self._list_azure_blobs(prefix, max_keys)
            elif self.storage_type == 'gcs':
                return self._list_gcs_objects(prefix, max_keys)
            elif self.storage_type == 'dbfs':
                return self._list_dbfs_files(prefix)
            
            return []
        
        except Exception as e:
            self.logger.error(f"Failed to list objects: {str(e)}")
            raise
    
    def _list_s3_objects(self, prefix: str, max_keys: int) -> List[Dict]:
        """List S3 objects."""
        response = self._client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        objects = []
        for obj in response.get('Contents', []):
            objects.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat(),
                'storage_class': obj.get('StorageClass', 'STANDARD')
            })
        
        return objects
    
    def _list_azure_blobs(self, prefix: str, max_keys: int) -> List[Dict]:
        """List Azure blobs."""
        container_client = self._client.get_container_client(self.bucket)
        blobs = container_client.list_blobs(name_starts_with=prefix)
        
        objects = []
        for blob in list(blobs)[:max_keys]:
            objects.append({
                'key': blob.name,
                'size': blob.size,
                'last_modified': blob.last_modified.isoformat(),
                'content_type': blob.content_settings.content_type
            })
        
        return objects
    
    def _list_gcs_objects(self, prefix: str, max_keys: int) -> List[Dict]:
        """List GCS objects."""
        bucket = self._client.get_bucket(self.bucket)
        blobs = bucket.list_blobs(prefix=prefix, max_results=max_keys)
        
        objects = []
        for blob in blobs:
            objects.append({
                'key': blob.name,
                'size': blob.size,
                'last_modified': blob.updated.isoformat(),
                'content_type': blob.content_type
            })
        
        return objects
    
    def _list_dbfs_files(self, prefix: str) -> List[Dict]:
        """List DBFS files."""
        path = f"/dbfs/{prefix}" if not prefix.startswith('/dbfs/') else prefix
        
        objects = []
        try:
            for item in self._client.dbfs.list(path):
                objects.append({
                    'key': item.path,
                    'size': item.file_size or 0,
                    'is_directory': item.is_dir,
                    'last_modified': str(item.modification_time) if item.modification_time else None
                })
        except Exception as e:
            self.logger.warning(f"Failed to list DBFS path {path}: {str(e)}")
        
        return objects
    
    def download_file(self, key: str, local_path: Optional[str] = None) -> bytes:
        """
        Download a file from storage.
        
        Args:
            key: Object key/path
            local_path: Local path to save file (optional)
            
        Returns:
            File content as bytes
        """
        if not self._connected:
            self.connect()
        
        try:
            if self.storage_type == 's3':
                content = self._download_s3_file(key)
            elif self.storage_type == 'azure_blob':
                content = self._download_azure_blob(key)
            elif self.storage_type == 'gcs':
                content = self._download_gcs_file(key)
            elif self.storage_type == 'dbfs':
                content = self._download_dbfs_file(key)
            else:
                raise ValueError(f"Unsupported storage type: {self.storage_type}")
            
            if local_path:
                with open(local_path, 'wb') as f:
                    f.write(content)
                self.logger.info(f"Downloaded {key} to {local_path}")
            
            return content
        
        except Exception as e:
            self.logger.error(f"Failed to download {key}: {str(e)}")
            raise
    
    def _download_s3_file(self, key: str) -> bytes:
        """Download file from S3."""
        response = self._client.get_object(Bucket=self.bucket, Key=key)
        return response['Body'].read()
    
    def _download_azure_blob(self, key: str) -> bytes:
        """Download blob from Azure."""
        blob_client = self._client.get_blob_client(container=self.bucket, blob=key)
        return blob_client.download_blob().readall()
    
    def _download_gcs_file(self, key: str) -> bytes:
        """Download file from GCS."""
        bucket = self._client.get_bucket(self.bucket)
        blob = bucket.blob(key)
        return blob.download_as_bytes()
    
    def _download_dbfs_file(self, key: str) -> bytes:
        """Download file from DBFS."""
        path = f"/dbfs/{key}" if not key.startswith('/dbfs/') else key
        content = self._client.dbfs.read(path)
        return content.data
    
    def upload_file(self, key: str, content: bytes, metadata: Optional[Dict] = None) -> bool:
        """
        Upload a file to storage.
        
        Args:
            key: Object key/path
            content: File content as bytes
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        if not self._connected:
            self.connect()
        
        try:
            if self.storage_type == 's3':
                self._upload_s3_file(key, content, metadata)
            elif self.storage_type == 'azure_blob':
                self._upload_azure_blob(key, content, metadata)
            elif self.storage_type == 'gcs':
                self._upload_gcs_file(key, content, metadata)
            elif self.storage_type == 'dbfs':
                self._upload_dbfs_file(key, content)
            
            self.logger.info(f"Uploaded {key} successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to upload {key}: {str(e)}")
            raise
    
    def _upload_s3_file(self, key: str, content: bytes, metadata: Optional[Dict]):
        """Upload file to S3."""
        extra_args = {'Metadata': metadata} if metadata else {}
        self._client.put_object(Bucket=self.bucket, Key=key, Body=content, **extra_args)
    
    def _upload_azure_blob(self, key: str, content: bytes, metadata: Optional[Dict]):
        """Upload blob to Azure."""
        blob_client = self._client.get_blob_client(container=self.bucket, blob=key)
        blob_client.upload_blob(content, metadata=metadata, overwrite=True)
    
    def _upload_gcs_file(self, key: str, content: bytes, metadata: Optional[Dict]):
        """Upload file to GCS."""
        bucket = self._client.get_bucket(self.bucket)
        blob = bucket.blob(key)
        if metadata:
            blob.metadata = metadata
        blob.upload_from_string(content)
    
    def _upload_dbfs_file(self, key: str, content: bytes):
        """Upload file to DBFS."""
        path = f"/dbfs/{key}" if not key.startswith('/dbfs/') else key
        self._client.dbfs.put(path, content, overwrite=True)
    
    def validate_connection(self) -> ConnectionStatus:
        """
        Validate storage connection.
        
        Returns:
            ConnectionStatus object
        """
        if not self._connected or not self._client:
            return ConnectionStatus(
                is_connected=False,
                message="Not connected"
            )
        
        try:
            # Try to list objects with max 1 result
            self.fetch_data(prefix="", max_keys=1)
            
            return ConnectionStatus(
                is_connected=True,
                message="Connection is valid"
            )
        
        except Exception as e:
            return ConnectionStatus(
                is_connected=False,
                message=f"Connection validation failed: {str(e)}"
            )
