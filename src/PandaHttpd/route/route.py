from ..filehandler import FileHandler
from ..http import FileResponse, HttpStatus, JsonResponse, Response
from .._typing import UserFunc, HasPrefix
from ..utils import MappingStr

import mimetypes
from typing import Optional, Type
from pathlib import Path


mimetypes.add_type("application/x-yaml", ".yaml")
mimetypes.add_type("application/x-yaml", ".yml")


# TODO: MUST SUPPORT MIDDLEWARE
class BaseRoute:
    
    def __init__(self,
        path: str,
        method: str,
        endpoint: UserFunc,
        response_class: Type[Response] = JsonResponse,
    ):
        self.path: str = path
        self.method: str = method.upper()
        self.endpoint: UserFunc = endpoint
        self._response_class: Type[Response] = response_class
        
        assert path.startswith('/'), 'Route path must start with "/"'
        assert callable(self.endpoint) or self.endpoint is None, 'Endpoint must be a callable or None'
        assert issubclass(response_class, Response), 'Response class must be a subclass of Response'
		
    def handle(self, 
        dict_headers: Optional[MappingStr],
        *args, **kwargs,
    ) -> Response:
        body = self.endpoint(*args, **kwargs)
        if isinstance(body, Response):
            return body
        
        res_ins: Response = self.response_class(
            body=body, 
            dict_headers=dict_headers, 
        )
        return res_ins
    
    @property
    def response_class(self) -> Type[Response]:
        return self._response_class
    
    @response_class.setter
    def response_class(self, response_class: Type[Response]) -> None:
        assert issubclass(response_class, Response), 'Response class must be a subclass of Response'
        self._response_class = response_class

    def match(self, path: str, method: str) -> bool:
        return self.path == path and self.method == method.upper()
    
    def __str__(self) -> str:
        class_name = self.__class__.__name__
        return f'{class_name}(path={self.path}, method={self.method}, response_class={self.response_class.__name__})'


class Route(BaseRoute):
    pass


class Mount(BaseRoute):

    # Above this, a file is streamed rather than read into memory. Chosen so
    # the site's own CSS and JS stay on the in-memory path -- they are the
    # assets worth compressing, and the compression middleware needs a body to
    # work on.
    STREAM_THRESHOLD: int = 256 * 1024

    def __init__(self,
        path: str,
        handler: HasPrefix,
        file_handler: FileHandler = FileHandler(),
    ):
        self.file_handler: FileHandler = file_handler
        self.handler = handler
        super().__init__(
            path=path,
            method='GET',
            endpoint=file_handler.read_file,
            response_class=Response,
        )
        
    def match(self, path: str, method: str) -> bool:
        return path.startswith(self.path) and method.upper() == 'GET'
        
    def handle(self,
    	dict_headers: MappingStr,
        *args, **kwargs,
    ) -> Response:
        """
        url = `http://<ip>:<port>/<mount_path>/path/to/file.png`
		request_path = `/<mount_path>/path/to/file.png`
		self.path = `/<mount_path>`
		self.handler.prefix = `<physical_path_to_mount>`  # e.g. `/var/www/static`
		file_path = `<physical_path_to_mount>/path/to/file.png`
        """
        
        request_path: Path = Path(dict_headers['path'])
        mount_root = Path(self.handler.prefix).resolve()
        file_path = (Path(self.handler.prefix) / request_path.relative_to(self.path)).resolve()
        if (
            not file_path.is_relative_to(mount_root)
            or not file_path.exists()
            or not file_path.is_file()
        ):
            response: Response = self.file_handler.handler(dict_headers, *args, **kwargs)
            return response
        
        media_type, _ = mimetypes.guess_type(file_path)
        media_type = media_type or 'application/octet-stream'

        # A range request, or a file big enough that holding it in memory
        # matters, is streamed from disk. Everything else keeps the in-memory
        # path, because that is what the compression middleware can act on --
        # and the small text assets are exactly the ones worth compressing.
        wants_range = bool(dict_headers.get('range'))
        if wants_range or file_path.stat().st_size >= self.STREAM_THRESHOLD:
            return FileResponse(
                file_path,
                media_type=media_type,
                request_headers=dict_headers,
            )

        conditional = FileResponse(
            file_path, media_type=media_type, request_headers=dict_headers
        )
        if conditional.status_code == HttpStatus.NOT_MODIFIED:
            # The client already holds this. Answering with the file again is
            # the single most wasteful thing a static server can do.
            return conditional

        body: bytes | None = self.endpoint(file_path, *args, **kwargs)
        # dict_headers is deliberately not passed through: it holds routing
        # details and the client's own request headers, and echoing those back
        # put `path`, `method` and `protocol` on every static response.
        res_ins: Response = self.response_class(
            status_code=200,
			body=body,
			media_type=media_type,
			dict_headers={
                'ETag': conditional.etag,
                'Last-Modified': conditional.last_modified,
                'Accept-Ranges': 'bytes',
            },
		)
        return res_ins
    
    def __str__(self) -> str:
        class_name = self.__class__.__name__
        return f'{class_name}(path={self.path}, prefix={self.handler.prefix})'
    