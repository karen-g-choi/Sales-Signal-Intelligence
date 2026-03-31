#!/bin/zsh

PROJECT_ROOT="/Users/karen/Documents/sales_analytics_portfolio"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

cd "$FRONTEND_DIR" || exit 1

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is not installed or not available in PATH."
  echo ""
  echo "Please install Node.js first, then run this launcher again."
  echo "Recommended: install the current LTS version from https://nodejs.org/"
  echo ""
  echo "After installation, reopen Terminal and run:"
  echo "  cd /Users/karen/Documents/sales_analytics_portfolio/frontend"
  echo "  npm install"
  echo "  npm run dev"
  read -k 1 "?Press any key to close..."
  echo ""
  exit 1
fi

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install || exit 1
fi

echo "Starting React dashboard..."
echo "Open http://localhost:5173 once Vite is ready."

npm run dev
