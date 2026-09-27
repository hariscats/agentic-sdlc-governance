import json
import sys
from pathlib import Path
from typing import Any


def bound(sbom: dict[str, Any], verified: list[dict[str, Any]]) -> bool:
    return any(
        item.get("verificationResult", {}).get("statement", {}).get("predicate") == sbom
        for item in verified
    )


if __name__ == "__main__":
    document = json.loads(Path(sys.argv[1]).read_text())
    results = json.loads(Path(sys.argv[2]).read_text())
    if not bound(document, results):
        raise SystemExit("Downloaded SPDX file does not match a verified signed predicate")
    print("SPDX file matches the verified attestation predicate")
