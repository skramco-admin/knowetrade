from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
