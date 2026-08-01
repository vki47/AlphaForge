"""AlphaForge browser UI development server.

The quantitative and AI service layers remain framework-independent.  This
entry point now serves their browser client instead of constructing a desktop
widget tree.
"""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parent / "web"


def run_app(host: str = "127.0.0.1", port: int = 8080) -> None:
    handler = lambda *args, **kwargs: SimpleHTTPRequestHandler(  # noqa: E731
        *args, directory=str(WEB_ROOT), **kwargs
    )
    server = ThreadingHTTPServer((host, port), handler)
    print(f"AlphaForge web terminal: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve the AlphaForge web terminal")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()
    run_app(args.host, args.port)
