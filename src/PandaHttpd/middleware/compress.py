import gzip

from .base import BaseMiddleware
from ..http import Request, Response
from ..utils import MappingStr


class GZipMiddleware(BaseMiddleware):
    """
    Middleware that compresses response bodies using gzip encoding.
    
    This middleware:
    1. Checks if the client accepts gzip encoding via the Accept-Encoding header
    2. Compresses the response body if:
       - The client accepts gzip
       - The response body is large enough (>= GZIP_MIN_SIZE bytes)
       - The content type is compressible (text/*, application/json, etc.)
    3. Updates the response headers:
       - Content-Encoding: gzip
       - Content-Length: updated to compressed size
       - Vary: Accept-Encoding
    """
    GZIP_MIN_SIZE = 500
    GZIP_CONTENT_TYPES = (
        'text/',
        'application/json',
        'application/javascript',
        'application/xml',
        'application/xhtml+xml',
        'image/svg+xml',
    )
    
    def __init__(self, min_size: int = GZIP_MIN_SIZE, compress_level: int = 6):
        """
        min_size: Minimum response body size to trigger compression (default: 500 bytes)
        compress_level: Gzip compression level 1-9 (default: 6, balanced speed/ratio)
        """
        super().__init__()
        self.min_size = min_size
        self.compress_level = compress_level
    
    def pre(self, dict_headers: MappingStr, request: Request) -> MappingStr:
        accept_encoding = request.headers.get('accept-encoding', '')
        dict_headers['_gzip'] = 'gzip' if 'gzip' in accept_encoding.lower() else ''
        return dict_headers
    
    def post(self, dict_headers: MappingStr, response: Response) -> Response:
        if response.header.pop(b'_gzip', b'') != b'gzip':
            return response
        
        if not response.body or len(response.body) < self.min_size:
            return response
        
        if not self._is_compressible_content_type(response):
            return response
        
        if not b'content-encoding' in response.header.keys():
            return response
        
        compressed_body = gzip.compress(response.body, compresslevel=self.compress_level)
        if len(compressed_body) >= len(response.body):
            return response
        
        response.body = compressed_body
        response.update_header('content-length', str(len(compressed_body)))
        response.update_header('content-encoding', 'gzip')
        response.update_header('vary', 'Accept-Encoding')
        return response
    
    def _is_compressible_content_type(self, response: Response) -> bool:
        content_type = response.header.get(b'content-type', b'').lower()
        
        if not content_type:
            return False
        
        for compressible_type in self.GZIP_CONTENT_TYPES:
            if content_type.startswith(compressible_type.encode()):
                return True
        return False
    