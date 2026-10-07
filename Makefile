.PHONY: demo test reset

demo:  ## start the live console on http://127.0.0.1:8001 and open a browser
	uv run --frozen python -m demo.console.server

test:  ## run the test suite
	uv run --frozen pytest

reset:  ## clear local demo state
	rm -rf .agent-audit demo/events.jsonl /tmp/proof
