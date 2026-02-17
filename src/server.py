#!/usr/bin/env python3
"""
ARCADE server entry point.

The server logic is split across the server/ package for clarity:
  - server/config.py      Constants and paths
  - server/state.py        Mutable global state
  - server/utils.py        Image encoding, JSON, depth colormap, etc.
  - server/session_mgr.py  Session folder and frame paths
  - server/handlers/       HTTP and WebSocket handlers (base, websocket, mesh, inference, ...)
  - server/workers.py      Render and save background workers
  - server/app.py          Tornado app and routes
  - server/main.py         Initialization and main loop

Run with: python server.py
"""

from server.main import main

if __name__ == "__main__":
    main()