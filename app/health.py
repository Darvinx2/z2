"""Минимальный HTTP-сервер состояния для проверки развёрнутого контейнера.

Используется стадией local deploy конвейера: контейнер запускается с
пробросом порта, а конвейер проверяет, что приложение поднялось.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.config import settings

HOST = os.getenv("HEALTH_HOST", "0.0.0.0")  # nosec: сервис слушает внутри контейнера
PORT = int(os.getenv("HEALTH_PORT", "8080"))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 — имя задано BaseHTTPRequestHandler
        if self.path not in ("/", "/health"):
            self.send_error(404)
            return
        payload = json.dumps(
            {
                "status": "ok",
                "application": "secure-file-manager",
                "storage_root": str(settings.storage_root),
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        print(f"health: {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), HealthHandler)
    print(f"Проверка состояния доступна на http://{HOST}:{PORT}/health")
    server.serve_forever()


if __name__ == "__main__":
    main()
