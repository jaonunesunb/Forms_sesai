from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import requests

# Paths to Ontop configuration files
OBDA_DIR = Path(__file__).resolve().parent / "OBDA"
MAPPING_FILE = OBDA_DIR / "mapping.obda"
ONTOLOGY_FILE = OBDA_DIR / "ontology.ttl"
PROPERTIES_FILE = OBDA_DIR / "ontop.properties"

# Port where Ontop will listen
ONTOP_PORT = int(os.getenv("ONTOP_PORT", "8080"))

# Reference to the Ontop subprocess (if started)
_ontop_process: Optional[subprocess.Popen] = None

def start_ontop() -> None:
    """Start the Ontop endpoint if it is not already running."""

    global _ontop_process

    # If the process is already running, do nothing
    if _ontop_process and _ontop_process.poll() is None:
        return

    # Build the command to launch Ontop.  We rely on the `ontop` CLI being
    # available in the environment.
    cmd = [
        "ontop",
        "endpoint",
        "--mapping",
        str(MAPPING_FILE),
        "--ontology",
        str(ONTOLOGY_FILE),
        "--properties",
        str(PROPERTIES_FILE),
        "--port",
        str(ONTOP_PORT),
    ]

    _ontop_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Wait for the server to start accepting connections.  We try for a short
    # period and then give up, letting subsequent requests fail naturally.
    for _ in range(30):
        try:
            requests.get(f"http://localhost:{ONTOP_PORT}/sparql", timeout=0.1)
            break
        except Exception:
            time.sleep(0.1)


def query_ontop(sparql: str) -> dict:
    """Execute a SPARQL query against the Ontop endpoint."""

    # Ensure the server is running before sending the request
    start_ontop()

    headers = {
        "Content-Type": "application/sparql-query",
        "Accept": "application/sparql-results+json",
    }

    response = requests.post(
        f"http://localhost:{ONTOP_PORT}/sparql",
        data=sparql.encode("utf-8"),
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def stop_ontop() -> None:
    """Terminate the Ontop subprocess if it is running."""

    global _ontop_process
    if _ontop_process and _ontop_process.poll() is None:
        _ontop_process.terminate()
        try:
            _ontop_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _ontop_process.kill()
    _ontop_process = None


# Ensure the Ontop process is terminated when the interpreter exits
try:  # pragma: no cover - defensive programming
    import atexit

    atexit.register(stop_ontop)
except Exception:  # pragma: no cover
    pass