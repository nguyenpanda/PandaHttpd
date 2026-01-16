from .filehandler import FileHandler
from .http import JsonResponse, Response, Request
from .middleware import Middleware, BaseMiddleware, DefaultMiddleware
from .route import Router, BaseRoute
from .utils import CaseInsensitiveDict, PandaLogger, lgreen, lred
from ._typing import Socket, GenericHandler, HeaderHandler, UserFunc, HasPrefix
from .worker import WorkerPool

import asyncio
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
    ) -> None:
        assert prefix.startswith('/'), 'Prefix must start with "/"'
        assert not prefix.endswith('/') or prefix == '/', 'Prefix must not end with "/" unless it is root "/"'
        
        self._prefix: str = prefix
        self._config: Dict[str, Any] = config
        self._ip: str = str(config.get('ip', '0.0.0.0'))
        self._port: int = int(config.get('port', 80))
        
        num_workers: int = int(config.get('num_workers', psutil.cpu_count(False) or 4))
        executor_per_worker: int = int(config.get('executor_per_worker', 10))
        
        self.worker_pool: WorkerPool = WorkerPool(
            num_workers=num_workers,
            handle_client_func=self._handle_client_wrapper,
            executor_size_per_worker=executor_per_worker,
        )
        
        self.router: Router = Router(routes=routes, default_handler=default_handler)
        self.middle_ware: Middleware = Middleware(
            middlewares=[DefaultMiddleware()] + list(middleware) if middleware else [DefaultMiddleware()]
        )
        
        self.logger = logger.setup() \
            if isinstance(logger, PandaLogger) \
            else PandaLogger().setup()
        self.logger.debug(f'PandaHttpd Initialized with IP: {self.ip}, Port: {self.port}')
        self.logger.info(f'WorkerPool initialized with {num_workers} workers, {executor_per_worker} executors per worker')

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
    
    def middleware(self) -> None:
        pass
    
    def set_default_handler(self, handler: GenericHandler) -> None:
        self.router.set_default_handler(handler)
        handler_name = getattr(handler, '__qualname__', handler.__class__.__name__)
        self.logger.info(f'Default_handler set to `{lred(handler_name)}`')

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
    
    async def _handle_client_wrapper(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        executor: ThreadPoolExecutor,
    ) -> None:
        """
        Wrapper for handle_client that accepts executor from worker.
        This runs in the worker's event loop.
        """
        await self.handle_client(reader, writer, executor)
    
    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        executor: ThreadPoolExecutor,
    ) -> None:
        """Async client handler using StreamReader and StreamWriter"""
        client_address = writer.get_extra_info('peername')
        
        try:
            # Handle Request with async streams
            request = Request(reader=reader, writer=writer)
            await request.handle()
            
            real_ip: str = request.headers.get('cf-connecting-ip', client_address[0] if client_address else 'unknown')
            self.logger.info(f'[Requested] IP=`{real_ip}` | Method=`{request.method}` | Path=`{request.path}`')
            
            # Pre-Middleware
            dict_headers = await self.middle_ware.pre(CaseInsensitiveDict(), request)
            
            # Find Route
            route: Optional[BaseRoute] = self.router.find_route(request.path, request.method)
            response: Response
            if not route:
                self.logger.error(f'[Response] 404 Not Found: No route for {request.method} {request.path}, using default handler.')
                # Use default handler
                response = await self.router.not_found_handler(dict_headers, executor=executor)
            else:
                # Generate Response using route handler
                response = await route.handle(
                    dict_headers=dict_headers,
                    executor=executor,
                )
            
            # Post-Middleware
            response = await self.middle_ware.post(dict_headers, response)
            
            # Send Response async
            await response.send(writer)
            
            self.logger.debug(f'Success handling client {client_address}')
            
        except Exception as e:
            tb_list = traceback.extract_tb(e.__traceback__)
            filename, line, func, text = tb_list[-1]
            self.logger.error(f'Error handling client {client_address} in {filename}:{line} \n\t {text} -> {e}')
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            
    def _run(self) -> None:
        """Main server loop - accepts connections and distributes to workers"""
        self.logger.info(f'Server running at {lgreen(f"http://{self.ip}:{self.port}")}')
        
        self.worker_pool.start()
        self.logger.info(f'Worker pool started with {self.worker_pool.num_workers} workers')
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.ip, self.port))
        server_socket.listen(self.config.get('listen', 1000))
        
        server_socket.settimeout(1.0)
        
        try:
            self.logger.info('Accepting connections...')
            while True:
                try:
                    client_socket, client_address = server_socket.accept()
                    
                    timeout = self.config.get('connection_timeout', 30)
                    client_socket.settimeout(timeout)
                    
                    if not self.worker_pool.distribute_connection(client_socket):
                        self.logger.warning(f'All workers busy, rejecting connection from {client_address}')
                        client_socket.close()
                        
                except socket.timeout:
                    continue
                    
        except KeyboardInterrupt:
            self.logger.warning('Stopping server by user request...')
        finally:
            self.logger.info('Shutting down worker pool...')
            self.worker_pool.shutdown(wait=True)
            server_socket.close()
            self.logger.info('Server shutdown complete')
            
    def run(self) -> None:
        """Entry point to run the server"""
        self._run()
