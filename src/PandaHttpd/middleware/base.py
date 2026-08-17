from ..http import Request, Response
from ..utils import MappingStr


class BaseMiddleware:
    
    def __init__(self, *args, **kwargs):
        pass
    
    def pre(self, dict_headers: MappingStr, request: Request) -> MappingStr:
        return dict_headers
    
    def post(self, dict_headers: MappingStr, response: Response) -> Response:
        return response
	
    def __repr__(self) -> str:
        return f'<BaseMiddleware {self.__class__.__name__}>'
    
    def __str__(self) -> str:
        return f'{self.__class__.__name__}()'


class DefaultMiddleware(BaseMiddleware):

    #: Request headers a static file needs in order to answer correctly: which
    #: bytes were asked for, and whether the copy the client holds is current.
    #: Nothing else in dict_headers carries them, and a route is handed
    #: dict_headers rather than the Request itself.
    FORWARDED_REQUEST_HEADERS = ('range', 'if-none-match', 'if-modified-since')

    def pre(self, dict_headers: MappingStr, request: Request) -> MappingStr:
        dict_headers['method'] = request.method
        dict_headers['path'] = request.path
        dict_headers['protocol'] = request._protocol
        for name in self.FORWARDED_REQUEST_HEADERS:
            value = request.headers.get(name)
            if value:
                dict_headers[name] = value
        return dict_headers

    def post(self, dict_headers: MappingStr, response: Response) -> Response:
        response.update_header('X-Processed-By', 'DefaultMiddleware')
        return response
    