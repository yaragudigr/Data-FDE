from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging


class ConnectorConfig:
    """Configuration class for connectors."""
    
    def __init__(self, **kwargs):
        self.config = kwargs
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return self.config.copy()


class ConnectionStatus:
    """Status of a connector connection."""
    
    def __init__(self, is_connected: bool, message: str = "", metadata: Optional[Dict] = None):
        self.is_connected = is_connected
        self.message = message
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def __repr__(self):
        return f"ConnectionStatus(is_connected={self.is_connected}, message='{self.message}')"


class BaseConnector(ABC):
    """Abstract base class for all data connectors."""
    
    def __init__(self, config: ConnectorConfig):
        """
        Initialize the connector.
        
        Args:
            config: ConnectorConfig object with connector-specific settings
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connected = False
        self._connection = None
    
    @abstractmethod
    def connect(self) -> ConnectionStatus:
        """
        Establish connection to the data source.
        
        Returns:
            ConnectionStatus object indicating success/failure
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close connection to the data source.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def fetch_data(self, query: Optional[Dict] = None, **kwargs) -> List[Dict]:
        """
        Fetch data from the source.
        
        Args:
            query: Query parameters specific to the connector type
            **kwargs: Additional arguments
            
        Returns:
            List of records as dictionaries
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> ConnectionStatus:
        """
        Validate that the connection is active and working.
        
        Returns:
            ConnectionStatus object
        """
        pass
    
    def get_metadata(self) -> Dict:
        """
        Get metadata about the connector and connection.
        
        Returns:
            Dictionary with metadata
        """
        return {
            "connector_type": self.__class__.__name__,
            "is_connected": self._connected,
            "config": {k: v for k, v in self.config.to_dict().items() if "password" not in k.lower() and "secret" not in k.lower() and "token" not in k.lower() and "key" not in k.lower()}
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
