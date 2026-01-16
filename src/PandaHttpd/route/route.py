from ..filehandler import FileHandler
from ..http import JsonResponse, Response
from .._typing import UserFunc, HasPrefix
from ..utils import MappingStr

import asyncio
import inspect
import mimetypes
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Optional, Type
from pathlib import Path


class BaseRoute:
    
    def __init__(self,
        path: str,
        method: str,
        endpoint: UserFunc,
        response_class: Type[Response] = JsonResponse,
    ) -> None:
        self.path: str = path
        self.method: str = method.upper()
        self.endpoint: UserFunc = endpoint
        self._response_class: Type[Response] = response_class
        
        assert path.startswith('/'), 'Route path must start with "/"'
        assert callable(self.endpoint) or self.endpoint is None, 'Endpoint must be a callable or None'
        assert issubclass(response_class, Response), 'Response class must be a subclass of Response'
		
    async def handle(self, 
        dict_headers: Optional[MappingStr],
        executor: Optional[ThreadPoolExecutor] = None,
        *args, **kwargs,
    ) -> Response:
        """Async route handler with support for both sync and async endpoints"""
        if inspect.iscoroutinefunction(self.endpoint):
            body = await self.endpoint(*args, **kwargs)
        else:
            if executor:
                loop = asyncio.get_event_loop()
                body = await loop.run_in_executor(executor, self.endpoint, *args, **kwargs)
            else:
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
    
    def __init__(self,
        path: str,
        handler: HasPrefix,
        file_handler: FileHandler = FileHandler(),
    ) -> None:
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
        
    async def handle(self,
    	dict_headers: Optional[MappingStr],
        executor: Optional[ThreadPoolExecutor] = None,
        *args, **kwargs,
    ) -> Response:
        """
        url = `http://<ip>:<port>/<mount_path>/path/to/file.png`
		request_path = `/<mount_path>/path/to/file.png`
		self.path = `/<mount_path>`
		self.handler.prefix = `<physical_path_to_mount>`  # e.g. `/var/www/static`
		file_path = `<physical_path_to_mount>/path/to/file.png`
        """
        
        if dict_headers is None or 'path' not in dict_headers:
            raise ValueError("dict_headers must contain 'path' key")
            
        request_path: Path = Path(dict_headers['path'])
        # TODO: FIX HARD CODED PATH JOINING
        file_path = Path(self.handler.prefix) / request_path.relative_to(self.path)
        if not (file_path.exists() and file_path.is_file()):
            response: Response | Awaitable[Response] = self.file_handler.handler(dict_headers, executor, *args, **kwargs)
            if hasattr(response, '__await__'):
                return await response # type: ignore
            return response  # type: ignore
        
        # Read file async using executor
        body: bytes | None = await self.endpoint(file_path, executor, *args, **kwargs)
        media_type, _ = mimetypes.guess_type(file_path)
        
        res_ins: Response = self.response_class(
            status_code=200,
			body=body,
			media_type=media_type or 'application/octet-stream',
			dict_headers=dict_headers,
		)
        return res_ins
    
    def __str__(self) -> str:
        class_name = self.__class__.__name__
        return f'{class_name}(path={self.path}, prefix={self.handler.prefix})'
    