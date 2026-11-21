"""Fluidian — the AI-native interface framework.

The engine package hosts the HTTP/SSE server, the application supervisor,
the AI kernel and the capability registry.  It depends only on the Python
standard library.
"""

__version__ = "1.2.0"
PROTOCOL_VERSION = 1

__all__ = ["__version__", "PROTOCOL_VERSION"]
