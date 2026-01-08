from .status import HttpStatus
from .._typing import Socket

import json
from typing_extensions import Optional, Any


class Response:
    media_type: str
    charset: str = 'utf-8'
    
    def __init__(self, 
		status_code: int | HttpStatus = 200, 
  		body: Any = None,
    	media_type: Optional[str] = None,
		dict_headers: Optional[dict[str, str]] = None,
    ):
        self.status_code: HttpStatus = (status_code if isinstance(status_code, HttpStatus) else HttpStatus(status_code))
        if media_type is not None:
            self.media_type: str = media_type
        self.headers: list[tuple[bytes, bytes]] = []
        self.body: bytes = self.render(body)
        self.init_header(dict_headers)
    
    def render(self, content: Any) -> bytes:
        if content is None:
            return b''
        elif isinstance(content, bytes):
            return content
        else:
            return content.encode(self.charset)
    
    def init_header(self, dict_header: Optional[dict[str, str]] = None):
        self.list_headers: list[tuple[bytes, bytes]]
        if dict_header is None:
            self.list_headers = []
            already_have_content_type = False
            already_have_content_length = False
        else:
            self.list_headers = [
                (k.lower().encode(self.charset), v.encode(self.charset))
				for k, v in dict_header.items()
    		]
            k = dict_header.keys()
            already_have_content_type = b'content-type' in k
            already_have_content_length = b'content-length' in k
            
        if (
            self.body is not None
            and already_have_content_length is False
            and not (self.status_code < 200 or self.status_code in (204, 304))
        ):
            content_length = str(len(self.body))
            self.list_headers.append((b'content-length', content_length.encode(self.charset)))
            
        if (self.media_type is not None
            and already_have_content_type is False
        ):
            if self.media_type.startswith('text/') and 'charset=' not in self.media_type.lower():
                self.media_type += '; charset=' + self.charset
            self.list_headers.append((b'content-type', self.media_type.encode(self.charset)))
        
    @property
    def header(self):
        pass
    
    def set_cookies(self,
        key: str,
        value: str,
        expires: Optional[str] = None,
        max_age: Optional[int] = None,
    ):
        raise NotImplementedError()
    
    def delete_cookies(self,
        key: str,
        value: str = '',
        expires: Optional[str] = None,
        max_age: Optional[int] = None,
    ):
        raise NotImplementedError()
		
    def to_bytes(self) -> bytes:
        status_line = f'HTTP/1.1 {self.status_code} {self.status_code.phrase if hasattr(self.status_code, 'phrase') else ''} \r\n'.encode(self.charset)
        headers = b''
        for k, v in self.list_headers:
            headers += k + b': ' + v + b'\r\n'
        headers += b'\r\n'
        return status_line + headers + self.body
    
    def __call__(self, sender: Socket, receiver: Optional[Socket]) -> None:
        status_line = f'HTTP/1.1 {self.status_code.value} {self.status_code.phrase}\r\n'.encode(self.charset)

        header_block = b''
        for k, v in self.list_headers:
            header_block += k + b': ' + v + b'\r\n'
        header_block += b'\r\n'
        
        sender.sendall(status_line + header_block)
        
        if self.body:
            sender.sendall(self.body)


class PlainTextResponse(Response):
    media_type: str = 'text/plain'
    
        
class HtmlResponse(Response):
    media_type: str = 'text/html'
    

class CssResponse(Response):
    media_type: str = 'text/css'
    

class JsResponse(Response):
    media_type: str = 'text/javascript'
    

class PDFResponse(Response):
    media_type: str = 'text/pdf'
    

class JsonResponse(Response):
    media_type: str = 'application/json'
    
    def render(self, content: Any) -> bytes:
        return json.dumps(content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(',', ':'),
        ).encode(self.charset)
    
    
class ManifestResponse(Response):
    media_type: str = 'application/manifest+json'
    

class BinaryResponse(Response):
    media_type: str = 'application/octet-stream'
    
    
class JpegResponse(Response):
    media_type: str = 'image/jpeg'
    

class PngResponse(Response):
    media_type: str = 'image/png'
    
    
class IcoResponse(Response):
    media_type: str = 'image/vnd.microsoft.icon'
    
    
class SvgResponse(Response):
    media_type: str = 'image/svg+xml'
    
    
class GifResponse(Response):
    media_type: str = 'image/gif'
    
    
class RedirectResponse(Response):
    
    def __init__(self, 
        location: str,
        status_code: int | HttpStatus = 302,
        dict_headers: Optional[dict[str, str]] = None,
    ):
        if dict_headers is None:
            dict_headers = {}
        dict_headers['Location'] = location
        super().__init__(
            status_code=status_code,
            body='',
            dict_headers=dict_headers,
        )
    
