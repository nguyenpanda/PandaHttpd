from .http.response import JsonResponse, Response, PlainTextResponse
from ._typing import ResponseFunc, UserFunc

from typing import Any, Callable, Dict, List, Optional, Sequence, Type


class Route:
    
    def __init__(self,
        path: str,
        method: str,
        endpoint: UserFunc,
        response_class: Type[Response] = JsonResponse,
    ):
        self.path: str = path
        self.method: str = method.upper()
        self.endpoint: UserFunc = endpoint
        self.response_class: Type[Response] = response_class
        
        assert path.startswith('/'), 'Route path must start with "/"'
        assert callable(self.endpoint) or self.endpoint is None, 'Endpoint must be a callable or None'
        assert issubclass(self.response_class, Response) or self.response_class is None, 'Response class must be a subclass of Response or None'
    
    def handle(self, 
        dict_headers: Optional[Dict[str, str]],
        *args, **kwargs,
    ) -> Response:
        body = self.endpoint(*args, **kwargs)
        res_ins: Response = self.response_class(
            body=body, 
            dict_headers=dict_headers
        )
        return res_ins

    def match(self, path: str, method: str) -> bool:
        return self.path == path and self.method == method.upper()


class Router:
    
    def __init__(self,
        routes: Optional[Sequence[Route]] = None,
        default_handler: Optional[ResponseFunc] = None,
    ):
        self.routes: List[Route] = [] if routes is None else list(routes)
        self.default_handler: ResponseFunc = \
            self.set_default_handler(default_handler) \
            if default_handler is not None \
            else self.not_found_handler
    
    def add_route(self, 
        path: str, 
        method: str, 
        endpoint: UserFunc,
        response_class: Type[Response] = JsonResponse,
    ) -> None:
        self.routes.append(Route(
            path=path, 
            method=method, 
            endpoint=endpoint,
            response_class=response_class,
        ))

    def find_route(self, path: str, method: str) -> Optional[Route]:
        for route in self.routes:
            if route.match(path, method):
                return route
        return None
    
    def set_default_handler(self, handler: ResponseFunc) -> ResponseFunc:
        assert callable(handler), 'Default handler must be a callable'
        assert issubclass(handler.__annotations__.get('return', Response), Response), 'Default handler must return a Response instance'
        
        def wrapper(headers, *args, **kwargs) -> Response:
            return handler(*args, **kwargs)
        
        self.default_handler = wrapper
        return wrapper

    def not_found_handler(self, headers, *args, **kwargs) -> Response:
        return PlainTextResponse(
            status_code=404,
            body=b'404 Not Found'
        )
        