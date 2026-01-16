from .http import Response, PlainTextResponse
from ._typing import HeaderHandler
from .utils import CaseInsensitiveDict

import asyncio
import os
from pathlib import Path
from typing import Callable, MutableMapping, Optional
from concurrent.futures import ThreadPoolExecutor


class FileHandler:
    
    def __init__(self, default_handler: HeaderHandler | None = None, default_file: os.PathLike | None = None) -> None:
        self._handler: HeaderHandler = default_handler \
            if default_handler is not None \
			else self.default_handler
        self._default_file: Optional[Path] = Path(default_file) if default_file is not None else None

        assert callable(self._handler), 'Default handler must be a callable'
        if self._default_file is not None:
            assert self._default_file.is_file(), f'Default file `{self._default_file}` does not exist or is not a file'
    
    @staticmethod
    async def read_file(
        path: os.PathLike,
        executor: Optional[ThreadPoolExecutor] = None,
        *args, **kwargs
    ) -> bytes | None:
        """Async file reader using ThreadPoolExecutor"""
        def _sync_read():
            with Path(path).open('rb') as f:
                return f.read()
        
        if executor:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(executor, _sync_read)
        else:
            # Fallback to asyncio.to_thread
            return await asyncio.to_thread(_sync_read)
        
    async def serve_file(
        self,
        file_path: os.PathLike,
        executor: Optional[ThreadPoolExecutor] = None,
        response_class: type[Response] | None = None,
    ) -> Response:
        """Serve a file asynchronously with proper MIME type detection"""
        import mimetypes
        from .http import HtmlResponse, JsonResponse
        
        path: Path = Path(file_path)
        if not path.is_file():
            if self._default_file is not None and self._default_file.is_file():
                path = self._default_file
            else:
                return PlainTextResponse(status_code=404, body=b'404 Not Found')
        
        file_content: bytes | None = await self.read_file(path, executor)
        if file_content is None:
            return PlainTextResponse(status_code=500, body=b'500 Internal Server Error')
        
        if response_class is not None:
            return response_class(status_code=200, body=file_content)
        
        media_type: Optional[str]
        media_type, _ = mimetypes.guess_type(path)
        
        return Response(
            status_code=200,
            body=file_content,
            media_type=media_type or 'application/octet-stream',
        )
    
    @property
    def handler(self) -> HeaderHandler:
        return self._handler
        
    @handler.setter
    def handler(self, handler: HeaderHandler) -> None:
        assert callable(handler), 'Default handler must be a callable'
        self._handler = handler
        
    async def default_handler(
        self,
        dict_headers: MutableMapping[str, str] | None,
        executor: Optional[ThreadPoolExecutor] = None,
        *args, **kwargs
    ) -> Response:
        if self._default_file is not None:
            return await self.serve_file(self._default_file, executor)
        return PlainTextResponse(
            status_code=404,
            body=b'404 Not Found',
        )
    

class StaticFiles:
        
    def __init__(self, directory: str | os.PathLike) -> None:
        self._directory: Path = Path(directory).resolve()
        assert self._directory.is_dir(), f'Directory `{self._directory}` does not exist'
    
    @property
    def directory(self) -> Path:
        return self._directory
    
    @property
    def prefix(self) -> Path:
        return self._directory
        