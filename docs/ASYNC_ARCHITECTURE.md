# PandaHttpd: Asynchronous Architecture 🐼⚡

This branch contains the high-performance, `asyncio`-driven implementation of the PandaHttpd framework. It utilizes a sophisticated **Master-Worker** pattern to handle thousands of concurrent connections using non-blocking I/O.

---

## 🏗 System Overview (Asynchronous)

Unlike the standard threaded model, this implementation leverages the power of Python's `asyncio` event loop within dedicated worker threads. This allows for massive concurrency within each worker while still taking advantage of multi-core processing.

### Key Components

1. **`WorkerPool`**: Manages a set of `AsyncWorker` threads. It uses a round-robin distribution strategy to balance incoming connections from the main listener.
2. **`AsyncWorker`**: Each worker runs its own `asyncio` event loop. It maintains an internal queue of connections and processes them concurrently using `asyncio.create_task`.
3. **Async Request Lifecycle**: The entire protocol layer (`Request` and `Response`) has been converted to use `async/await` and non-blocking `StreamReader`/`StreamWriter`.

---

## 🔄 The Async Request Flow

1. **Master Accept**: The main thread accepts a raw socket connection.
2. **Distribution**: The `WorkerPool` pushes the `client_socket` into a specific worker's thread-safe queue.
3. **Event Loop Pick-up**: The `AsyncWorker` event loop detects the new socket, wraps it in an async stream, and initiates the handler.
4. **Non-Blocking Parsing**: `await Request.handle()` reads bytes as they arrive without blocking other tasks.
5. **Route Dispatch**: The router resolves the endpoint, executing it within the same event loop.
6. **Async Transmission**: The response is streamed back through the `StreamWriter`, and the connection is closed gracefully.

---

## 🛠 Usage (Asynchronous Branch)

The API remains consistent with the FastAPI-like experience, but the engine is powered by the `WorkerPool`.

```python
from PandaHttpd import PandaHttpd

config = {
    "ip": "127.0.0.1",
    "port": 8080,
    "num_workers": 4,           # Number of AsyncWorker threads
    "executor_per_worker": 10   # ThreadPool size per worker for blocking I/O tasks
}

app = PandaHttpd(config=config)

@app.route("/", method="GET")
def home():
    return {"status": "async_online"}

if __name__ == "__main__":
    app.run()
```

---

## ⚖️ Concurrency Comparison

| Feature | Threaded (Master) | Asynchronous (Branch) |
| :--- | :--- | :--- |
| **I/O Model** | Blocking with ThreadPool | Non-blocking (asyncio) |
| **Concurrency** | One thread per request | Thousands of requests per worker |
| **Resource Usage** | High (Thread overhead) | Very Low (Task overhead) |
| **Recommended for** | Simple deployments | High-traffic production |

---

## 📬 Contact

Developed by **Ha Tuong Nguyen**.
[nguyenpanda.com](https://nguyenpanda.com)
