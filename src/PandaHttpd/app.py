from .filehandler import FileHandler
from .http import JsonResponse, Response, Request
from .middleware import Middleware, BaseMiddleware, DefaultMiddleware
from .route import Router, BaseRoute
from .utils import CaseInsensitiveDict, PandaLogger, lgreen, lred
from ._typing import Socket, GenericHandler, HeaderHandler, UserFunc, HasPrefix

import psutil
import socket
import traceback
from concurrent.futures import ThreadPoolExecutor

from typing import Any, Callable, Dict, Type, Tuple, Optional, Sequence
from nguyenpanda.swan import green, blue


class PandaHttpd:
    
    def __init__(self, 
        config: Dict[str, Any],
        prefix: str = '/',
        routes: Optional[Sequence[BaseRoute]] = None,
        middleware: Optional[Sequence[BaseMiddleware]] = None,
        default_handler: Optional[GenericHandler] = None,
        logger: Optional[PandaLogger] = None,
    ):
        assert prefix.startswith('/'), 'Prefix must start with "/"'
        assert not prefix.endswith('/') or prefix == '/', 'Prefix must not end with "/" unless it is root "/"'
        
        self._prefix: str = prefix
        self._config: Dict[str, Any] = config
        self._ip: str = str(config.get('ip', '0.0.0.0'))
        self._port: int = int(config.get('port', 80))
        
        self.router: Router = Router(routes=routes, default_handler=default_handler)
        self.middle_ware: Middleware = Middleware(
            middlewares=[DefaultMiddleware()] + list(middleware) if middleware else [DefaultMiddleware()]
        )
        
        self.logger = logger.setup() \
            if isinstance(logger, PandaLogger) \
            else PandaLogger()
        self.logger.debug(f'PandaHttpd Initialized with IP: {self.ip}, Port: {self.port}')

    def route(self, 
        path: str, method: str = 'GET',
        response_class: Type[Response] = JsonResponse,
    ) -> Callable[[UserFunc], UserFunc]:
        
        path = self.prefix + path if self.prefix != '/' else path
        def decorator(endpoint: UserFunc) -> UserFunc:
            self.router.add_route(
                path=path, 
                method=method, 
                endpoint=endpoint,
                response_class=response_class,
            )
            self.logger.debug(f'[Registered]: [{method.upper():^6}] `{blue(endpoint.__name__)}` -> `{green(path)}`')
            return endpoint
        return decorator
    
    def mount(self, 
        path: str, 
        handler: HasPrefix, 
        file_handler: FileHandler | None = None,
    ) -> None:
        
        path = self.prefix + path if self.prefix != '/' else path
        self.router.add_mount(
            path=path,
            handler=handler,
            file_handler=file_handler,
        )
        self.logger.debug(f'[Mounted]: `{blue(path)}` -> `{green(handler.prefix)}`')
    
    def middleware(self):
        pass
    
    def set_default_handler(self, handler: GenericHandler) -> None:
        self.router.set_default_handler(handler)
        self.logger.info(f'Default_handler set to `{lred(handler.__qualname__)}`')

    @property
    def ip(self) -> str:
        return self._ip
    
    @property
    def port(self) -> int:
        return self._port
    
    @property
    def config(self) -> Dict[str, Any]:
        return self._config
    
    @property
    def prefix(self) -> str:
        return self._prefix
    
    def handle_client(self, client_connection: Socket, client_address: Tuple[str, int]) -> None:
        try:
            # Handle Request
            request = Request(client_connection)
            request.handle()
            
            real_ip: str = request.headers.get('cf-connecting-ip', client_address[0])
            self.logger.info(f'[Requested] IP=`{real_ip}` | Method=`{request.method}` | Path=`{request.path}`')
            
            # TODO: Pre-Middleware (This part is not implemented yet)
            dict_headers = self.middle_ware.pre(CaseInsensitiveDict(), request)
            
            # Find Route
            route: Optional[BaseRoute] = self.router.find_route(request.path, request.method)
            if not route:
                self.logger.error(f'[Response] 404 Not Found: No route for {request.method} {request.path}, using default handler.')
                response_func: HeaderHandler = self.router.default_handler
            else:
                response_func: HeaderHandler = route.handle
            
            # Generate Response
            # TODO: MUST USE `request.headers` to custom the header passed in response
            args, kwargs = [], {}
            response: Response = response_func(dict_headers=dict_headers, *args, **kwargs)
            
            # TODO: Post-Middleware (This part is not implemented yet)
            response: Response = self.middle_ware.post(dict_headers, response)
            
            # Send Response
            response(client_connection, None)
            
            try:
                client_connection.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            self.logger.debug(f'Success handling client {client_address}')
        except Exception as e:
            tb_list = traceback.extract_tb(e.__traceback__)
            filename, line, func, text = tb_list[-1]
            self.logger.error(f'Error handling client {client_address} in {filename}:{line} \n\t {text} -> {e}')
        finally:
            client_connection.close()
            
    def run(self) -> None:
        self.logger.info(f'Server running at {lgreen(f'http://{self.ip}:{self.port}')}')

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.ip, self.port))
        server_socket.listen(self.config.get('listen', 1000))
        
        try:
            mw: int = int(self.config.get('max_workers', psutil.cpu_count(False)))
            self.logger.info(f'Using `ThreadPoolExecutor` with max_workers={mw}')
            with ThreadPoolExecutor(max_workers=mw) as pool:
                while True:
                    client_connection: Socket
                    client_address: Tuple[str, int]
                    client_connection, client_address = server_socket.accept()
                    
                    pool.submit(self.handle_client, client_connection, client_address)
        except KeyboardInterrupt:
            self.logger.warning('Stopping server by user request...')
        finally:
            server_socket.close()
