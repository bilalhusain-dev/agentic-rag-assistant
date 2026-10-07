#!/usr/bin/env python3
"""
NexusRAG — Local Development Launcher
Runs the FastAPI server with live reloading enabled.
"""
import os
import sys
import uvicorn

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "127.0.0.1")
    
    print("=================================================================")
    print(" [NexusRAG] Launching Assistant Gateway...")
    print(f" Web UI:   http://{host}:{port}")
    print(f" API Docs: http://{host}:{port}/docs")
    print("=================================================================")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
