from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("UNIGURU_HOST", "0.0.0.0")
    port = int(os.getenv("UNIGURU_PORT", "8000"))
    uvicorn.run("uniguru.service.api:app", host=host, port=port, workers=1)


if __name__ == "__main__":
    main()
