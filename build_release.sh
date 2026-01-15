#!/bin/bash
set -e

# Define directories
PROJECT_ROOT=$(pwd)
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_ENV_DIR="$PROJECT_ROOT/venv_build"

echo "=========================================="
echo "Dads Invoice Pro - Release Build Script"
echo "Target Architecture: x86_64 (Intel)"
echo "=========================================="

# 1. Clean previous builds
echo "[1/5] Cleaning up..."
rm -rf "$DIST_DIR"
rm -rf "$PROJECT_ROOT/build"
rm -rf "$BUILD_ENV_DIR"
rm -rf "$BACKEND_DIR/frontend_dist"

# 2. Build Frontend
echo "[2/5] Building Frontend..."
cd "$FRONTEND_DIR"
npm install --legacy-peer-deps
npm run build
if [ ! -d "dist" ]; then
    echo "Frontend build failed: dist directory not found."
    exit 1
fi
# Move frontend dist to backend for inclusion
cp -r dist "$BACKEND_DIR/frontend_dist"
echo "Frontend built and copied to $BACKEND_DIR/frontend_dist"


# 3. Setup x86_64 Python Environment
# We use 'arch -x86_64' to force running as Intel.
# This ensures PyInstaller pulls Intel binaries.
echo "[3/5] Setting up Intel Python Environment..."
cd "$PROJECT_ROOT"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "python3 could not be found"
    exit 1
fi

# Create venv using Intel architecture explicitly with /usr/bin/python3
arch -x86_64 /usr/bin/python3 -m venv "$BUILD_ENV_DIR"

# Activate environment
source "$BUILD_ENV_DIR/bin/activate"

# Verify architecture (should output 'x86_64' or similar)
CURRENT_ARCH=$(arch -x86_64 python3 -c "import platform; print(platform.machine())")
echo "Python running as: $CURRENT_ARCH"

echo "Creating compatible requirements file..."
# Create a version-relaxed requirements file for Python 3.9 compatibility
# We strip the specific versions (everything after ==)
# but keep the package names.
sed 's/==.*//' "$BACKEND_DIR/requirements.txt" > "$BACKEND_DIR/requirements_build.txt"

echo "Installing dependencies..."
arch -x86_64 python3 -m pip install --upgrade pip
arch -x86_64 python3 -m pip install -r "$BACKEND_DIR/requirements_build.txt"
arch -x86_64 python3 -m pip install pyinstaller

# 4. Run PyInstaller
echo "[4/5] Packaging with PyInstaller..."
cd "$BACKEND_DIR"

# Copy .env to backend for packaging
cp "$PROJECT_ROOT/.env" "$BACKEND_DIR/.env"

arch -x86_64 python3 -m PyInstaller --noconfirm --log-level=WARN \
    --name "DadsInvoicePro" \
    --add-data "frontend_dist:frontend_dist" \
    --add-data ".env:." \
    --clean \
    --distpath "$DIST_DIR" \
    --workpath "$PROJECT_ROOT/build" \
    --noconsole \
    run_app.py

# Clean up .env from backend
rm "$BACKEND_DIR/.env"

# Note: --noconsole hides terminal. Remove it if debugging is needed.
# Added --add-data ".env:." assuming .env is in backend dir, but user said it's in root?
# Let's check where .env is. User context says root. BACKEND_DIR/../.env
# We'll handle .env copy in step 5.

# 5. Finalize
echo "[5/5] Finalizing..."
# Copy specific .env if not baked in (PyInstaller add-data often reliable for baking)
# But let's copy it to the dist folder too just in case the app looks for it externally.
cp "$PROJECT_ROOT/.env" "$DIST_DIR/DadsInvoicePro/DadsInvoicePro.app/Contents/Resources/" 2>/dev/null || cp "$PROJECT_ROOT/.env" "$DIST_DIR/DadsInvoicePro/"

echo "=========================================="
echo "Build Complete!"
echo "Executable located at: $DIST_DIR/DadsInvoicePro/DadsInvoicePro.app"
echo "You can zip this app and send it to your sister."
echo "=========================================="
