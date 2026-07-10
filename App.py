"""Entrypoint de desenvolvimento do Hub Central."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from App import CriarApp

load_dotenv()

app = CriarApp()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    porta = int(os.getenv("PORT", "9010"))
    debug = os.getenv("APP_ENV", "development").strip().lower() != "production"
    app.run(host=host, port=porta, debug=debug)
