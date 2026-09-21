import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

def export_specs():
    print("Generating OpenAPI / Swagger schema from FastAPI app...")
    spec = app.openapi()

    # Paths to write
    workspace_root = backend_dir.parent
    
    json_paths = [
        backend_dir / "swagger.json",
        backend_dir / "openapi.json",
        workspace_root / "swagger.json",
        workspace_root / "openapi.json",
    ]

    yaml_paths = [
        backend_dir / "swagger.yaml",
        backend_dir / "openapi.yaml",
        workspace_root / "swagger.yaml",
        workspace_root / "openapi.yaml",
    ]

    formatted_json = json.dumps(spec, indent=2, ensure_ascii=False)

    for path in json_paths:
        path.write_text(formatted_json, encoding="utf-8")
        print(f"  [+] Saved {path}")

    try:
        import yaml
        formatted_yaml = yaml.dump(spec, sort_keys=False, allow_unicode=True)
        for path in yaml_paths:
            path.write_text(formatted_yaml, encoding="utf-8")
            print(f"  [+] Saved {path}")
    except ImportError:
        print("  [!] PyYAML not installed; skipped .yaml exports.")

    print("OpenAPI / Swagger spec export complete!")

if __name__ == "__main__":
    export_specs()
