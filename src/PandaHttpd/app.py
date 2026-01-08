from .http import HttpStatus, JsonResponse, Response
from .router import Router, Route
from ._typing import Socket, ResponseFunc
from .utils.logger import PandaLogger

import socket
import threading

from typing import Type, Tuple, Callable, Optional, Sequence, Any
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
        self.server_ip: str = str(server_ip)
        self.server_port: int = int(server_port)
        self.router: Router = Router(routes=routes, default_handler=default_handler)
        
        self.logger = logger.setup() \
            if isinstance(logger, PandaLogger) \
            else PandaLogger()
        self.logger.info(f'HookAPI Initialized with IP: {self.server_ip}, Port: {self.server_port}')

    def route(self, 
        path: str, method: str = 'GET',
        response_class: Type[Response] = JsonResponse,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.router.add_route(
                path=path, 
                method=method, 
                endpoint=func,
                response_class=response_class,
            )
            self.logger.info(f'[Registered]: [{method.upper():^6}] `{blue(func.__name__)}` -> `{green(path)}`')
            return func
        
        return decorator
        
    def _recive_all(self, connection: Socket) -> bytes:
        data = []
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            data.append(chunk)
            if b'\r\n\r\n' in chunk:
                break
        return b''.join(data)

    def handle_client(self, client_connection: Socket, client_address: Tuple[str, int]) -> None:
        try:
            raw_data = self._recive_all(client_connection)
            if not raw_data:
                return

            try:
                request_string = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                request_string = raw_data.decode('iso-8859-1')

            lines = request_string.split("\r\n")
            if not lines or not lines[0]:
                return

            first_line_parts = lines[0].split()
            if len(first_line_parts) < 2:
                return
            
            method: str = first_line_parts[0].upper()
            path: str = first_line_parts[1]

            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()

            real_ip: str = headers.get('cf-connecting-ip', client_address[0])
            self.logger.info(f"[Requested] IP=`{real_ip}` | Method=`{method}` | Path=`{path}`")
            
            route: Optional[Route] = self.router.find_route(path, method)
            response: Response = route.handle(headers, *[], **{}) \
                if route \
                else self.router.default_handler(headers, *[], **{})
            response(client_connection, None)
            
            try:
                client_connection.shutdown(socket.SHUT_WR)
            except OSError:
                pass
        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_connection.close()

    def run(self) -> None:
        self.logger.warning(f'Server running at http://{self.server_ip}:{self.server_port}')

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.server_ip, self.server_port))
        server_socket.listen(10000)

        try:
            while True:
                client_connection: socket.socket
                client_address: Tuple[str, int]
                client_connection, client_address = server_socket.accept()
                
                t = threading.Thread(
                    target=self.handle_client, 
                    args=(client_connection, client_address)
                )
                t.start()
        except KeyboardInterrupt:
            self.logger.warning("Stopping server by user request...")
        finally:
            server_socket.close()
            
    def set_default_handler(self, handler: ResponseFunc) -> None:
        self.router.set_default_handler(handler)
        self.logger.info(f'Default handler set to `{handler.__name__}`')
        