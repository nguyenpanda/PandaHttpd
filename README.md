# PandaHttpd🐼🌐

**A High-Performance, Zero-Dependency Python Web Framework Built Entirely from Scratch.**

[![Project Status: Production-Ready](https://img.shields.io/badge/Status-Production--Ready-success.svg)](#)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Framework: From Scratch](https://img.shields.io/badge/Framework-Zero--Dependency-orange.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)

PandaHttpd is a minimalist yet powerful web framework for Python, engineered for developers who value performance, transparency, and low-level control. Inspired by the developer experience of FastAPI, it is built **entirely from scratch** using only Python's standard `socket` library for the HTTP server implementation—meaning no Uvicorn, no Gunicorn, and no third-party dependencies for its core engine.

> [!IMPORTANT]
> PandaHttpd is currently powering [nguyenpanda.com](https://nguyenpanda.com) in a production environment.

---

## 🚀 Key Highlights

- **"From Scratch" Philosophy:** Every byte of the HTTP lifecycle—from raw TCP socket acceptance to header parsing and response transmission—is handled by internal logic.
- **Asynchronous Architecture:** Leverages `asyncio` (available in the `asynchronous` branch) with a sophisticated `WorkerPool` model for high-concurrency, non-blocking I/O.
- **FastAPI-like DX:** Familiar decorator-based routing, type-hinted parameters, and clean application structure.
- **Zero-Dependency Core:** Requires only the Python standard library, ensuring a minimal footprint and maximum portability.
- **Production Proven:** Successfully handles real-world traffic on [nguyenpanda.com](https://nguyenpanda.com).

---

## 🏗 System Architecture

PandaHttpd implements a multi-layered architecture designed for speed and modularity. The system follows a **Master-Worker** pattern to scale across multiple CPU cores while maintaining asynchronous efficiency within each worker.

### Request Flow

1. **Master Listener:** A single thread manages the main TCP socket, accepting connections via raw `socket`.
2. **Worker Distribution:** Connections are distributed using a round-robin strategy to a pool of `AsyncWorker` threads.
3. **Event Loop Processing:** Each worker runs its own `asyncio` event loop, handling multiple concurrent connections using non-blocking stream readers/writers.
4. **Middleware Pipeline:** Requests pass through a bi-directional middleware stack (e.g., GZip compression, request logging).
5. **Router Dispatch:** The internal matching engine resolves the URL path to a specific endpoint.
6. **Response Generation:** Structured responses are serialized and transmitted directly back through the asynchronous stream.

### File Organization

```text
src/PandaHttpd/
├── app.py              # Application Orchestrator & Master Server
├── worker.py           # Multi-threaded WorkerPool & AsyncWorker logic
├── http/               # HTTP/1.1 Protocol Layer (Request/Response)
├── route/              # Path matching & Routing engine
├── middleware/         # Pre/Post processing hooks
└── utils/              # Data structures (CaseInsensitiveDict, CookieDict)
```

---

## 🛠 Installation & Setup

PandaHttpd uses [uv](https://github.com/astral-sh/uv) for modern, lightning-fast dependency management.

### 1. Clone the Repository

```bash
git clone https://github.com/nguyenpanda/PandaHttpd.git
cd PandaHttpd
```

### 2. Set Up Environment

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

---

## 💻 Usage Demo

Creating a production-ready server is straightforward:

```python
from PandaHttpd import PandaHttpd
from PandaHttpd.http import JsonResponse, PlainTextResponse

# Server Configuration
config = {
    "ip": "127.0.0.1",
    "port": 8080,
    "num_workers": 4,           # Number of worker threads
    "executor_per_worker": 10   # ThreadPool size per worker for blocking tasks
}

app = PandaHttpd(config=config)

@app.route("/", method="GET")
def home():
    return {"message": "Welcome to PandaHttpd!", "status": "online"}

@app.route("/hello", response_class=PlainTextResponse)
def hello():
    return "Hello, World!"

if __name__ == "__main__":
    app.run()
```

### Live Implementation

Check out the full production source code for my personal website using PandaHttpd:
👉 **[nguyenpanda.com Demo Repository](https://github.com/nguyenpanda/nguyenpanda.com)**

---

## 📊 Technical Deep Dive

### Raw Socket Handling

Unlike traditional frameworks that hide the networking layer, PandaHttpd exposes the power of the `socket` library. It manages its own socket options (`SO_REUSEADDR`), handles keep-alive connections, and implements manual byte-level parsing for the HTTP/1.1 protocol.

### Async Transition

In the `asynchronous` branch, we transitioned from a purely threaded model to a hybrid `WorkerPool` architecture. This allows us to handle thousands of concurrent connections by utilizing `asyncio.open_connection` while still being able to offload CPU-intensive tasks to dedicated thread executors within each worker.

### Visual Architecture

Detailed UML diagrams and class hierarchies can be generated using the provided documentation script:

```bash
bash docs/uml.sh
```

The generated PDFs in `docs/uml/` provide a comprehensive view of the class associations and internal dependency mapping.

---

## 📬 Contact & Author

Developed with ❤️ by **Hà Tường Nguyên**.

- **Website:** [nguyenpanda.com](https://nguyenpanda.com)
- **Email:** [hatuongnguyen@0107gmail.com](mailto:hatuongnguyen@0107gmail.com)
- **GitHub:** [@nguyenpanda](https://github.com/nguyenpanda)

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
