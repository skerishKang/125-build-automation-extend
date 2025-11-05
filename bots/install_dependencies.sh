#!/bin/bash
# Install dependencies for all 4 bots

echo "=========================================="
echo "🤖 4-Bot Telegram System - Dependency Installer"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Function to install dependencies for a bot
install_bot_deps() {
    local bot_dir=$1
    local bot_name=$2
    echo "Installing dependencies for $bot_name..."
    echo "----------------------------------------"

    if [ -f "$bot_dir/requirements.txt" ]; then
        pip3 install -r "$bot_dir/requirements.txt"
        if [ $? -eq 0 ]; then
            echo "✅ $bot_name dependencies installed successfully"
        else
            echo "❌ Failed to install $bot_name dependencies"
            exit 1
        fi
    else
        echo "⚠️ requirements.txt not found for $bot_name"
    fi
    echo ""
}

# Install dependencies for each bot
install_bot_deps "main_bot" "Main Bot"
install_bot_deps "document_bot" "Document Bot"
install_bot_deps "audio_bot" "Audio Bot"
install_bot_deps "image_bot" "Image Bot"

echo "=========================================="
echo "🎉 All dependencies installed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env"
echo "2. Edit .env and add your API keys"
echo "3. Start Redis server: redis-server"
echo "4. Run all bots: python run_bots.py"
echo ""
