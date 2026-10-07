.PHONY: demo test reset

demo:  ## start the live console on http://127.0.0.1:8001 and open a browser
	python3 -m demo.console.server

test:  ## run the test suite (standard library only)
	python3 -m unittest discover -s tests -t .

reset:  ## clear local demo state
	rm -rf .agent-audit demo/events.jsonl /tmp/proof
