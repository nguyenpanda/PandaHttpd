from .http import Response, PlainTextResponse
from ._typing import HeaderHandler
from .utils import CaseInsensitiveDict

import os
from pathlib import Path
from typing import Callable, MutableMapping


class FileHandler:
    
    def __init__(self, default_handler: HeaderHandler | None = None):
        self._handler: HeaderHandler = default_handler \
            if default_handler is not None \
			else self.default_handler

        assert callable(self._handler), 'Default handler must be a callable'
    
    @staticmethod
    def read_file(path: os.PathLike, *args, **kwargs) -> bytes | None:
        with Path(path).open('rb') as f:
            return f.read()
        
    @property
    def handler(self) -> HeaderHandler:
        return self._handler
        
    @handler.setter
    def handler(self, handler: HeaderHandler) -> None:
        assert callable(handler), 'Default handler must be a callable'
        self._handler = handler
        
    def default_handler(self, dict_headers: MutableMapping[str, str] | None, *args, **kwargs) -> Response:
        return PlainTextResponse(
            status_code=404,
            body=b'404 Not Found',
        )
    

class StaticFiles:
        
    def __init__(self, directory: str | os.PathLike):
        self._directory: Path = Path(directory).resolve()
        assert self._directory.is_dir(), f'Directory `{self._directory}` does not exist'
    
    @property
    def directory(self) -> Path:
        return self._directory
    
    @property
    def prefix(self) -> Path:
        return self._directory
        