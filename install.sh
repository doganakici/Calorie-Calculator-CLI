#!/usr/bin/env bash
# Quick installer for Calorie Calculator CLI on Fedora / Linux
set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"

mkdir -p "${BIN_DIR}"

LAUNCHER="${BIN_DIR}/calorie"

cat << 'EOF' > "${LAUNCHER}"
#!/usr/bin/env bash
APP_PATH="$(dirname "$(readlink -f "$0")")/../.."
# Fallback to direct path if symlinked
EOF

# Write explicit target runner pointing to the app directory
cat << EOF > "${LAUNCHER}"
#!/usr/bin/env bash
exec /usr/bin/env python3 "${APP_DIR}/calorie_calc.py" "\$@"
EOF

chmod +x "${LAUNCHER}"

# Create convenient alias calorie-calc
ln -sf "${LAUNCHER}" "${BIN_DIR}/calorie-calc"

echo "=========================================================="
echo " [✓] Calorie Calculator installed successfully!"
echo "=========================================================="
echo "Executable linked to: ${LAUNCHER}"
echo
# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    echo "Notice: ${BIN_DIR} is not currently in your PATH."
    echo "Add it by running:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    echo "  source ~/.bashrc"
    echo
fi

echo "You can now run the app from any directory with:"
echo "  calorie"
echo "  # or"
echo "  calorie-calc"
echo "=========================================================="
