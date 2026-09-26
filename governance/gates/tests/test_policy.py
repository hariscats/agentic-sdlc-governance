import pytest

from governance.gates.policy import Change, PullRequest, agent_policy, is_agent, risk, trace


def valid() -> PullRequest:
    return PullRequest(
        author="app/copilot-swe-agent",
        title="feat(T012): intake [spec:001]",
        labels=["spec:001"],
        linked_issues=[1],
        files=[Change("src/app.py"), Change("tests/test_app.py")],
        additions=399,
    )


def test_positive_boundary() -> None:
    pr = valid()
    pr.additions = 400
    assert agent_policy(pr) == []
    assert trace(pr, {"001": "- [ ] T012 create app"}) == []
    assert risk(pr) == "medium"


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("additions", 401, "exceeds"),
        ("linked_issues", [], "linked issue"),
        ("labels", [], "label"),
        ("files", [Change(".github/workflows/ci.yml")], "protected"),
        ("files", [Change("src/x.py", ".github/workflows/ci.yml")], "protected"),
    ],
)
def test_agent_negative(field: str, value: object, message: str) -> None:
    pr = valid()
    setattr(pr, field, value)
    assert any(message in e for e in agent_policy(pr))


@pytest.mark.parametrize(
    "title,files,specs",
    [
        ("T012", [Change("src/app.py")], {"001": "T012"}),
        ("spec:001", [Change("src/app.py")], {"001": "T012"}),
        ("spec:999 T012", [Change("src/app.py")], {"001": "T012"}),
        ("spec:001 T999", [Change("src/app.py")], {"001": "T012"}),
        ("spec:001 T012", [Change("src/app.py")], {"001": "T012"}),
    ],
)
def test_trace_negative(title: str, files: list[Change], specs: dict[str, str]) -> None:
    assert trace(PullRequest(author="human", title=title, files=files), specs)


def test_signals_and_risk() -> None:
    pr = PullRequest(author="human")
    assert not is_agent(pr)
    assert agent_policy(pr) == []
    assert trace(pr, {}) == []
    assert risk(pr) == "low"
    pr.commits = ["feat: work\n\nCo-authored-by: Copilot <example@example.invalid>"]
    assert is_agent(pr)
    pr.files = [Change("src/auth.py")]
    assert risk(pr) == "high"
    pr.files = [Change("src/__init__.py")]
    pr.title = "spec:001 T012"
    assert trace(pr, {"001": "T012"}) == []


@pytest.mark.parametrize(
    "pr",
    [
        # Verified on public cloud-agent PRs: gh reports "app/copilot-swe-agent",
        # REST "Copilot"; commits use copilot-swe-agent[bot] and a Copilot noreply email.
        PullRequest(author="app/copilot-swe-agent"),
        PullRequest(author="Copilot"),
        PullRequest(author="human", identities=["copilot-swe-agent[bot]"]),
        PullRequest(author="human", identities=["198982749+Copilot@users.noreply.github.com"]),
        PullRequest(author="human", labels=["agent-authored"]),
        PullRequest(
            author="human",
            commits=["x\n\nCo-authored-by: bot <198982749+Copilot@users.noreply.github.com>"],
        ),
    ],
)
def test_agent_signals(pr: PullRequest) -> None:
    assert is_agent(pr)
    assert agent_policy(pr)


def test_human_signals_are_not_agent() -> None:
    pr = PullRequest(
        author="hariscats",
        identities=["hariscats", "123+hariscats@users.noreply.github.com", "GitHub"],
        commits=["Co-authored-by: Hariscats <123+hariscats@users.noreply.github.com>"],
    )
    assert not is_agent(pr)


@pytest.mark.parametrize(
    "path", ["GOVERNANCE/hooks.py", ".GITHUB/workflows/ci.yml", "Scripts/x.sh", "agents.md"]
)
def test_protected_paths_ignore_case(path: str) -> None:
    pr = valid()
    pr.files = [Change(path)]
    assert any("protected" in e for e in agent_policy(pr))
    assert risk(pr) == "high"
