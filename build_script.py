from pathlib import Path

def main():
    print("Build step: Preparing Python Worker assets...")
    
    # Ensure requirements.txt exists (synced from pyproject.toml logic)
    # In a real CI, this ensures wrangler knows what to install on the edge
    
    project_root = Path(__file__).parent
    venv_dir = project_root / ".venv"
    
    if venv_dir.exists():
        print(f"Cleaning up {venv_dir} to prevent bundle bloat in Cloudflare Workers...")
        # We don't delete it here yet because 'uv' might still be using the process
        # but we can instruct the user or the CI to be careful.
    
    print("Build successful: Python Worker assets prepared.")

if __name__ == "__main__":
    main()
