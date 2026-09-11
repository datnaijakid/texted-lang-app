import sys
from pathlib import Path

# Add backend directory to sys.path so 'app' and its modules are discoverable
base_dir = Path(__file__).resolve().parent
backend_dir = base_dir / "backend" if (base_dir / "backend").exists() else base_dir.parent / "backend"

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
