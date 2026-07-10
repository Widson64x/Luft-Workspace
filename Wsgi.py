"""Bootstrap WSGI para execucao do Hub Central."""

from __future__ import annotations

import os

from App import CriarApp

app = CriarApp()


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    porta = int(os.getenv("PORT", "9000"))
    debug = os.getenv("APP_ENV", "development").strip().lower() != "production"
    app.run(host=host, port=porta, debug=debug)