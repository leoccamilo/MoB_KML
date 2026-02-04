import os
import sys
import webbrowser
import time
import traceback
from threading import Thread

def open_browser():
    time.sleep(3)
    try:
        webbrowser.open('http://127.0.0.1:8000')
    except Exception as e:
        print(f"Could not open browser: {e}")

if __name__ == "__main__":
    app_dir = os.path.dirname(os.path.abspath(__file__))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    try:
        # Direct import so Nuitka can trace the dependency
        from app.main import app as fastapi_app
        import uvicorn

        browser_thread = Thread(target=open_browser, daemon=True)
        browser_thread.start()

        print("Starting MoB_KML server on http://127.0.0.1:8000 ...")
        uvicorn.run(
            fastapi_app,
            host="127.0.0.1",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)
    except Exception as e:
        # Write error to file next to exe for debugging
        err_path = os.path.join(app_dir, "mob_kml_error.log")
        with open(err_path, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
