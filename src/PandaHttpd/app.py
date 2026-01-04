import socket
import threading
from typing import Dict, Tuple, Callable, Optional
from pathlib import Path
from nguyenpanda.swan import green, blue

from .utils.logger import PandaLogger
from .typing import HandlerFunc

class PandaHttpd:
    
    def __init__(self, 
        server_ip: str = '0.0.0.0', 
        server_port: int = 80,
        logger: Optional[PandaLogger] = None,
    ) -> None:
        
        self.server_ip: str = str(server_ip)
        self.server_port: int = int(server_port)
        
        self.logger = logger.setup() \
            if isinstance(logger, PandaLogger) \
            else PandaLogger()
        
        self.routes: Dict[Tuple[str, str], HandlerFunc] = {}
        self.logger.info(f'HookAPI Initialized with IP: {self.server_ip}, Port: {self.server_port}')

    def route(self, path: str, method: str = 'GET') -> Callable[[HandlerFunc], HandlerFunc]:
        def decorator(func: HandlerFunc) -> HandlerFunc:
            self.routes[(path, method.upper())] = func
            self.logger.info(f'[Registered]: [{method.upper():^6}] `{blue(func.__name__)}` -> `{green(path)}`')
            return func
        return decorator

    def handle_client(self, client_connection: socket.socket, client_address: Tuple[str, int]) -> None:
        try:
            raw_data = b''
            while True:
                chunk = client_connection.recv(4096)
                if not chunk:
                    break
                raw_data += chunk
                if b'\r\n\r\n' in raw_data:
                    break
            
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
            
            handler: Optional[HandlerFunc] = self.routes.get((path, method))
            
            response: bytes
            if handler:
                response = handler()
            # elif method == 'GET':
            #     static_response = self.serve_file_logic(path) 
            #     if static_response:
            #         response = static_response
            #     else:
            #         response = self.not_found()
            else:
                response = self.not_found()

            client_connection.sendall(response)
            
            try:
                client_connection.shutdown(socket.SHUT_WR)
            except OSError:
                pass
        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_connection.close()
          
    def not_found(self) -> bytes:
        img_path = Path(__file__).parent.parent / 'src' / 'assets' / 'errors' / '404.html'
        
        if img_path.exists():
            with open(img_path, 'r', encoding='utf-8') as f:
                body = f.read()
        else:
            body = "<h1>404 Not Found</h1>"

        header = "HTTP/1.1 404 Not Found\r\n"
        header += "Content-Type: text/html; charset=utf-8\r\n"
        header += f"Content-Length: {len(body.encode('utf-8'))}\r\n"
        header += "Connection: close\r\n\r\n"
        return (header + body).encode()

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
            