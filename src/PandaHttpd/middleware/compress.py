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
    COMPRESS_TYPE: str = 'gzip'
    GZIP_MIN_SIZE = 500
    GZIP_CONTENT_TYPES = (
        # Web Document Formats
        'text/html',
        'text/css',
        'text/plain',
        'text/xml',
        'text/markdown',
        'text/cache-manifest',
        'text/vcard',
        'text/vnd.rim.location.xloc',
        'text/vtt',
        'text/x-component',
        'text/x-cross-domain-policy',

        # Scripts and JSON
        'application/javascript',
        'application/json',
        'application/x-javascript',
        'application/ld+json',
        'application/manifest+json',
        'application/schema+json',
        'application/vnd.geo+json',
        'application/x-web-app-manifest+json',
        'text/javascript', # Legacy support

        # XML and Structured Data
        'application/xml',
        'application/atom+xml',
        'application/rss+xml',
        'application/xhtml+xml',
        'application/soap+xml',
        'application/rdf+xml',
        'application/vnd.mozilla.xul+xml',
        'application/wsdl+xml',
        
        # YAML
        'text/yaml',
        'text/x-yaml',
        'application/yaml',
        'application/x-yaml',

        # Fonts (Only specific types!)
        # WOFF and WOFF2 are already compressed. Only compress these older/raw formats:
        'application/vnd.ms-fontobject', # EOT
        'application/x-font-ttf',        # TTF
        'application/x-font-opentype',   # OTF
        'application/x-font-truetype',
        'font/eot',
        'font/opentype',
        'font/otf',
        'font/ttf',
        
        # Images (Only Vector!)
        'image/svg+xml',
        'image/x-icon', # Favicons often compress well
        'image/bmp',    # Uncompressed bitmap
    )
        
    def __init__(self, min_size: int = GZIP_MIN_SIZE, compress_level: int = 6):
        """
        min_size: Minimum response body size to trigger compression (default: 500 bytes)
        compress_level: Gzip compression level 1-9 (default: 6, balanced speed/ratio)
        """
        super().__init__()
        self.min_size = min_size
        self.compress_level = compress_level
        self.compress_type = self.COMPRESS_TYPE
        
    def post(self, dict_headers: MappingStr, response: Response) -> Response:
        accept_encoding = str(response.header.get(b'accept-encoding', b''))
        if self.compress_type not in accept_encoding.lower():
            return response

        if response.header.get(b'content-encoding'):
            return response
        
        if not response.body or len(response.body) < self.min_size:
            return response
        
        if not self._is_compressible_content_type(response):
            return response
        
        compressed_body = gzip.compress(response.body, compresslevel=self.compress_level)
        
        if len(compressed_body) >= len(response.body):
            return response
        
        response.body = compressed_body
        response.update_header('content-length', str(len(compressed_body)))
        response.update_header('content-encoding', self.COMPRESS_TYPE)
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
    