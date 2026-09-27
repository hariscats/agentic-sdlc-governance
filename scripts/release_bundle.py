import argparse
import hashlib
import json
import re
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def zip_files(target: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)


def build(version: str, root: Path = Path(".")) -> Path:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-demo)?", version):
        raise ValueError("Version must be vMAJOR.MINOR.PATCH[-demo]")
    out = root / "dist" / version
    out.mkdir(parents=True, exist_ok=True)
    selected = [root / "pyproject.toml", root / "uv.lock", *sorted((root / "src").glob("*.py"))]
    files = {p.relative_to(root).as_posix(): p.read_bytes() for p in selected}
    source = out / "permit-intake.zip"
    zip_files(source, files)
    lock = tomllib.loads((root / "uv.lock").read_text())
    packages = [
        {
            "SPDXID": f"SPDXRef-Package-{i}",
            "name": pkg["name"],
            "versionInfo": pkg["version"],
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
        }
        for i, pkg in enumerate(lock["package"])
    ]
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"permit-intake-{version}-lockfile-inventory",
        "documentNamespace": f"https://github.com/hariscats/agentic-sdlc-governance/sbom/{digest(source.read_bytes())}",
        "creationInfo": {
            "created": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "creators": ["Tool: guardrails-as-code-0.1.0"],
        },
        "comment": (
            "Complete uv.lock inventory including development packages; "
            "not an installed-image inventory."
        ),
        "packages": packages,
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": p["SPDXID"],
            }
            for p in packages
        ],
    }
    (out / "sbom.spdx.json").write_text(json.dumps(sbom, indent=2) + "\n")
    manifest = {p.name: digest(p.read_bytes()) for p in (source, out / "sbom.spdx.json")}
    (out / "checksums.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(out)
    return out


def verify(out: Path) -> None:
    manifest = json.loads((out / "checksums.json").read_text())
    if set(manifest) != {"permit-intake.zip", "sbom.spdx.json"}:
        raise ValueError("Unexpected manifest entries")
    for name, expected in manifest.items():
        if digest((out / name).read_bytes()) != expected:
            raise ValueError(f"Digest mismatch: {name}")
    with zipfile.ZipFile(out / "permit-intake.zip") as archive:
        if archive.testzip() is not None:
            raise ValueError("Invalid ZIP member")
    print("Local integrity PASS (not a cryptographic attestation)")


def evidence(out: Path, root: Path = Path(".")) -> Path:
    verify(out)
    files = {
        name: (out / name).read_bytes()
        for name in ["permit-intake.zip", "sbom.spdx.json", "checksums.json"]
    }
    for path in [
        root / ".specify/memory/constitution.md",
        *sorted((root / "specs").glob("*/*.md")),
    ]:
        files[path.relative_to(root).as_posix()] = path.read_bytes()
    for name in [
        "cloud-agent-audit.json",
        "rehearsal.json",
        "pr-evidence.json",
        "attestation-verification.json",
        "sbom-verification.json",
    ]:
        path = root / ".demo-state" / name
        if path.exists():
            files[f"evidence/{name}"] = path.read_bytes()
    missing = [
        name
        for name in [
            "cloud-agent-audit.json",
            "pr-evidence.json",
            "attestation-verification.json",
            "sbom-verification.json",
        ]
        if f"evidence/{name}" not in files
    ]
    status: dict[str, Any] = {
        "version": out.name,
        "local_integrity": "pass",
        "missing_evidence": missing,
        "production_approval": "not asserted by this local bundle",
        "hook_audit": "not exported (local private files are not uploaded automatically)",
        "scan_summaries": "see PR check evidence and workflow artifacts; not inferred",
    }
    files["evidence/status.json"] = json.dumps(status, indent=2).encode()
    files["evidence/file-hashes.json"] = json.dumps(
        {name: digest(data) for name, data in files.items()}, indent=2
    ).encode()
    target = out / f"evidence-{out.name}.zip"
    zip_files(target, files)
    print(target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "verify", "evidence"])
    parser.add_argument("version")
    args = parser.parse_args()
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-demo)?", args.version):
        parser.error("Invalid version")
    out = Path("dist") / args.version
    if args.command == "build":
        build(args.version)
    elif args.command == "verify":
        verify(out)
    else:
        evidence(out)


if __name__ == "__main__":
    main()
