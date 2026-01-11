from .http import JsonResponse, Response, Request
from .router import Router, Route
from ._typing import Socket, ResponseFunc, UserFunc
from .utils import PandaLogger, lgreen, lred

import socket
import threading

from typing import Any, Callable, Type, Tuple, Optional, Sequence
from pathlib import Path
from nguyenpanda.swan import green, blue


class PandaHttpd:
    
    def __init__(self, 
        server_ip: str = '0.0.0.0', 
        server_port: int = 80,
        routes: Optional[Sequence[Route]] = None,
        default_handler: Optional[ResponseFunc] = None,
        logger: Optional[PandaLogger] = None,
    ):
        self._ip: str = str(server_ip)
        self._port: int = int(server_port)
        self.router: Router = Router(routes=routes, default_handler=default_handler)
        
        self.logger = logger.setup() \
            if isinstance(logger, PandaLogger) \
            else PandaLogger()
        self.logger.debug(f'PandaHttpd Initialized with IP: {self.ip}, Port: {self.port}')

    def route(self, 
        path: str, method: str = 'GET',
        response_class: Type[Response] = JsonResponse,
    ) -> Callable[[UserFunc], UserFunc]:
        
        def decorator(func: UserFunc) -> UserFunc:
            self.router.add_route(
                path=path, 
                method=method, 
                endpoint=func,
                response_class=response_class,
            )
            self.logger.debug(f'[Registered]: [{method.upper():^6}] `{blue(func.__name__)}` -> `{green(path)}`')
            return func
        
        return decorator
    
    def set_default_handler(self, handler: ResponseFunc) -> None:
        self.router.set_default_handler(handler)
        self.logger.info(f'Default_handler set to `{lred(handler.__name__)}`')

    @property
    def ip(self) -> str:
        return self._ip
    
    @property
    def port(self) -> int:
        return self._port
    
    def handle_client(self, client_connection: Socket, client_address: Tuple[str, int]) -> None:
        try:
            request = Request(client_connection)
            request.handle()
            
            real_ip: str = request.headers.get('cf-connecting-ip', client_address[0])
            self.logger.info(f'[Requested] IP=`{real_ip}` | Method=`{request.method}` | Path=`{request.path}`')

            route: Optional[Route] = self.router.find_route(request.path, request.method)
            if not route:
                self.logger.error(f'[Response] 404 Not Found: No route for {request.method} {request.path}, using default handler.')
                response_func = self.router.default_handler
            else:
                response_func = route.handle
            
            # TODO: MUST USE `request.headers` to custom the header passed in response
            args, kwargs = [], {}
            response: Response = response_func(dict_headers={}, *args, **kwargs)
            response(client_connection, None)
            
            try:
                client_connection.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            self.logger.info(f'Success handling client {client_address}')
        except Exception as e:
            self.logger.error(f'Error handling client {client_address}: {e}')
        finally:
            client_connection.close()
            
    def run(self) -> None:
        self.logger.info(f'Server running at {lgreen(f'http://{self.ip}:{self.port}')}')

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.ip, self.port))
        server_socket.listen(10000)

        try:
            while True:
                client_connection: Socket
                client_address: Tuple[str, int]
                client_connection, client_address = server_socket.accept()
                
                t = threading.Thread(
                    target=self.handle_client, 
                    args=(client_connection, client_address)
                )
                t.start()
        except KeyboardInterrupt:
            self.logger.warning('Stopping server by user request...')
        finally:
            server_socket.close()
