from typing import Dict, List, Optional, Any
import logging

try:
    from databricks import sql as databricks_sql
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

from .base_connector import BaseConnector, ConnectorConfig, ConnectionStatus


class DatabaseConnector(BaseConnector):
    """Connector for SQL database sources."""
    
    SUPPORTED_TYPES = ['databricks', 'postgres', 'mysql', 'sqlite']
    
    def __init__(self, config: ConnectorConfig):
        """
        Initialize database connector.
        
        Required config:
            - db_type: Type of database ('databricks', 'postgres', 'mysql', 'sqlite')
            - host: Database host (not needed for sqlite)
            - database: Database name
        
        Optional config (depending on db_type):
            - port: Database port
            - username: Username
            - password: Password
            - http_path: HTTP path for Databricks SQL Warehouse
            - access_token: Access token for Databricks
            - catalog: Databricks Unity Catalog name
            - schema: Database schema
        """
        super().__init__(config)
        
        self.db_type = config.get('db_type', '').lower()
        if self.db_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported database type: {self.db_type}. Supported types: {self.SUPPORTED_TYPES}")
        
        self._validate_dependencies()
        
        self.host = config.get('host')
        self.port = config.get('port')
        self.database = config.get('database')
        self.username = config.get('username')
        self.password = config.get('password')
        
        self._connection = None
        self._cursor = None
    
    def _validate_dependencies(self):
        """Validate required dependencies are installed."""
        if self.db_type == 'databricks' and not DATABRICKS_AVAILABLE:
            raise ImportError("databricks-sql-connector is required for Databricks. Install with: pip install databricks-sql-connector")
        elif self.db_type == 'postgres' and not POSTGRES_AVAILABLE:
            raise ImportError("psycopg2 is required for PostgreSQL. Install with: pip install psycopg2-binary")
        elif self.db_type == 'mysql' and not MYSQL_AVAILABLE:
            raise ImportError("mysql-connector-python is required for MySQL. Install with: pip install mysql-connector-python")
    
    def connect(self) -> ConnectionStatus:
        """
        Establish database connection.
        
        Returns:
            ConnectionStatus object
        """
        try:
            if self.db_type == 'databricks':
                self._connect_databricks()
            elif self.db_type == 'postgres':
                self._connect_postgres()
            elif self.db_type == 'mysql':
                self._connect_mysql()
            elif self.db_type == 'sqlite':
                self._connect_sqlite()
            
            self._connected = True
            self.logger.info(f"Successfully connected to {self.db_type} database")
            
            return ConnectionStatus(
                is_connected=True,
                message="Database connection successful",
                metadata={"db_type": self.db_type, "database": self.database}
            )
        
        except Exception as e:
            self.logger.error(f"Database connection failed: {str(e)}")
            return ConnectionStatus(
                is_connected=False,
                message=f"Connection failed: {str(e)}"
            )
    
    def _connect_databricks(self):
        """Connect to Databricks SQL Warehouse."""
        self._connection = databricks_sql.connect(
            server_hostname=self.host,
            http_path=self.config.get('http_path'),
            access_token=self.config.get('access_token'),
            catalog=self.config.get('catalog'),
            schema=self.config.get('schema')
        )
    
    def _connect_postgres(self):
        """Connect to PostgreSQL database."""
        self._connection = psycopg2.connect(
            host=self.host,
            port=self.port or 5432,
            database=self.database,
            user=self.username,
            password=self.password
        )
    
    def _connect_mysql(self):
        """Connect to MySQL database."""
        self._connection = mysql.connector.connect(
            host=self.host,
            port=self.port or 3306,
            database=self.database,
            user=self.username,
            password=self.password
        )
    
    def _connect_sqlite(self):
        """Connect to SQLite database."""
        import sqlite3
        self._connection = sqlite3.connect(self.database)
        self._connection.row_factory = sqlite3.Row
    
    def disconnect(self) -> bool:
        """
        Close database connection.
        
        Returns:
            True if successful
        """
        try:
            if self._cursor:
                self._cursor.close()
            if self._connection:
                self._connection.close()
            
            self._connected = False
            self._connection = None
            self._cursor = None
            
            self.logger.info("Database connection closed")
            return True
        
        except Exception as e:
            self.logger.error(f"Error closing connection: {str(e)}")
            return False
    
    def fetch_data(
        self,
        query: Optional[Dict] = None,
        sql: Optional[str] = None,
        params: Optional[tuple] = None,
        **kwargs
    ) -> List[Dict]:
        """
        Execute SQL query and fetch results.
        
        Args:
            query: Dict with 'sql' key (legacy parameter)
            sql: SQL query string
            params: Query parameters for parameterized queries
            **kwargs: Additional arguments
            
        Returns:
            List of records as dictionaries
        """
        if not self._connected:
            self.connect()
        
        # Handle legacy query parameter
        if query and not sql:
            sql = query.get('sql')
        
        if not sql:
            raise ValueError("SQL query is required")
        
        try:
            if self.db_type == 'postgres':
                cursor = self._connection.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = self._connection.cursor()
            
            # Execute query
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # Fetch results
            results = cursor.fetchall()
            
            # Convert to list of dicts
            if self.db_type == 'sqlite':
                data = [dict(row) for row in results]
            elif self.db_type == 'postgres':
                data = [dict(row) for row in results]
            elif self.db_type in ['databricks', 'mysql']:
                columns = [desc[0] for desc in cursor.description]
                data = [dict(zip(columns, row)) for row in results]
            else:
                data = []
            
            cursor.close()
            
            self.logger.info(f"Fetched {len(data)} records")
            return data
        
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def execute_query(self, sql: str, params: Optional[tuple] = None) -> int:
        """
        Execute a SQL statement (INSERT, UPDATE, DELETE, etc.).
        
        Args:
            sql: SQL statement
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        if not self._connected:
            self.connect()
        
        try:
            cursor = self._connection.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            self._connection.commit()
            affected_rows = cursor.rowcount
            
            cursor.close()
            
            self.logger.info(f"Query executed, {affected_rows} rows affected")
            return affected_rows
        
        except Exception as e:
            self._connection.rollback()
            self.logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def validate_connection(self) -> ConnectionStatus:
        """
        Validate database connection.
        
        Returns:
            ConnectionStatus object
        """
        if not self._connected or not self._connection:
            return ConnectionStatus(
                is_connected=False,
                message="Not connected"
            )
        
        try:
            # Try a simple query
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            
            return ConnectionStatus(
                is_connected=True,
                message="Connection is valid"
            )
        
        except Exception as e:
            return ConnectionStatus(
                is_connected=False,
                message=f"Connection validation failed: {str(e)}"
            )
    
    def get_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        Get list of tables in the database.
        
        Args:
            schema: Schema name (optional)
            
        Returns:
            List of table names
        """
        if self.db_type == 'databricks':
            sql = f"SHOW TABLES IN {schema}" if schema else "SHOW TABLES"
        elif self.db_type == 'postgres':
            schema = schema or 'public'
            sql = f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema}'"
        elif self.db_type == 'mysql':
            sql = "SHOW TABLES"
        elif self.db_type == 'sqlite':
            sql = "SELECT name FROM sqlite_master WHERE type='table'"
        else:
            return []
        
        results = self.fetch_data(sql=sql)
        
        # Extract table names from results
        if results:
            first_key = list(results[0].keys())[0]
            return [row[first_key] for row in results]
        
        return []
