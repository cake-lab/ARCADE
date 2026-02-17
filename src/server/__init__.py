# ARCADE server package - split from server.py for maintainability.
# Run via: python server.py (or python -m server.main)

from server.app import make_app

__all__ = ["make_app"]
