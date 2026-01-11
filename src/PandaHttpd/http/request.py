import enum
import json

from urllib.parse import parse_qs
from nguyenpanda.swan import green

from typing import Tuple, Dict, Optional
from .._typing import Socket


class ParseRequestBody:

    class Type(enum.StrEnum):
        TEXT = 'text/plain'
        FORM = 'application/x-www-form-urlencoded'
        JSON = 'application/json'
        XML = 'application/xml'

    @staticmethod
    def parse(content_type: str, content: bytes) -> Dict[str, str]:
        _t = ParseRequestBody.Type
        if content_type.startswith((_t.FORM, _t.TEXT)):
            return ParseRequestBody.parse_form(content.decode('utf-8', 'ignore'))
        elif content_type.startswith(_t.JSON):
            return ParseRequestBody.parse_json(content)
        elif content_type.startswith(_t.XML):
            return ParseRequestBody.parse_xml(content)
        else:
            raise TypeError(f'Unsupported Content-Type: {content_type}')

    @staticmethod
    def parse_form(content: str) -> Dict[str, str]:
        result = {}
        parsed = parse_qs(content)
        for k, v in parsed.items():
            result[k] = v[0] if v else ''
        return result

    @staticmethod
    def parse_json(content: bytes) -> Dict[str, str]:
        try:
            return json.loads(content.decode('utf-8'))
        except Exception:
            raise ValueError('Invalid JSON body')

    @staticmethod
    def parse_xml(content: bytes) -> Dict[str, str]:
        raise NotImplementedError('XML parsing not implemented')
    

class HttpConnection:
    pass


class Request(HttpConnection):

    def __init__(self, client_connection: Socket) -> None:
        super().__init__()
        self.client_connection: Socket = client_connection
        self._method: str = ''
        self._path: str = ''
        self._protocol: str = ''
        self._headers: Dict[str, str] = {}
        self._cookie: Dict[str, str] = {}
        self._body: bytes | Dict[str, str] = b''
        self._raw_data: bytearray | None = None

    def handle(self):
        self._raw_data = self._recv_header()
        if self._raw_data is None:
            return
        
        self._method, self._path, self._protocol, self._headers \
            = self._parse_header(self._raw_data)
        
        body = self._recv_body(self._raw_data)
        self._raw_data.extend(body)
        
        content_length = int(self._headers.get('content-length', 0))
        if content_length > 0:
            ct = self._headers.get('content-type', '')
            print(ct)
            if self._method == 'POST' or self._method == 'PUT':
                self._body = ParseRequestBody.parse(ct, body)
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
    def headers(self) -> Dict[str, str]:
        return self._headers

    @property
    def cookie(self) -> Dict[str, str]:
        return self._cookie
    
    @property
    def body(self) -> bytes | Dict[str, str]:
        return self._body
    
    @property
    def protocol(self) -> str:
        return self._protocol

    def _parse_header(self, raw_data: bytearray) -> Tuple[str, str, str, Dict[str, str]]:
        idx = raw_data.find(b'\r\n\r\n')
        header_bytes = raw_data[:idx]
            
        try:
            header_str = header_bytes.decode('utf-8')
        except UnicodeDecodeError:
            header_str = header_bytes.decode('iso-8859-1')
         
        lines = header_str.split('\r\n')
        
        if not lines or not lines[0]:
            return '', '', '', {}

        method, path, protocol = lines[0].split(None)
        
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        return method.upper(), path, protocol, headers
        
    def _parse_cookie(self, cookie_str: Optional[str]) -> Dict[str, str]:
        if cookie_str is None:
            return {}
        
        cookie = {}
        for pair in cookie_str.split(';'):
            if '=' in pair:
                k, v = pair.strip().split('=', 1)
                cookie[k] = v
        
        return cookie

    def _recv_header(self) -> Optional[bytearray]:
        buffer = bytearray()
        while True:
            chunk = self.client_connection.recv(4096)
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
            chunk = self.client_connection.recv(min(4096, remaining))
            if not chunk:
                break
            body.extend(chunk)
            remaining -= len(chunk)
        return body
    