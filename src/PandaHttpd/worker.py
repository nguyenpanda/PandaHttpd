"""
AsyncWorker - Worker thread that runs its own async event loop
Each worker handles multiple connections concurrently using asyncio
"""

import asyncio
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable, Any
import socket


class AsyncWorker(threading.Thread):
    """
    Worker thread that runs its own async event loop.
    Handles client connections concurrently within a single thread.
    """
    
    def __init__(
        self,
        worker_id: int,
        handle_client_func: Callable,
        executor_size: int = 2,
        max_queue_size: int = 1000,
    ):
        super().__init__(daemon=True, name=f'AsyncWorker-{worker_id}')
        self.worker_id: int = worker_id
        self.handle_client_func: Callable = handle_client_func
        self.executor_size: int = executor_size
        
        self.queue: Queue = Queue(maxsize=max_queue_size)
        
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.executor: Optional[ThreadPoolExecutor] = None
        
        self.running: bool = False
        self.shutdown_event: threading.Event = threading.Event()
        
    def run(self) -> None:
        """Thread main - creates and runs event loop"""
        self.running = True
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.executor = ThreadPoolExecutor(
            max_workers=self.executor_size,
            thread_name_prefix=f'Worker{self.worker_id}-Executor'
        )
        
        try:
            self.loop.run_until_complete(self._async_main())
        except Exception as e:
            print(f"Worker {self.worker_id} error: {e}")
        finally:
            if self.executor:
                self.executor.shutdown(wait=True)
            self.loop.close()
            self.running = False
            
    async def _async_main(self) -> None:
        """Async main loop - processes connections from queue"""
        active_tasks = set()
        
        while not self.shutdown_event.is_set():
            try:
                try:
                    client_socket = self.queue.get(timeout=0.1)
                    
                    task = asyncio.create_task(
                        self._handle_connection(client_socket)
                    )
                    active_tasks.add(task)
                    task.add_done_callback(active_tasks.discard)
                    
                except Empty:
                    pass
                
                await asyncio.sleep(0)
                
            except asyncio.CancelledError:
                break
        
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)
            
    async def _handle_connection(self, client_socket: socket.socket) -> None:
        """Handle a single client connection with async I/O"""
        try:
            reader, writer = await asyncio.open_connection(sock=client_socket)
            await self.handle_client_func(reader, writer, self.executor)
            
        except Exception as e:
            print(f"Worker {self.worker_id} connection error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def submit_connection(self, client_socket: socket.socket) -> bool:
        """
        Submit a connection to this worker's queue.
        Returns True if accepted, False if queue is full.
        """
        try:
            self.queue.put_nowait(client_socket)
            return True
        except:
            return False
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
    
    def shutdown(self) -> None:
        """Signal worker to shutdown gracefully"""
        self.shutdown_event.set()


class WorkerPool:
    """
    Pool of AsyncWorker threads.
    Distributes incoming connections across workers.
    """
    
    def __init__(
        self,
        num_workers: int,
        handle_client_func: Callable,
        executor_size_per_worker: int = 2,
    ):
        self.num_workers: int = num_workers
        self.workers: list[AsyncWorker] = []
        self.current_worker_index: int = 0
        
        # Create workers
        for i in range(num_workers):
            worker = AsyncWorker(
                worker_id=i,
                handle_client_func=handle_client_func,
                executor_size=executor_size_per_worker,
            )
            self.workers.append(worker)
    
    def start(self) -> None:
        """Start all worker threads"""
        for worker in self.workers:
            worker.start()
    
    def distribute_connection(self, client_socket: socket.socket) -> bool:
        """
        Distribute connection to a worker using round-robin.
        Returns True if accepted, False if all workers are busy.
        """
        for attempt in range(self.num_workers):
            worker_idx = (self.current_worker_index + attempt) % self.num_workers
            worker = self.workers[worker_idx]
            
            if worker.submit_connection(client_socket):
                self.current_worker_index = (worker_idx + 1) % self.num_workers
                return True
        
        return False
    
    def get_stats(self) -> dict:
        """Get worker pool statistics"""
        return {
            'num_workers': self.num_workers,
            'workers': [
                {
                    'id': w.worker_id,
                    'running': w.running,
                    'queue_size': w.get_queue_size(),
                }
                for w in self.workers
            ]
        }
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown all workers"""
        for worker in self.workers:
            worker.shutdown()
        
        if wait:
            for worker in self.workers:
                worker.join(timeout=5.0)
