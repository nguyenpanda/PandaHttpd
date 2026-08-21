from .status import HttpStatus
from .._typing import Socket
from ..utils import MappingStr, CaseInsensitiveDict, CookieDict

import json
import os
import re
from email.utils import formatdate, parsedate_to_datetime
from pathlib import Path
from typing_extensions import Any, Dict, List, Optional, Self, Tuple


class Response:
    media_type: str
    charset: str = 'utf-8'

    # Set by the app for a HEAD request, so the headers are built exactly as
    # they would be for GET and only the transfer is skipped. Off by default:
    # nothing that does not set it behaves any differently.
    suppress_body: bool = False
    
    def __init__(self, 
		status_code: int | HttpStatus = 200, 
  		body: Any = None,
    	media_type: Optional[str] = None,
		dict_headers: Optional[MappingStr] = None,
    ):
        self.status_code: HttpStatus = (status_code if isinstance(status_code, HttpStatus) else HttpStatus(status_code))
        if media_type is not None:
            self.media_type: str = media_type
        self.body: bytes = self.render(body)
        self._list_headers: List[tuple[bytes, bytes]] = self.init_header(dict_headers)
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

        self.declare_connection_close(list_headers)
        return list_headers

    @classmethod
    def declare_connection_close(cls, list_headers: List[tuple[bytes, bytes]]) -> None:
        """Tell the client this connection is finished after one response.

        This server handles exactly one request per connection -- handle_client
        shuts the socket down and closes it in a finally block, always. HTTP/1.1
        defaults the other way: a connection is persistent unless a response
        says `Connection: close`. Closing silently therefore tells a client the
        socket is reusable when it is not, and a pooling client (requests,
        urllib3, any browser) caches it and hands it to the next request.

        Measured before this existed: one request left ten connections in
        urllib3's pool, every one already closed by this server. Reusing one
        raises RemoteDisconnected. Idempotent methods are quietly retried, so
        GETs mostly survive and POST and PATCH do not -- which is why it looked
        like flakiness that only ever appeared on a loaded CI runner, never on
        a developer's loopback.

        Announcing the close is the whole fix. Implementing real keep-alive
        would be the other answer, and a much larger change: it needs per-
        connection request framing, read timeouts and a socket budget, none of
        which exist here.
        """
        if not any(k == b'connection' for k, _ in list_headers):
            list_headers.append((b'connection', b'close'))
    
    @property
    def header(self) -> Dict[bytes, bytes]:
        if not self._header:
            for k, v in self._list_headers:
                self._header[k] = v
            
        return self._header
    
    @property
    def status_line(self) -> bytes:
        return f'HTTP/1.1 {self.status_code.value} {self.status_code.phrase}\r\n'.encode(self.charset)
    
    def update_header(self, key: str, value: str) -> None:
        k = key.lower().encode(self.charset)
        v = value.encode(self.charset)
        self._list_headers.append((k, v))
        self._header[k] = v
    
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
    
    def __call__(self, 
        sender: Socket, 
        receiver: Optional[Socket], 
    ) -> None:
        header_block = bytearray()
        for k, v in self.header.items():
            header_block += k + b': ' + v + b'\r\n'
        header_block += b'\r\n'
        
        sender.sendall(self.status_line + header_block)

        if self.suppress_body:
            return

        if self.body:
            sender.sendall(self.body)
            

_RANGE_HEADER = re.compile(r'^\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)\s*(?:,.*)?$', re.IGNORECASE)


class FileResponse(Response):
    """Serves a file from disk without reading it into memory.

    Every other response type renders its whole body up front and hands it to
    one sendall(). For a page that is right; for a download it means the file
    is resident in RAM for as long as it takes to send, once per worker thread
    doing so. This reads and writes in chunks instead, so the memory a
    download costs is bounded by the chunk size rather than by the file.

    It also answers the two things a browser asks about a file it has seen
    before, or wants only part of:

      Range   -- without it, seeking in a video is not possible: the player has
                 no way to ask for the middle, so every scrub refetches from
                 byte zero.
      ETag /
      Last-Modified -- so an unchanged file costs a 304 and no body at all.

    Additive by design: nothing that does not construct one of these behaves
    any differently.
    """

    media_type: str = 'application/octet-stream'
    chunk_size: int = 64 * 1024

    def __init__(self,
        path: str | os.PathLike,
        media_type: Optional[str] = None,
        dict_headers: Optional[MappingStr] = None,
        request_headers: Optional[MappingStr] = None,
        status_code: int | HttpStatus = 200,
    ):
        self.path: Path = Path(path)
        stat = self.path.stat()  # Raises for a missing file, which is the caller's to handle.
        self.file_size: int = stat.st_size
        self.last_modified: str = formatdate(stat.st_mtime, usegmt=True)
        # Size and mtime together change whenever the bytes do, and cost a
        # stat() rather than a read of the whole file to compute.
        self.etag: str = f'"{stat.st_size:x}-{int(stat.st_mtime):x}"'

        asked = self._normalise(request_headers)
        headers: Dict[str, str] = dict(dict_headers or {})
        headers.setdefault('Accept-Ranges', 'bytes')
        headers['ETag'] = self.etag
        headers['Last-Modified'] = self.last_modified

        self._start = 0
        self._length = self.file_size

        if self._is_unchanged(asked):
            # 304 carries no body, and must not carry a Content-Length for one.
            self._length = 0
            super().__init__(HttpStatus.NOT_MODIFIED, b'', media_type, headers)
            return

        wanted = self._parse_range(asked.get('range'))
        if wanted is None:
            headers['Content-Length'] = str(self.file_size)
            super().__init__(status_code, b'', media_type, headers)
            return

        start, end = wanted
        if start >= self.file_size:
            # The client asked for bytes past the end. Saying so, with the real
            # size, is what lets it ask again correctly.
            self._length = 0
            headers['Content-Range'] = f'bytes */{self.file_size}'
            super().__init__(HttpStatus.RANGE_NOT_SATISFIABLE, b'', media_type, headers)
            return

        end = min(end, self.file_size - 1)
        self._start = start
        self._length = end - start + 1
        headers['Content-Range'] = f'bytes {start}-{end}/{self.file_size}'
        headers['Content-Length'] = str(self._length)
        super().__init__(HttpStatus.PARTIAL_CONTENT, b'', media_type, headers)

    @staticmethod
    def _normalise(request_headers: Optional[MappingStr]) -> Dict[str, str]:
        if not request_headers:
            return {}
        return {str(k).lower(): v for k, v in request_headers.items()}

    def _is_unchanged(self, asked: Dict[str, str]) -> bool:
        """Whether the copy the client already holds is still current.

        If-None-Match wins outright when present, as the specification
        requires: an entity tag is exact where a timestamp is only to the
        second.
        """
        if 'if-none-match' in asked:
            offered = [tag.strip() for tag in str(asked['if-none-match']).split(',')]
            return '*' in offered or self.etag in offered

        since = asked.get('if-modified-since')
        if not since:
            return False
        try:
            return parsedate_to_datetime(since) >= parsedate_to_datetime(self.last_modified)
        except (TypeError, ValueError):
            # An unparseable date is no evidence that anything is unchanged.
            return False

    def _parse_range(self, header: Optional[str]) -> Optional[Tuple[int, int]]:
        """The first byte range asked for, or None if there is not a usable one.

        A malformed or unsupported header is deliberately not an error: the
        specification says to ignore it and serve the whole thing, which is
        also the behaviour that keeps an odd client working rather than broken.
        """
        if not header:
            return None
        match = _RANGE_HEADER.match(str(header))
        if not match:
            return None

        first, last = match.group(1), match.group(2)
        if not first and not last:
            return None

        if not first:
            # `bytes=-500` means the final 500 bytes, not "from 500 onwards".
            length = int(last)
            if length <= 0:
                return None
            return max(0, self.file_size - length), self.file_size - 1

        start = int(first)
        if not last:
            # Open-ended. A start past the end is still a range -- an
            # unsatisfiable one, which the caller answers with 416 and the real
            # size, rather than quietly sending the whole file instead.
            return start, self.file_size - 1

        end = int(last)
        if end < start:
            return None
        return start, end

    def init_header(self, dict_header: Optional[MappingStr] = None) -> List[tuple[bytes, bytes]]:
        """Headers exactly as given, plus a content type.

        The inherited version derives Content-Length from the body, which here
        is empty on purpose -- the length of what will be sent is worked out in
        __init__ and passed in with the rest.
        """
        list_headers = [
            (str(k).lower().encode(self.charset), str(v).encode(self.charset))
            for k, v in (dict_header or {}).items()
        ]
        if self.media_type is not None and not any(k == b'content-type' for k, _ in list_headers):
            media_type = self.media_type
            if media_type.startswith('text/') and 'charset=' not in media_type.lower():
                media_type += '; charset=' + self.charset
            list_headers.append((b'content-type', media_type.encode(self.charset)))

        self.declare_connection_close(list_headers)
        return list_headers

    def __call__(self,
        sender: Socket,
        receiver: Optional[Socket],
    ) -> None:
        header_block = bytearray()
        for k, v in self.header.items():
            header_block += k + b': ' + v + b'\r\n'
        header_block += b'\r\n'

        sender.sendall(self.status_line + header_block)

        if self.suppress_body:
            return

        if self._length <= 0:
            return

        with self.path.open('rb') as handle:
            if self._start:
                handle.seek(self._start)
            remaining = self._length
            while remaining > 0:
                chunk = handle.read(min(self.chunk_size, remaining))
                if not chunk:
                    # The file shrank under us. Stopping short is the only
                    # honest option; the declared length is already sent.
                    break
                sender.sendall(chunk)
                remaining -= len(chunk)


class PlainTextResponse(Response):
    media_type: str = 'text/plain'
    
        
class HtmlResponse(Response):
    media_type: str = 'text/html'
    

class XmlResponse(Response):
    media_type: str = 'application/xml'
    

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
    ):
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
