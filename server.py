from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from agent import (
    CONFIG_PATH, Context, GovernanceError, database_status,
    inspect_file, load_json, search_workspace
)


class Handler(BaseHTTPRequestHandler):
    server_version = "CEPKnowledgeAgent/0.6-sqlite"

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise GovernanceError("Invalid Content-Length") from exc
        if length <= 0:
            return {}
        if length > 2_000_000:
            raise GovernanceError("Request body exceeds 2 MB")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GovernanceError("Request must contain valid UTF-8 JSON") from exc
        if not isinstance(payload, dict):
            raise GovernanceError("Request JSON must be an object")
        return payload

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            if path == "/health":
                ctx = Context.load()
                self.send_json(200, {
                    "status": "ok",
                    "mode": "read-only-sqlite",
                    "roots": [root.name for root in ctx.roots],
                })
                return
            if path == "/roots":
                ctx = Context.load()
                self.send_json(200, {
                    "knowledge_roots": [
                        {"name": root.name, "path": str(root.path)}
                        for root in ctx.roots
                    ]
                })
                return
            if path == "/status":
                self.send_json(200, database_status())
                return
            self.send_json(404, {"error": "not_found", "path": path})
        except (GovernanceError, FileNotFoundError, RuntimeError) as exc:
            self.send_json(400, {"error": type(exc).__name__, "message": str(exc)})
        except Exception as exc:
            self.send_json(500, {"error": type(exc).__name__, "message": str(exc)})

    def do_POST(self) -> None:
        try:
            ctx = Context.load()
            path = urlparse(self.path).path
            payload = self.read_json()

            if path == "/inspect":
                value = payload.get("path")
                if not isinstance(value, str):
                    raise GovernanceError("'path' must be a string")
                result = inspect_file(ctx, value)
            elif path == "/search":
                query = payload.get("query")
                if not isinstance(query, str):
                    raise GovernanceError("'query' must be a string")
                extensions = payload.get("extensions")
                roots = payload.get("roots")
                if extensions is not None and not isinstance(extensions, list):
                    raise GovernanceError("'extensions' must be an array")
                if roots is not None and not isinstance(roots, list):
                    raise GovernanceError("'roots' must be an array")
                result = search_workspace(
                    ctx,
                    query,
                    max_results=int(payload.get("max_results", 50)),
                    extensions=extensions,
                    roots=roots,
                )
            elif path in {"/trace", "/apply", "/validate", "/propose"}:
                raise GovernanceError(
                    "This HTTP server is retrieval-only. Run traces directly in PowerShell."
                )
            else:
                self.send_json(404, {"error": "not_found", "path": path})
                return

            self.send_json(200, result)
        except (GovernanceError, FileNotFoundError, ValueError, RuntimeError) as exc:
            self.send_json(400, {"error": type(exc).__name__, "message": str(exc)})
        except Exception as exc:
            self.send_json(500, {"error": type(exc).__name__, "message": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    config = load_json(CONFIG_PATH)
    host = str(config.get("server_host", "127.0.0.1"))
    if host not in {"127.0.0.1", "localhost"}:
        raise GovernanceError("Server host must remain local-only")
    port = int(config.get("server_port", 8765))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"CEP/LBE SQLite agent listening on http://{host}:{port}")
    print("Mode: read-only local retrieval")
    print("Endpoints: GET /health, GET /roots, GET /status, POST /search, POST /inspect")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
