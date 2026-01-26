from ..utils import (
    CaseInsensitiveDict, 
    CookieDict,
    UrlParser,
    RequestBodyParser,
)


from typing import Any, Tuple, Dict, Optional
from .._typing import Socket


class HttpConnection:
    pass


class Request(HttpConnection):

    def __init__(self, client_connection: Socket) -> None:
        super().__init__()
        self._client_connection: Socket = client_connection
        self._method: str = ''
        self._path: str = ''
        self._protocol: str = ''
        self._headers: CaseInsensitiveDict = CaseInsensitiveDict()
        self._cookie: CookieDict = CookieDict()
        self._body: bytes | Dict[str, Any] = b''
        self._raw_data: bytearray | None = None
        self._query_params: Dict[str, str] = {}

    def handle(self):
        self._raw_data = self._recv_header()
        if self._raw_data is None:
            return
        
        self._method, raw_url_path, self._protocol, self._headers \
            = self._parse_header(self._raw_data)
            
        self._path, self._query_params = UrlParser.parse_url(raw_url_path)
        
        body = self._recv_body(self._raw_data)
        self._raw_data.extend(body)
        
        content_length = int(self._headers.get('content-length', 0))
        if content_length > 0:
            ct = self._headers.get('content-type', '')
            if self._method == 'POST' or self._method == 'PUT':
                self._body = RequestBodyParser.parse(ct, body)
            else:
                self._body = body
                
        self._cookie = self._parse_cookie(self._headers.pop('cookie', None))
        
    @property
    def method(self) -> str:
        return self._method

    @property
    def path(self) -> str:
        return self._path
    
    @property
    def query_params(self) -> Dict[str, str]:
        return self._query_params

    @property
    def headers(self) -> CaseInsensitiveDict:
        return self._headers

    @property
    def cookie(self) -> CookieDict:
        return self._cookie
    
    @property
    def body(self) -> bytes | Dict[str, Any]:
        return self._body
    
    @property
    def protocol(self) -> str:
        return self._protocol
    
    @property
    def client_connection(self) -> Socket:
        return self._client_connection
    
    def _parse_header(self, raw_data: bytearray) -> Tuple[str, str, str, CaseInsensitiveDict]:
        idx = raw_data.find(b'\r\n\r\n')
        header_bytes = raw_data[:idx]
            
        try:
            header_str = header_bytes.decode('utf-8')
        except UnicodeDecodeError:
            header_str = header_bytes.decode('iso-8859-1')
         
        lines = header_str.split('\r\n')
        
        if not lines or not lines[0]:
            return '', '', '', CaseInsensitiveDict()

        parts = lines[0].split(None)
        if len(parts) == 3:
            method, path, protocol = parts
        elif len(parts) == 2:
            method, path = parts
            protocol = "HTTP/1.1"
        else:
            method, path, protocol = "GET", "/", "HTTP/1.1"
        
        headers = CaseInsensitiveDict()
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
        
        return method.upper(), path, protocol, headers
        
    def _parse_cookie(self, cookie_str: Optional[str]) -> CookieDict:
        if cookie_str is None:
            return CookieDict()
        
        cookie = CookieDict()
        for pair in cookie_str.split(';'):
            if '=' in pair:
                k, v = pair.strip().split('=', 1)
                cookie[k] = UrlParser.unquote(v)
        
        return cookie

    def _recv_header(self) -> Optional[bytearray]:
        buffer = bytearray()
        while True:
            chunk = self._client_connection.recv(4096)
            if not chunk:
                return None
            buffer.extend(chunk)
                
            if b'\r\n\r\n' in buffer:
                break
        return buffer
       
    def _recv_body(self, header_buffer: bytearray) -> bytearray:
        idx = header_buffer.find(b'\r\n\r\n')
        body_start = header_buffer[idx+4:]

        content_length = int(self._headers.get('content-length', 0))
        already = len(body_start)

        if already >= content_length:
            return body_start[:content_length]
        
        body = bytearray(body_start)
        remaining = content_length - already

        while remaining > 0:
            chunk = self._client_connection.recv(min(4096, remaining))
            if not chunk:
                break
            body.extend(chunk)
            remaining -= len(chunk)
        return body
    