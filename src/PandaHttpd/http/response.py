from .status import HttpStatus
from .._typing import Socket
from ..utils import MappingStr, CaseInsensitiveDict, CookieDict

import asyncio
import json
from typing_extensions import Any, Dict, List, Optional, Self


class Response:
    media_type: str
    charset: str = 'utf-8'
    
    def __init__(self, 
		status_code: int | HttpStatus = 200, 
  		body: Any = None,
    	media_type: Optional[str] = None,
		dict_headers: Optional[MappingStr] = None,
    ) -> None:
        if isinstance(status_code, HttpStatus):
            self.status_code: HttpStatus = status_code
        else:
            self.status_code = HttpStatus(status_code)  # type: ignore[call-arg]
            
        if media_type is not None:
            self.media_type: str = media_type
            
        self.body: bytes = self.render(body)
        self.list_headers: List[tuple[bytes, bytes]] = self.init_header(dict_headers)
        self._header: Dict[bytes, bytes] = {}
    
    def render(self, content: Any) -> bytes:
        if content is None:
            return b''
        elif isinstance(content, bytes):
            return content
        else:
            return content.encode(self.charset)
    
    def init_header(self, dict_header: Optional[MappingStr] = None) -> List[tuple[bytes, bytes]]:
        list_headers: List[tuple[bytes, bytes]]
        if dict_header is None:
            list_headers = []
            already_have_content_type = False
            already_have_content_length = False
        else:
            list_headers = [
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
            list_headers.append((b'content-length', content_length.encode(self.charset)))
            
        if (self.media_type is not None
            and already_have_content_type is False
        ):
            if self.media_type.startswith('text/') and 'charset=' not in self.media_type.lower():
                self.media_type += '; charset=' + self.charset
            list_headers.append((b'content-type', self.media_type.encode(self.charset)))
        return list_headers
    
    @property
    def header(self) -> Dict[bytes, bytes]:
        if not self._header:
            for k, v in self.list_headers:
                self._header[k] = v
            
        return self._header
    
    @property
    def status_line(self) -> bytes:
        return f'HTTP/1.1 {self.status_code.value} {self.status_code.phrase}\r\n'.encode(self.charset)
    
    def update_header(self, key: str, value: str) -> None:
        k = key.lower().encode(self.charset)
        v = value.encode(self.charset)
        self.list_headers.append((k, v))
        self._header[k] = v
    
    def set_cookies(self,
        key: str,
        value: str,
        expires: Optional[str] = None,
        max_age: Optional[int] = None,
    ) -> None:
        raise NotImplementedError()
    
    def delete_cookies(self,
        key: str,
        value: str = '',
        expires: Optional[str] = None,
        max_age: Optional[int] = None,
    ) -> None:
        raise NotImplementedError()
    
    async def send(self, writer: asyncio.StreamWriter) -> None:
        """Async response sender using StreamWriter"""
        header_block = b''
        for k, v in self.list_headers:
            header_block += k + b': ' + v + b'\r\n'
        header_block += b'\r\n'
        
        writer.write(self.status_line + header_block)
        
        if self.body:
            writer.write(self.body)
        
        await writer.drain()
    
    def __call__(self, 
        sender: Socket, 
        receiver: Optional[Socket], 
    ) -> None:
        """Legacy sync response sender (for backward compatibility)"""
        header_block = b''
        for k, v in self.list_headers:
            header_block += k + b': ' + v + b'\r\n'
        header_block += b'\r\n'
        
        sender.sendall(self.status_line + header_block)
        
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
    media_type: str = 'text/plain'
    
    def __init__(self, 
        body: Dict[str, Any] | None = None,
        url: str | None = None,
        status_code: int | HttpStatus = 301, 
        dict_headers: CaseInsensitiveDict | None = None
    ) -> None:
        body_params = {}
        if body is not None:
            body_params = {str(k).lower(): v for k, v in body.items()}
            
        target_url = url if url is not None else body_params.get('location')
        if not target_url:
            raise ValueError("RedirectResponse requires a 'url' argument or a 'location' key in the body.")
        
        if dict_headers is None:
            dict_headers = CaseInsensitiveDict()
        dict_headers['Location'] = target_url
        
        super().__init__(
            status_code=body_params.get('status_code', status_code),
            body=b'', 
            dict_headers=dict_headers
        )
