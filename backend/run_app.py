import os
import sys
import webbrowser
import uvicorn
import multiprocessing
import time
from threading import Timer

def open_browser():
    """Wait a slightly longer time to ensure server is up, then open browser."""
    # Wait for server to start
    # localhost:8001 because we might bind there to avoid conflict with dev 8000
    # But for a packaged app, 8000 is usually fine if user isn't a dev.
    # Let's use 8001 just to be safe and distinct.
    webbrowser.open("http://localhost:8001/")

if __name__ == "__main__":
    # PyInstaller needs this for multiprocessing
    multiprocessing.freeze_support()

    # Set environment variable to tell main.py we are in packaged mode
    os.environ["IS_PACKAGED_APP"] = "True"
    
    # Load .env from PyInstaller temporary directory
    if getattr(sys, 'frozen', False):
        try:
            # sys._MEIPASS is where PyInstaller unpacks data (or where it lives in onedir)
            bundle_dir = sys._MEIPASS
        except Exception:
            # Fallback for onedir if _MEIPASS isn't set (sometimes happens in older versions, but 6.x usually sets it)
            bundle_dir = os.path.dirname(os.path.abspath(__file__))
            
        env_path = os.path.join(bundle_dir, '.env')
        if os.path.exists(env_path):
            print(f"Loading environment from bundled .env: {env_path}")
            from dotenv import load_dotenv
            load_dotenv(env_path)
        else:
            print(f"Bundled .env not found at {env_path}")
    
    # Also ensure we are using the bundled .env if possible, or expect it in the same dir
    # For now, we assume the app will look for .env in the current working directory or 
    # we can try to find the one bundled. 
    # Detailed path handling is in config.py, but for now let's just create this runner.

    print("Starting Dad's Invoice Pro...")

    # Schedule browser opening
    Timer(2, open_browser).start()

    # Run Uvicorn
    # We import app content via string to allow reload support if needed, 
    # but for frozen app, direct import is better or string is fine.
    # String requires the module to be importable.
    # Since we are in the root of the bundled app, "app.main:app" should work.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, log_level="info", reload=False)
