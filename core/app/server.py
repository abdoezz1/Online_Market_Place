"""
server.py -- Custom Threaded TCP Socket Server
===============================================
Member 1 (Server Lead)

Entry point for the marketplace application.
Replaces Django's manage.py runserver + Gunicorn.

Usage:
    python -m core.app.server
    python -m core.app.server --host 0.0.0.0 --port 8000 --workers 50
"""

import socket
import threading
import signal
import sys
import os
import time
import argparse
import traceback

# ---------------------------------------------------------------------------
#  Import Member 2's modules (http_parser + response_builder)
# ---------------------------------------------------------------------------

from core.http.http_parser import parse_request
from core.http.response_builder import build_response, error_response

# ---------------------------------------------------------------------------
#  Import Member 3's router
# ---------------------------------------------------------------------------

from core.app.router import route


# ===========================================================================
#  CONFIGURATION
# ===========================================================================

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_MAX_WORKERS = 50          # max simultaneous threads
RECV_BUFFER_SIZE = 8192           # initial recv() chunk size
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB hard cap (prevents DoS)
SOCKET_TIMEOUT = 30               # seconds before dropping idle connection


# ===========================================================================
#  CLIENT HANDLER  (runs in its own thread)
# ===========================================================================

class ClientHandler:
    """
    Handles a single client TCP connection in a dedicated thread.

    Lifecycle:
        1. Receive raw bytes from the socket
        2. Pass to Member 2's parse_request() -> structured dict
        3. Pass dict to Member 3's route() -> response bytes
        4. Send response bytes back through the socket
        5. Close the connection
    """

    def __init__(self, client_socket, client_address):
        self.client_socket = client_socket
        self.client_address = client_address

    def handle(self):
        """Main entry point -- called by the thread."""
        try:
            self.client_socket.settimeout(SOCKET_TIMEOUT)

            # ---- Step 1: Receive raw HTTP bytes ----
            raw_data = self._receive_full_request()
            if not raw_data:
                self._close()
                return

            # ---- Step 2: Parse using Member 2's parse_request() ----
            request_dict = parse_request(raw_data)
            request_dict["client_address"] = self.client_address

            # ---- Log the request ----
            method = request_dict.get("method", "?")
            path = request_dict.get("path", "?")
            thread_name = threading.current_thread().name
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {self.client_address[0]}:{self.client_address[1]} "
                  f"-> {method} {path}  ({thread_name})")

            # ---- Step 3: Route to handler -> get response bytes ----
            response_bytes = route(request_dict)

            # Ensure we always have bytes
            if isinstance(response_bytes, str):
                response_bytes = response_bytes.encode("utf-8")

            # ---- Step 4: Send response back through the socket ----
            self.client_socket.sendall(response_bytes)

        except socket.timeout:
            self._send_error(408, "Request Timeout")
        except ConnectionResetError:
            pass  # client disconnected mid-request
        except BrokenPipeError:
            pass  # client closed their end before we finished sending
        except Exception as e:
            print(f"[ERROR] {self.client_address} -> {e}")
            traceback.print_exc()
            self._send_error(500, "Internal Server Error")
        finally:
            self._close()

    # ----- Receive Helpers -----

    def _receive_full_request(self):
        """
        Read the complete HTTP request from the socket.

        For GET requests: read until we see the \\r\\n\\r\\n header terminator.
        For POST requests: after headers, continue reading until we've
        received Content-Length bytes of body data.
        """
        data = b""
        while True:
            try:
                chunk = self.client_socket.recv(RECV_BUFFER_SIZE)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk

            # Safety: reject absurdly large requests
            if len(data) > MAX_REQUEST_SIZE:
                self._send_error(413, "Request Entity Too Large")
                return None

            # Check if we've received the full headers
            if b"\r\n\r\n" in data:
                header_part, _, body_part = data.partition(b"\r\n\r\n")

                # Extract Content-Length to know how much body to expect
                content_length = self._extract_content_length(header_part)

                if content_length == 0:
                    # No body expected (GET, HEAD, etc.)
                    break

                # We need to read more body bytes
                total_received_body = len(body_part)
                while total_received_body < content_length:
                    remaining = content_length - total_received_body
                    try:
                        more = self.client_socket.recv(min(remaining, RECV_BUFFER_SIZE))
                    except socket.timeout:
                        break
                    if not more:
                        break
                    data += more
                    total_received_body += len(more)

                    if len(data) > MAX_REQUEST_SIZE:
                        self._send_error(413, "Request Entity Too Large")
                        return None
                break

        return data if data else None

    @staticmethod
    def _extract_content_length(header_bytes):
        """Parse Content-Length from raw header bytes."""
        try:
            header_text = header_bytes.decode("utf-8", errors="replace")
            for line in header_text.split("\r\n"):
                if line.lower().startswith("content-length:"):
                    return int(line.split(":", 1)[1].strip())
        except (ValueError, IndexError):
            pass
        return 0

    # ----- Error / Cleanup Helpers -----

    def _send_error(self, code, message):
        """Send a styled error response using Member 2's error_response()."""
        try:
            response = error_response(code, message)
            self.client_socket.sendall(response)
        except Exception:
            pass

    def _close(self):
        """Safely close the client socket."""
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.client_socket.close()
        except OSError:
            pass


# ===========================================================================
#  THREAD POOL  (limits max concurrent connections)
# ===========================================================================

class ThreadPool:
    """
    A simple bounded thread pool using a Semaphore.

    Instead of spawning unlimited threads (which would crash the server
    under heavy load), we limit the max concurrent threads. If the limit
    is reached, new connections wait until a thread finishes.
    """

    def __init__(self, max_workers):
        self.max_workers = max_workers
        self.semaphore = threading.Semaphore(max_workers)
        self.active_count = 0
        self.lock = threading.Lock()

    def submit(self, target, args=()):
        """Submit a task. Blocks if the pool is full."""
        self.semaphore.acquire()
        with self.lock:
            self.active_count += 1

        def wrapper():
            try:
                target(*args)
            finally:
                with self.lock:
                    self.active_count -= 1
                self.semaphore.release()

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread

    def get_active_count(self):
        with self.lock:
            return self.active_count


# ===========================================================================
#  MAIN SERVER
# ===========================================================================

class MarketplaceServer:
    """
    The main TCP socket server.

    Creates a TCP socket, binds to host:port, listens for connections,
    and dispatches each to a ClientHandler running in the ThreadPool.
    """

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, max_workers=DEFAULT_MAX_WORKERS):
        self.host = host
        self.port = port
        self.server_socket = None
        self.thread_pool = ThreadPool(max_workers)
        self.running = False

        # Stats
        self.total_requests = 0
        self.start_time = None
        self._stats_lock = threading.Lock()

    def start(self):
        """Bind, listen, and start accepting connections."""
        # Create TCP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Allow port reuse (prevents "Address already in use" after restart)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to host:port
        try:
            self.server_socket.bind((self.host, self.port))
        except OSError as e:
            print(f"[FATAL] Cannot bind to {self.host}:{self.port} -- {e}")
            print(f"        Is another process using port {self.port}?")
            sys.exit(1)

        # Start listening (backlog = 128 queued connections)
        self.server_socket.listen(128)
        self.server_socket.settimeout(1.0)  # 1s timeout so we can check self.running

        self.running = True
        self.start_time = time.time()

        # Print startup banner
        self._print_banner()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Main accept loop
        self._accept_loop()

    def _accept_loop(self):
        """Continuously accept new connections and dispatch to thread pool."""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()

                with self._stats_lock:
                    self.total_requests += 1

                # Create handler and submit to thread pool
                handler = ClientHandler(client_socket, client_address)
                self.thread_pool.submit(handler.handle)

            except socket.timeout:
                continue
            except OSError:
                if not self.running:
                    break
                raise

    def shutdown(self):
        """Gracefully stop the server."""
        if not self.running:
            return

        self.running = False
        print("\n[SERVER] Shutting down gracefully...")

        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass

        uptime = time.time() - self.start_time if self.start_time else 0
        print(f"[SERVER] Uptime: {uptime:.1f}s | Total requests served: {self.total_requests}")
        print("[SERVER] Goodbye.")

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C and kill signals."""
        self.shutdown()

    def _print_banner(self):
        """Print a startup banner with server info."""
        print("=" * 60)
        print("  MARKETPLACE SERVER")
        print("=" * 60)
        print(f"  Host:            {self.host}")
        print(f"  Port:            {self.port}")
        print(f"  URL:             http://localhost:{self.port}")
        print(f"  Max Workers:     {self.thread_pool.max_workers}")
        print(f"  Mode:            FULL (all modules connected)")
        print(f"  PID:             {os.getpid()}")
        print("-" * 60)
        print(f"  HTTP Parser:      core.http.http_parser      [OK]")
        print(f"  Response Builder: core.http.response_builder  [OK]")
        print(f"  Router:           core.app.router             [OK]")
        print("-" * 60)
        print(f"  Modules:  core | items | carts | deposit")
        print(f"            dashboard | inventory | wishlist | messages")
        print("=" * 60)
        print(f"  [SERVER] Listening on http://{self.host}:{self.port}")
        print(f"  [SERVER] Press Ctrl+C to stop\n")


# ===========================================================================
#  ENTRY POINT
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="Marketplace Low-Level Socket Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind (default: {DEFAULT_PORT})")
    parser.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS, help=f"Max threads (default: {DEFAULT_MAX_WORKERS})")
    args = parser.parse_args()

    server = MarketplaceServer(host=args.host, port=args.port, max_workers=args.workers)
    server.start()


if __name__ == "__main__":
    main()
