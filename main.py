"""
HS AI SOLUTIONS — JULY CENTRAL CONTROL SERVER
Root ASGI Entrypoint for Render Cloud Deployment
Organization: HS AI Solutions
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/

Exposes ASGI 'app' so that both:
  - Default Render command: 'uvicorn main:app --host 0.0.0.0 --port $PORT'
  - Package command:        'uvicorn july_distribution.server.main:app --host 0.0.0.0 --port $PORT'
work identically without configuration mismatch.
"""

from __future__ import annotations
import os
import sys

# Ensure repository root is in sys.path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from july_distribution.server.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
