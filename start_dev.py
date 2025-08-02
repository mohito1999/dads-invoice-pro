import subprocess
import os
import time
import atexit

# Get the absolute path of the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# --- Store processes to terminate them on exit ---
processes = []
def cleanup():
    print("Shutting down processes...")
    for p in processes:
        try:
            p.terminate()
        except ProcessLookupError:
            pass # Process already terminated
    
    # Wait a moment for graceful shutdown
    time.sleep(2)

    # Force kill any that are still running
    for p in processes:
        if p.poll() is None:
            try:
                p.kill()
                print(f"Killed process {p.pid}")
            except ProcessLookupError:
                pass # Process already terminated during the grace period
    
    # Stop docker-compose
    print("Stopping Docker services...")
    try:
        subprocess.run(["docker-compose", "down"], check=True, cwd=project_root)
        print("Docker services stopped.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Could not stop docker-compose services: {e}")


atexit.register(cleanup)


# --- 1. Start Docker services ---
print("Starting Docker services in the background...")
docker_compose_cmd = ["docker-compose", "up", "-d"]
try:
    subprocess.run(docker_compose_cmd, check=True, cwd=project_root)
    print("Docker services started successfully.")
except subprocess.CalledProcessError as e:
    print(f"Failed to start Docker services: {e}")
    exit(1)
except FileNotFoundError:
    print("Error: 'docker-compose' command not found. Is Docker installed and in your PATH?")
    exit(1)


# --- 2. Start Backend Server ---
print("\nStarting backend server...")
backend_dir = os.path.join(project_root, "backend")
uvicorn_executable = os.path.join(backend_dir, "venv/bin/uvicorn")
backend_cmd = [uvicorn_executable, "app.main:app", "--reload"]

try:
    backend_process = subprocess.Popen(backend_cmd, cwd=backend_dir)
    processes.append(backend_process)
    print(f"Backend server started with PID: {backend_process.pid}")
except FileNotFoundError:
    print(f"Error: Could not find '{uvicorn_executable}'. Make sure the virtual environment and dependencies are set up correctly.")
    exit(1)


# --- 3. Start Frontend Server ---
print("\nStarting frontend development server...")
frontend_dir = os.path.join(project_root, "frontend")
frontend_cmd = ["npm", "run", "dev"]

try:
    frontend_process = subprocess.Popen(frontend_cmd, cwd=frontend_dir)
    processes.append(frontend_process)
    print(f"Frontend server started with PID: {frontend_process.pid}")
except FileNotFoundError:
    print("Error: 'npm' command not found. Is Node.js installed and in your PATH?")
    exit(1)


# --- Keep the main script alive & wait for exit ---
print("\nDevelopment environment is running.")
print("View frontend at http://localhost:5173")
print("Press Ctrl+C to shut down all services.")

try:
    # Wait for the frontend process to exit. When it does (or when Ctrl+C is pressed),
    # the atexit handler will clean everything up.
    frontend_process.wait()

except KeyboardInterrupt:
    print("\nCtrl+C received. Shutting down...")
