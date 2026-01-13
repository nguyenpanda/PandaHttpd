from .base import BaseMiddleware
from ..http import Request, Response
from ..utils import MappingStr

from typing import List, Sequence


class Middleware:
    
    def __init__(self, middlewares: Sequence[BaseMiddleware] | None = None) -> None:
        self.middlewares: List[BaseMiddleware] = list(middlewares) if middlewares else []
        
    def add_middleware(self, middleware: BaseMiddleware) -> None:
        assert isinstance(middleware, BaseMiddleware), 'Middleware must be an instance of BaseMiddleware'
        self.middlewares.append(middleware)
        
    def pre(self, dict_headers: MappingStr, request: Request) -> MappingStr:
        for middleware in self.middlewares:
            dict_headers = middleware.pre(dict_headers, request)
        return dict_headers
        
    def post(self, dict_headers: MappingStr, response: Response) -> Response:
        for middleware in reversed(self.middlewares):
            response = middleware.post(dict_headers, response)
        return response
        
    def __repr__(self) -> str:
        return f'<Middleware {len(self.middlewares)} middlewares>'
    
    def __str__(self) -> str:
        return f'Middleware(middlewares={self.middlewares})'
    