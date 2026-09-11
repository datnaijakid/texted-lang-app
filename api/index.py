import sys
import traceback
from pathlib import Path

# Locate backend directory in various execution environments (local, Vercel Lambda, etc.)
base_dir = Path(__file__).resolve().parent
candidates = [
    base_dir.parent / "backend",
    base_dir / "backend",
    Path("/var/task/backend"),
    Path.cwd() / "backend",
]

for candidate in candidates:
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from app.main import app
except Exception as exc:
    # If app import fails, create a fallback ASGI app that renders the error clearly
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Texted API - Boot Diagnostic")
    tb = traceback.format_exc()

    @app.get("/{catchall:path}")
    def boot_error(catchall: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "error": "FastAPI failed to initialize",
                "exception": str(exc),
                "traceback": tb.splitlines(),
                "sys_path": sys.path,
                "current_dir": str(Path.cwd()),
                "files_in_task": [str(p) for p in Path("/var/task").iterdir()] if Path("/var/task").exists() else [],
            },
        )
