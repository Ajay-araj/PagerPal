"""
PagerPal Launcher Script
Starts the FastAPI backend and serves the compiled React frontend at http://localhost:8000
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 65)
    print("  PagerPal · Evidence-Driven Autonomous Incident Response Console")
    print("  SIMULATION ENVIRONMENT · No production infrastructure connected")
    print("=" * 65)
    print("Starting server on http://localhost:8000 ...")
    print("API documentation: http://localhost:8000/docs")
    print("=" * 65)
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)

