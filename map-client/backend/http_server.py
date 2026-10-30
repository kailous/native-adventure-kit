"""Shared threaded HTTP listener for map assets and the media/MCP gateway."""
from http.server import ThreadingHTTPServer as _ThreadingHTTPServer


class ThreadingHTTPServer(_ThreadingHTTPServer):
    # Browsers and guide images can open more than the stdlib default of five
    # connections together. This bounds pending accepts; it changes no routes,
    # authentication or listening addresses.
    request_queue_size = 32
