#!/usr/bin/env bash
#
# RAPIDS CLI Installation Script
#
# This installs the RAPIDS CLI system which completely replaces
# the bash-based build utilities.
#
# Usage:
#   sudo ./install.sh              # System-wide installation
#   ./install.sh --user            # User installation (no sudo needed)
#   pip install .                  # Python package installation
#

set -euo pipefail

RAPIDS_CLI_VERSION="${VERSION:-"1.0.0"}"
USER_INSTALL=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --user)
            USER_INSTALL=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--user]"
            echo ""
            echo "Options:"
            echo "  --user    Install for current user only (no sudo required)"
            echo ""
            echo "Examples:"
            echo "  sudo $0                    # System-wide installation"
            echo "  $0 --user                  # User installation"
            echo "  pip install .              # Install as Python package"
            echo "  pip install --user .       # Install as Python package (user)"
            exit 0
            ;;
    esac
done

cd "$(dirname "${BASH_SOURCE[0]}")"

echo "Installing RAPIDS CLI v${RAPIDS_CLI_VERSION}..."

# Check if we should use pip installation
if command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1; then
    PIP_CMD=$(command -v pip3 || command -v pip)
    
    if [ "$USER_INSTALL" = true ]; then
        echo "Installing as Python package (user installation)..."
        ${PIP_CMD} install --user .
        
        # Add user bin to PATH if not already there
        USER_BIN="${HOME}/.local/bin"
        if [ -d "${USER_BIN}" ]; then
            echo ""
            echo "✓ RAPIDS CLI v${RAPIDS_CLI_VERSION} installed successfully!"
            echo ""
            echo "The 'rapids' command is installed in: ${USER_BIN}"
            echo ""
            if [[ ":$PATH:" != *":${USER_BIN}:"* ]]; then
                echo "⚠️  Add ${USER_BIN} to your PATH:"
                echo ""
                echo "  export PATH=\"${USER_BIN}:\$PATH\"  # Add to ~/.bashrc or ~/.zshrc"
                echo ""
            fi
        fi
        
        # Install bash completion for user
        COMPLETION_DIR="${HOME}/.local/share/bash-completion/completions"
        mkdir -p "${COMPLETION_DIR}"
        cp bin/rapids-completion.bash "${COMPLETION_DIR}/rapids"
        echo "Installed bash completion to ${COMPLETION_DIR}"
        
    else
        # System-wide pip installation
        if [ "$EUID" -ne 0 ]; then
            echo "Error: System-wide installation requires sudo"
            echo ""
            echo "Try one of:"
            echo "  sudo $0                  # System-wide installation"
            echo "  $0 --user                # User installation (no sudo)"
            exit 1
        fi
        
        echo "Installing as Python package (system-wide)..."
        ${PIP_CMD} install .
        
        # Install bash completion system-wide
        if [ -d "/etc/bash_completion.d" ]; then
            cp bin/rapids-completion.bash /etc/bash_completion.d/rapids
            echo "Installed bash completion system-wide"
        fi
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
    
else
    # Fallback to manual installation (legacy)
    echo "Warning: pip not found, using manual installation"
    echo ""
    
    if [ "$USER_INSTALL" = true ]; then
        RAPIDS_CLI_DIR="${HOME}/.local/rapids-cli"
        BIN_DIR="${HOME}/.local/bin"
    else
        if [ "$EUID" -ne 0 ]; then
            echo "Error: System-wide installation requires sudo"
            echo ""
            echo "Try: $0 --user"
            exit 1
        fi
        RAPIDS_CLI_DIR="/opt/rapids-cli"
        BIN_DIR="/usr/local/bin"
    fi
    
    # Create installation directory
    mkdir -p "${RAPIDS_CLI_DIR}/bin"
    mkdir -p "${BIN_DIR}"
    
    # Copy files
    cp -r bin/* "${RAPIDS_CLI_DIR}/bin/"
    
    # Make executables
    chmod +x "${RAPIDS_CLI_DIR}/bin/rapids"
    
    # Create symlink
    ln -sf "${RAPIDS_CLI_DIR}/bin/rapids" "${BIN_DIR}/rapids"
    echo "Created symlink: ${BIN_DIR}/rapids"
    
    # Install bash completion
    if [ "$USER_INSTALL" = true ]; then
        COMPLETION_DIR="${HOME}/.local/share/bash-completion/completions"
        mkdir -p "${COMPLETION_DIR}"
        cp bin/rapids-completion.bash "${COMPLETION_DIR}/rapids"
        echo "Installed bash completion to ${COMPLETION_DIR}"
    else
        if [ -d "/etc/bash_completion.d" ]; then
            cp bin/rapids-completion.bash /etc/bash_completion.d/rapids
            echo "Installed bash completion system-wide"
        fi
    fi
    
    echo ""
    echo "✓ RAPIDS CLI v${RAPIDS_CLI_VERSION} installed successfully!"
    echo ""
    if [ "$USER_INSTALL" = true ] && [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
        echo "⚠️  Add ${BIN_DIR} to your PATH:"
        echo ""
        echo "  export PATH=\"${BIN_DIR}:\$PATH\"  # Add to ~/.bashrc or ~/.zshrc"
        echo ""
    fi
    echo "Usage:"
    echo "  rapids list              # List all projects"
    echo "  rapids build rmm -j 16   # Build a project"
    echo "  rapids --help            # Get help"
    echo ""
fi

