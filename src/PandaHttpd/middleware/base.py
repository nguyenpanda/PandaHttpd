from ..http import Request, Response
from ..utils import MappingStr


class BaseMiddleware:
    
    def __init__(self, *args, **kwargs) -> None:
        pass
    
    async def pre(self, dict_headers: MappingStr, request: Request) -> MappingStr:
        return dict_headers
    
    async def post(self, dict_headers: MappingStr, response: Response) -> Response:
        return response
	
    def __repr__(self) -> str:
        return f'<BaseMiddleware {self.__class__.__name__}>'
    
    def __str__(self) -> str:
        return f'{self.__class__.__name__}()'


class DefaultMiddleware(BaseMiddleware):
    
    async def pre(self, dict_headers: MappingStr, request: Request) -> MappingStr:
        dict_headers['method'] = request.method
        dict_headers['path'] = request.path
        dict_headers['protocol'] = request._protocol
        return dict_headers

    async def post(self, dict_headers: MappingStr, response: Response) -> Response:
        response.update_header('X-Processed-By', 'DefaultMiddleware')
        return response
    