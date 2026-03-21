# PandaHttpd: Extended Documentation

This document provides a deep dive into the internal mechanics of the PandaHttpd framework, detailing the architecture, request lifecycle, and extension points.

---

## 🏗 Architectural Overview

PandaHttpd is built on a "Shared-Nothing" architecture where each request is handled in an isolated context within a `ThreadPoolExecutor`. This ensures that slow I/O or processing on one connection doesn't block the acceptance of new connections.

### Core Modules

1. **`PandaHttpd.app`**: The entry point. It initializes the socket, binds to the network interface, and orchestrates the hand-off between the listener and the workers.
2. **`PandaHttpd.http.request`**: Responsible for stream-based parsing. It uses a buffered approach to read HTTP headers (`\r\n\r\n` delimiter) before selectively reading the body based on `Content-Length`.
3. **`PandaHttpd.http.response`**: A class-based hierarchy for generating HTTP responses. It handles automatic header generation for `Content-Type` and `Content-Length`.
4. **`PandaHttpd.route.router`**: A trie-like matching system (planned enhancement) currently using sequential matching for robust route resolution.
5. **`PandaHttpd.middleware`**: A recursive wrapper system that allows developers to hook into the request before routing and the response after generation.

---

## 🔄 The Request Lifecycle

Understanding the flow of a single request through the system:

### 1. Socket Acceptance

The main loop in `app.run()` blocks on `server_socket.accept()`. Once a connection is received, the socket is wrapped and submitted to the `ThreadPoolExecutor`.

### 2. Request Parsing

The `Request` object performs the following:

- Reads from the socket until the double CRLF sequence is found.
- Parses the status line (Method, Path, Protocol).
- Populates a `CaseInsensitiveDict` with headers.
- Parses cookies and query parameters.
- If `Content-Length` is present, it reads the remaining bytes for the body.

### 3. Middleware Pipeline (Pre)

The `Middleware.pre()` sequence is triggered. Each middleware can modify the header dictionary or the request metadata.

### 4. Routing

The `Router` iterates through registered `Route` and `Mount` objects.

- **Route**: Matches exact paths and methods.
- **Mount**: Matches path prefixes (used for static files).

### 5. Execution

The endpoint (user-defined function) is called. PandaHttpd supports returning:

- `dict`: Automatically converted to `JsonResponse`.
- `str`: Automatically converted to `Response` (PlainText).
- `Response` object: Used directly.

### 6. Middleware Pipeline (Post)

The `Middleware.post()` sequence is triggered in reverse order. This is where `GZipMiddleware` compresses the body if the `Accept-Encoding` header allows.

### 7. Transmission & Shutdown

The final byte stream is sent via `socket.sendall()`. The server then calls `socket.shutdown(SHUT_WR)` to signal completion to the client before closing the connection.

---

## 🛠 Extension Points

### Custom Middleware

To create a middleware, inherit from `BaseMiddleware`:

```python
from PandaHttpd.middleware import BaseMiddleware

class CustomHeaderMiddleware(BaseMiddleware):
    def post(self, dict_headers, response):
        response.update_header("X-Powered-By", "Panda")
        return response
```

### Custom Response Types

You can create specialized responses by inheriting from the `Response` class and defining a `media_type`:

```python
from PandaHttpd.http import Response

class XMLResponse(Response):
    media_type = "application/xml"
    
    def render(self, content):
        # Convert dict/object to XML string
        return f"<root>{content}</root>".encode(self.charset)
```

---

## 📊 UML Generation

The project includes a shell script to visualize the class hierarchy:

```bash
bash docs/uml.sh
```

This script uses `pyreverse` to generate PDF diagrams in the `docs/uml/` directory. These diagrams are essential for understanding the relationship between `BaseRoute`, `Mount`, and `Router`.

---

## ⚖️ Performance Considerations

- **Threading**: The `max_workers` configuration is crucial. For CPU-bound tasks, match it to the number of cores. For I/O-bound tasks, it can be significantly higher.
- **Buffer Size**: The internal `recv` buffer is set to 4096 bytes. This is optimized for standard MTU sizes but can be adjusted in `http/request.py`.
- **Zero-Copy**: Future versions aim to implement `sendfile()` for `StaticFiles` to reduce user-space context switching.
