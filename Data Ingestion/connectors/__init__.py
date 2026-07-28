"""Data AI Scaffold - Connectors Package.

This package provides a unified interface for connecting to various data sources.
"""

from .base_connector import BaseConnector, ConnectorConfig, ConnectionStatus
from .rest_api_connector import RESTAPIConnector
from .database_connector import DatabaseConnector
from .storage_connector import StorageConnector

__all__ = [
    'BaseConnector',
    'ConnectorConfig',
    'ConnectionStatus',
    'RESTAPIConnector',
    'DatabaseConnector',
    'StorageConnector',
]

__version__ = '1.0.0'
