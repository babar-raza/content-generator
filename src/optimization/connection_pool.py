"""Connection pool for HTTP clients with sync and async support."""
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from typing import Optional, Dict, Any
import asyncio

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None


class ConnectionPool:
    """Persistent connection pool for synchronous HTTP requests."""
    
    def __init__(
        self,
        pool_size: int = 20,
        max_retries: int = 3,
        timeout: int = 30,
        backoff_factor: float = 0.5
    ):
        """Initialize connection pool.
        
        Args:
            pool_size: Size of connection pool
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
            backoff_factor: Backoff factor for retries
        """
        self.session = requests.Session()
        self.timeout = timeout
        
        # Configure retries with exponential backoff
        retry = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        # Configure adapter with pool
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size,
            max_retries=retry,
            pool_block=False
        )
        
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'Python/ConnectionPool',
            'Connection': 'keep-alive'
        })
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Perform GET request.
        
        Args:
            url: Target URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object
        """
        kwargs.setdefault('timeout', self.timeout)
        return self.session.get(url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Perform POST request.
        
        Args:
            url: Target URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object
        """
        kwargs.setdefault('timeout', self.timeout)
        return self.session.post(url, **kwargs)
    
    def put(self, url: str, **kwargs) -> requests.Response:
        """Perform PUT request."""
        kwargs.setdefault('timeout', self.timeout)
        return self.session.put(url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> requests.Response:
        """Perform DELETE request."""
        kwargs.setdefault('timeout', self.timeout)
        return self.session.delete(url, **kwargs)
    
    def close(self):
        """Close all connections in pool."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class AsyncConnectionPool:
    """Persistent connection pool for asynchronous HTTP requests."""
    
    def __init__(
        self,
        pool_size: int = 20,
        timeout: int = 30,
        ttl_dns_cache: int = 300
    ):
        """Initialize async connection pool.
        
        Args:
            pool_size: Connection pool size
            timeout: Request timeout in seconds
            ttl_dns_cache: DNS cache TTL in seconds
            
        Raises:
            ImportError: If aiohttp not available
        """
        if not AIOHTTP_AVAILABLE:
            raise ImportError(
                "aiohttp not available. "
                "Install with: pip install aiohttp"
            )
        
        self.pool_size = pool_size
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.ttl_dns_cache = ttl_dns_cache
        self._session = None
        self._lock = asyncio.Lock()
    
    async def _get_session(self):
        """Get or create session (lazy initialization)."""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=self.pool_size,
                        limit_per_host=self.pool_size // 2,
                        ttl_dns_cache=self.ttl_dns_cache,
                        enable_cleanup_closed=True
                    )
                    self._session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=self.timeout,
                        headers={
                            'User-Agent': 'Python/AsyncConnectionPool',
                            'Connection': 'keep-alive'
                        }
                    )
        return self._session
    
    async def get(self, url: str, **kwargs):
        """Perform async GET request.
        
        Args:
            url: Target URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object
        """
        session = await self._get_session()
        return await session.get(url, **kwargs)
    
    async def post(self, url: str, **kwargs):
        """Perform async POST request.
        
        Args:
            url: Target URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object
        """
        session = await self._get_session()
        return await session.post(url, **kwargs)
    
    async def put(self, url: str, **kwargs):
        """Perform async PUT request."""
        session = await self._get_session()
        return await session.put(url, **kwargs)
    
    async def delete(self, url: str, **kwargs):
        """Perform async DELETE request."""
        session = await self._get_session()
        return await session.delete(url, **kwargs)
    
    async def close(self):
        """Close all connections in pool."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._get_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
