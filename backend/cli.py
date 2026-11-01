"""Entry point: `python cli.py --help`."""
import sys

from app.controllers.cli_controller import main

if __name__ == "__main__":
    sys.exit(main())
