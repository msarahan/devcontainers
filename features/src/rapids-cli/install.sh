#!/usr/bin/env bash
#
# RAPIDS CLI Installation Script
#
# This installs the RAPIDS CLI system which completely replaces
# the bash-based build utilities.
#

set -euo pipefail

RAPIDS_CLI_VERSION="${VERSION:-"1.0.0"}"
RAPIDS_CLI_DIR="/opt/rapids-cli"

echo "Installing RAPIDS CLI v${RAPIDS_CLI_VERSION}..."

# Create installation directory
mkdir -p "${RAPIDS_CLI_DIR}/bin"

# Copy files
cp -r "$(dirname "${BASH_SOURCE[0]}")/bin/"* "${RAPIDS_CLI_DIR}/bin/"

# Make executables
chmod +x "${RAPIDS_CLI_DIR}/bin/rapids"

# Create symlinks in /usr/local/bin
if [ -d "/usr/local/bin" ]; then
    ln -sf "${RAPIDS_CLI_DIR}/bin/rapids" /usr/local/bin/rapids
    echo "Created symlink: /usr/local/bin/rapids"
fi

# Install bash completion
if [ -d "/etc/bash_completion.d" ]; then
    ln -sf "${RAPIDS_CLI_DIR}/bin/rapids-completion.bash" /etc/bash_completion.d/rapids
    echo "Installed bash completion"
fi

# Add to profile
if [ -d "/etc/profile.d" ]; then
    cat > /etc/profile.d/rapids-cli.sh <<EOF
# RAPIDS CLI
export PATH="${RAPIDS_CLI_DIR}/bin:\$PATH"

# Set default manifest location if not already set
if [ -z "\${RAPIDS_MANIFEST:-}" ]; then
    if [ -f "/opt/rapids-build-utils/manifest.yaml" ]; then
        export RAPIDS_MANIFEST="/opt/rapids-build-utils/manifest.yaml"
    fi
fi
EOF
    echo "Created profile script: /etc/profile.d/rapids-cli.sh"
fi

echo ""
echo "✓ RAPIDS CLI v${RAPIDS_CLI_VERSION} installed successfully!"
echo ""
echo "Usage:"
echo "  rapids list              # List all projects"
echo "  rapids build rmm -j 16   # Build a project"
echo "  rapids --help            # Get help"
echo ""
echo "Set RAPIDS_MANIFEST environment variable to point to your manifest.yaml"
echo "Example:"
echo "  export RAPIDS_MANIFEST=/path/to/manifest.yaml"
echo ""

