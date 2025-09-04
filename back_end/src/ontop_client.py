from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import requests

# Paths to Ontop configuration files
OBDA_DIR = Path(__file__).resolve().parent / "obda"
MAPPING_FILE = OBDA_DIR / "mapping.obda"
ONTOLOGY_FILE = OBDA_DIR / "ontology.ttl"
PROPERTIES_FILE = OBDA_DIR / "ontop.properties"

# Port where Ontop will listen
ONTOP_PORT = int(os.getenv("ONTOP_PORT", "8080"))

# Reference to the Ontop subprocess (if started)
_ontop_process: Optional[subprocess.Popen] = None
