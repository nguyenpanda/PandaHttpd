from .route import BaseRoute, Route, Mount
from ..filehandler import FileHandler
from ..http import JsonResponse, Response, PlainTextResponse
from ..utils import MappingStr
from .._typing import GenericHandler, HeaderHandler, UserFunc, HasPrefix

from typing import Optional, Type, List, Sequence
    

class Router:
    
    def __init__(self,
        routes: Optional[Sequence[BaseRoute]] = None,
        default_handler: Optional[HeaderHandler] = None,
    ):
        self.routes: List[BaseRoute] = [] if routes is None else list(routes)
        self.default_handler: HeaderHandler = \
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
        
    def add_mount(self,
        path: str,
        handler: HasPrefix,
        file_handler: FileHandler | None = None,
    ) -> None:
        if file_handler is None:
            file_handler = FileHandler(default_handler=self.default_handler)
            
        self.routes.append(Mount(
            path=path,
            handler=handler,
            file_handler=file_handler,
        ))

    def find_route(self, path: str, method: str) -> Optional[BaseRoute]:
        for route in self.routes:
            if route.match(path, method):
                return route
        return None
    
    def set_default_handler(self, handler: GenericHandler) -> HeaderHandler:
        assert callable(handler), 'Default handler must be a callable'
        assert issubclass(handler.__annotations__.get('return', Response), Response), 'Default handler must return a Response instance'
        
        def wrapper(dict_headers: MappingStr | None, *args, **kwargs) -> Response:
            return handler(*args, **kwargs)
        
        self.default_handler = wrapper
        return wrapper

    def not_found_handler(self, dict_headers, *args, **kwargs) -> Response:
        return PlainTextResponse(
            status_code=404,
            body=b'404 Not Found'
        )
        
    def __str__(self) -> str:
        route_list = '\n\t\t'.join([str(route) for route in self.routes])
        return f'Router(\n\troutes=[{route_list}], \n\tdefault_handler={self.default_handler.__class__.__name__})'
    