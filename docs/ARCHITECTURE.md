# PandaHttpd: Architectural Design

This document details the internal design and request-handling lifecycle of the PandaHttpd framework. PandaHttpd is engineered to bridge the gap between low-level socket programming and high-level web framework ergonomics.

---

## 🏗 System Overview

PandaHttpd operates as a multi-layered system where raw bytes from a TCP stream are progressively transformed into structured Python objects, processed through a middleware pipeline, and dispatched to user-defined endpoints.

### Core Architectural Pillars

1. **Raw Socket Layer:** Direct interaction with the `socket` module for connection acceptance and byte transmission.
2. **Asynchronous Dispatch:** A high-concurrency model that utilizes a `ThreadPoolExecutor` to handle multiple simultaneous connections without blocking the main listener loop.
3. **Protocol Layer:** A custom implementation of the HTTP/1.1 protocol, including stream-based parsing and stateful response generation.
4. **Routing Engine:** A decorator-based system for mapping HTTP methods and URL paths to executable Python functions.

---

## 🔄 Request Lifecycle

The following steps outline the flow of a single HTTP request from the wire to the application and back:

### 1. Connection Acceptance (`app.py`)

The server initializes a `socket.AF_INET` stream socket, binds it to the configured IP/Port, and enters a `listen` state. The `run()` loop blocks on `accept()`. When a client connects:

- A new `client_connection` (socket) is created.
- The connection is submitted to a `ThreadPoolExecutor`.

### 2. Stream Parsing (`http/request.py`)

Within the worker thread, the `handle_client()` method initializes a `Request` object.

- **Header Extraction:** The server reads from the socket until the `\r\n\r\n` delimiter is found.
- **State Initialization:** Method (GET/POST), Path, and Headers are parsed into a `CaseInsensitiveDict`.
- **Body Retrieval:** If a `Content-Length` header is present, the server reads the specified number of bytes from the remaining stream.

### 3. Middleware Pipeline (Pre-processing)

The `Middleware` manager executes the `pre()` hook for all registered middlewares. This is where request metadata (like authentication tokens or custom tracking IDs) can be injected or validated.

### 4. Routing & Dispatch (`route/router.py`)

The `Router` searches for a matching `Route` or `Mount` based on the requested path and HTTP method.

- **Route:** Performs an exact match.
- **Mount:** Performs a prefix match (primarily used for `StaticFiles`).
If no match is found, the `default_handler` (typically a 404 handler) is selected.

### 5. Execution & Response Generation

The selected endpoint is executed. If it returns a standard Python `dict` or `str`, PandaHttpd automatically wraps it in the appropriate `Response` class (`JsonResponse` or `PlainTextResponse`).

### 6. Middleware Pipeline (Post-processing)

The `Middleware` manager executes the `post()` hooks in reverse order. A primary example is the `GZipMiddleware`, which checks the `Accept-Encoding` header and compresses the response body if applicable.

### 7. Byte Transmission

The `Response` object is called as a function (via `__call__`), which:

- Constructs the HTTP status line.
- Formats and flushes the header block.
- Sends the raw body bytes over the socket using `sendall()`.

---

## 📊 Class Relationships (UML)

The internal class associations and hierarchy are mapped out using `pyreverse`. You can generate the latest visual diagrams by running the following command from the project root:

```bash
bash docs/uml.sh
```

### Reference Diagrams

The following diagrams are generated in the `docs/uml/` directory:

- **`classes_PandaHttpd.pdf`**: Detailed class attributes and method signatures.
- **`packages_PandaHttpd.pdf`**: High-level package dependencies and module interactions.

---

## 🛡 Concurrency Model

PandaHttpd leverages a "Parallel Worker" strategy. While the main thread manages the `AF_INET` listener, the `ThreadPoolExecutor` ensures that I/O-bound operations (like reading large request bodies or serving files from disk) do not stall the server. This design is optimized for the non-blocking intent of modern asynchronous applications while maintaining the stability of raw socket state management.

---

## 🧩 Key Components

| Component | Logic Source | Description |
| :--- | :--- | :--- |
| **PandaHttpd** | `app.py` | The main application class and server entry point. |
| **Request** | `http/request.py` | Handles raw byte-to-object conversion. |
| **Router** | `route/router.py` | Logic for dispatching requests to endpoints. |
| **Response** | `http/response.py` | Handles object-to-byte conversion and HTTP compliance. |
| **StaticFiles** | `filehandler.py` | Optimized logic for mounting physical directories to URL paths. |
