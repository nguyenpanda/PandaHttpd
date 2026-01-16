from .route import BaseRoute, Route, Mount
from ..filehandler import FileHandler
from ..http import JsonResponse, Response, PlainTextResponse
from ..utils import MappingStr
from .._typing import GenericHandler, HeaderHandler, UserFunc, HasPrefix

from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Type, List, Sequence
    

class Router:
    
    def __init__(self,
        routes: Optional[Sequence[BaseRoute]] = None,
        default_handler: Optional[GenericHandler | HeaderHandler] = None,
    ) -> None:
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
    
    def set_default_handler(self, handler: Optional[GenericHandler | HeaderHandler]) -> HeaderHandler:
        if handler is None:
            return self.not_found_handler
            
        assert callable(handler), 'Default handler must be a callable'
        
        from typing import Union, Awaitable, cast
        
        async def wrapper(dict_headers: MappingStr | None, executor: Optional[ThreadPoolExecutor] = None, *args, **kwargs) -> Response:
            result: Union[Response, Awaitable[Response]] = handler(*args, **kwargs)
            
            if hasattr(result, '__await__'):
                awaitable_result: Awaitable[Response] = cast(Awaitable[Response], result)
                return await awaitable_result
            return cast(Response, result)
        
        typed_wrapper: HeaderHandler = cast(HeaderHandler, wrapper)
        self.default_handler = typed_wrapper
        return typed_wrapper

    async def not_found_handler(
        self,
        dict_headers,
        executor: Optional[ThreadPoolExecutor] = None,
        *args, **kwargs
    ) -> Response:
        return PlainTextResponse(
            status_code=404,
            body=b'404 Not Found'
        )
        
    def __str__(self) -> str:
        route_list = '\n\t\t'.join([str(route) for route in self.routes])
        return f'Router(\n\troutes=[{route_list}], \n\tdefault_handler={self.default_handler.__class__.__name__})'
    