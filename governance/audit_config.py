import json
from pathlib import Path


def differences(expected: dict[str, object], actual: dict[str, object]) -> list[str]:
    return [key for key, value in expected.items() if key not in actual or actual[key] != value]


def main() -> None:
    expected = json.loads(Path("governance/expected-agent-config.json").read_text())
    actual = json.loads(Path(".demo-state/cloud-agent-actual.json").read_text())
    drift = differences(expected, actual)
    result = {"status": "drift" if drift else "pass", "differing_fields": drift}
    Path(".demo-state/cloud-agent-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    raise SystemExit(1 if drift else 0)


if __name__ == "__main__":
    main()
