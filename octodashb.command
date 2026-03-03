#!/bin/bash

# --- CONFIGURATION ---
ENV_NAME="octopus_energy_dashboard"
SCRIPT_PATH="$HOME/GitHub-Code/octopus_energy_dashboard/app.py"
URL="http://localhost:5454"
# ---------------------

# 1. RENAME and MINIMIZE the current terminal window immediately
# This makes it easy to find in the Dock right-click menu
echo -n -e "\033]0;⚡️ OCTOPUS DASHBOARD ENGINE\007"

osascript <<EOF
    tell application "Terminal"
        set miniaturized of window 1 to true
    end tell
EOF

# 2. Start the browser in the background
# We do this before 'exec' so it doesn't get blocked by the Python server
(sleep 7 && /Applications/Firefox.app/Contents/MacOS/firefox -new-window "$URL") &

# 3. Load Conda and REPLACE the shell with Python
# 'exec' ensures that when you quit the terminal, the script dies instantly.
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

echo "Server starting... Close this terminal window to stop the script."
exec python3 "$SCRIPT_PATH"
