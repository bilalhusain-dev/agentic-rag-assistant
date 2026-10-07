#!/usr/bin/env python3
"""
NexusRAG — Local Development Launcher
Runs the FastAPI server with live reloading enabled.
"""
import uvicorn

if __name__ == "__main__":
    print("=================================================================")
    print(" 🚀 Launching NexusRAG Assistant Gateway...")
    print(" 🌐 Web UI:   http://127.0.0.1:8000")
    print(" 📚 API Docs: http://127.0.0.1:8000/docs")
    print("=================================================================")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
