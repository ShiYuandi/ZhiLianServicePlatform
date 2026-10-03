from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "/app/alembic.ini", "upgrade", "head"],
        check=True,
    )
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--proxy-headers",
            "--log-level",
            os.getenv("LOG_LEVEL", "INFO").lower(),
        ],
    )


if __name__ == "__main__":
    main()
