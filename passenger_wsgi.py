import sys
import os

# Dodaj katalog aplikacji do ścieżki Pythona
sys.path.insert(0, os.path.dirname(__file__))

from app import app as flask_app
from config import Config

application = flask_app

# Serwer MCP (sterowanie CRM z aplikacji Claude) — montowany tylko, gdy w
# config.py ustawiony jest Config.MCP_TOKEN. Adres URL do skonfigurowania
# w Claude jako "custom connector" to wtedy:
#   https://<twoja-domena>/mcp-<MCP_TOKEN>/
_mcp_token = getattr(Config, "MCP_TOKEN", None)
if _mcp_token:
    import mcp_server

    _mcp_prefix = f"/mcp-{_mcp_token}"
    # mcp_server.wsgi_app jest zwykłą, synchroniczną funkcją WSGI (bez ASGI,
    # bez wątków w tle, bez montowania niczego przy starcie procesu) — patrz
    # komentarz w mcp_server.py przy definicji wsgi_app.
    _mcp_wsgi_app = mcp_server.wsgi_app

    class _McpDispatcher:
        """Kieruje żądania pod /mcp-<token>(/...) do serwera MCP, resztę do Flaska."""

        def __init__(self, default_app, prefix, mounted_app):
            self.default_app = default_app
            self.prefix = prefix
            self.mounted_app = mounted_app

        def __call__(self, environ, start_response):
            path = environ.get("PATH_INFO", "")
            if path == self.prefix or path.startswith(self.prefix + "/"):
                environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + self.prefix
                environ["PATH_INFO"] = path[len(self.prefix):] or "/"
                return self.mounted_app(environ, start_response)
            return self.default_app(environ, start_response)

    application = _McpDispatcher(flask_app, _mcp_prefix, _mcp_wsgi_app)
