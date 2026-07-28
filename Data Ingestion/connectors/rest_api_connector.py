import requests
from typing import Dict, List, Optional, Any
import time
from urllib.parse import urljoin

from .base_connector import BaseConnector, ConnectorConfig, ConnectionStatus


class RESTAPIConnector(BaseConnector):
    """Connector for REST API data sources."""
    
    def __init__(self, config: ConnectorConfig):
        """
        Initialize REST API connector.
        
        Required config:
            - base_url: Base URL of the API
        Optional config:
            - auth_type: 'bearer', 'basic', 'api_key', or None
            - token: Bearer token (if auth_type='bearer')
            - api_key: API key (if auth_type='api_key')
            - api_key_header: Header name for API key (default: 'X-API-Key')
            - username: Username for basic auth
            - password: Password for basic auth
            - headers: Additional headers
            - timeout: Request timeout in seconds (default: 30)
            - max_retries: Maximum number of retries (default: 3)
            - retry_delay: Delay between retries in seconds (default: 1)
        """
        super().__init__(config)
        self.base_url = config.get('base_url')
        if not self.base_url:
            raise ValueError("base_url is required in config")
        
        self.session = requests.Session()
        self._setup_authentication()
        self._setup_headers()
    
    def _setup_authentication(self):
        """Setup authentication for the session."""
        auth_type = self.config.get('auth_type', '').lower()
        
        if auth_type == 'bearer':
            token = self.config.get('token')
            if token:
                self.session.headers['Authorization'] = f'Bearer {token}'
        
        elif auth_type == 'api_key':
            api_key = self.config.get('api_key')
            api_key_header = self.config.get('api_key_header', 'X-API-Key')
            if api_key:
                self.session.headers[api_key_header] = api_key
        
        elif auth_type == 'basic':
            username = self.config.get('username')
            password = self.config.get('password')
            if username and password:
                self.session.auth = (username, password)
    
    def _setup_headers(self):
        """Setup additional headers."""
        headers = self.config.get('headers', {})
        if headers:
            self.session.headers.update(headers)
        
        # Set default content type if not specified
        if 'Content-Type' not in self.session.headers:
            self.session.headers['Content-Type'] = 'application/json'
    
    def connect(self) -> ConnectionStatus:
        """
        Establish connection (validate base URL and auth).
        
        Returns:
            ConnectionStatus object
        """
        try:
            # Try a simple GET request to validate connection
            health_endpoint = self.config.get('health_endpoint', '')
            url = urljoin(self.base_url, health_endpoint) if health_endpoint else self.base_url
            
            timeout = self.config.get('timeout', 30)
            response = self.session.get(url, timeout=timeout)
            
            self._connected = True
            self.logger.info(f"Successfully connected to {self.base_url}")
            
            return ConnectionStatus(
                is_connected=True,
                message="Connection successful",
                metadata={"status_code": response.status_code, "url": url}
            )
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Connection failed: {str(e)}")
            return ConnectionStatus(
                is_connected=False,
                message=f"Connection failed: {str(e)}"
            )
    
    def disconnect(self) -> bool:
        """
        Close the session.
        
        Returns:
            True if successful
        """
        try:
            self.session.close()
            self._connected = False
            self.logger.info("Session closed")
            return True
        except Exception as e:
            self.logger.error(f"Error closing session: {str(e)}")
            return False
    
    def fetch_data(
        self,
        query: Optional[Dict] = None,
        endpoint: str = "",
        method: str = "GET",
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        **kwargs
    ) -> List[Dict]:
        """
        Fetch data from the REST API.
        
        Args:
            query: Legacy parameter (use params instead)
            endpoint: API endpoint path
            method: HTTP method (GET, POST, PUT, DELETE)
            params: URL parameters
            data: Form data
            json_data: JSON payload
            **kwargs: Additional arguments for requests
            
        Returns:
            List of records
        """
        if not self._connected:
            self.connect()
        
        # Use query as params if params not provided (backwards compatibility)
        if query and not params:
            params = query
        
        url = urljoin(self.base_url, endpoint)
        timeout = self.config.get('timeout', 30)
        max_retries = self.config.get('max_retries', 3)
        retry_delay = self.config.get('retry_delay', 1)
        
        for attempt in range(max_retries):
            try:
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    data=data,
                    json=json_data,
                    timeout=timeout,
                    **kwargs
                )
                response.raise_for_status()
                
                # Try to parse JSON response
                try:
                    result = response.json()
                    # Ensure we return a list
                    if isinstance(result, list):
                        return result
                    elif isinstance(result, dict):
                        # Check common pagination patterns
                        if 'data' in result and isinstance(result['data'], list):
                            return result['data']
                        elif 'results' in result and isinstance(result['results'], list):
                            return result['results']
                        elif 'items' in result and isinstance(result['items'], list):
                            return result['items']
                        else:
                            return [result]
                    else:
                        return [{"value": result}]
                
                except ValueError:
                    # Response is not JSON
                    return [{"response": response.text}]
            
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"All retry attempts failed for {url}")
                    raise
        
        return []
    
    def validate_connection(self) -> ConnectionStatus:
        """
        Validate the connection is still active.
        
        Returns:
            ConnectionStatus object
        """
        if not self._connected:
            return ConnectionStatus(
                is_connected=False,
                message="Not connected"
            )
        
        return self.connect()  # Revalidate by attempting connection
    
    def paginated_fetch(
        self,
        endpoint: str,
        page_param: str = "page",
        page_size_param: str = "page_size",
        page_size: int = 100,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> List[Dict]:
        """
        Fetch paginated data from API.
        
        Args:
            endpoint: API endpoint
            page_param: Parameter name for page number
            page_size_param: Parameter name for page size
            page_size: Number of items per page
            max_pages: Maximum number of pages to fetch (None for all)
            **kwargs: Additional arguments for fetch_data
            
        Returns:
            Combined list of all records
        """
        all_data = []
        page = 1
        
        while True:
            if max_pages and page > max_pages:
                break
            
            params = kwargs.get('params', {})
            params[page_param] = page
            params[page_size_param] = page_size
            kwargs['params'] = params
            
            data = self.fetch_data(endpoint=endpoint, **kwargs)
            
            if not data:
                break
            
            all_data.extend(data)
            
            # If we got less than page_size, we're done
            if len(data) < page_size:
                break
            
            page += 1
        
        self.logger.info(f"Fetched {len(all_data)} records across {page} pages")
        return all_data
