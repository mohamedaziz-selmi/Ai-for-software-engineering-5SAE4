"""AI Assistant & Delivery Review API (FastAPI). Same run convention as the other platform services:

    ..\\.venv\\Scripts\\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8003   (cwd: module_assistant_delivery/backend)

Routes: /api/ai/* (API) and /assistant/* (UI), as registered in platform_gateway.
"""

from app.main import create_app

app = create_app()
