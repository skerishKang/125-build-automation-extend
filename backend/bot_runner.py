"""Entry point for the unified Telegram bot."""
import sys
import os

# Add the project root to the path so we can import backend modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from backend.bots.main.handlers.runtime import main


if __name__ == "__main__":
    main()
