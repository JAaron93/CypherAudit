"""Unit tests for the vendored Version-Free Rules verifier scripts.

The Bash tools under .agents/skills/version-free-rules-auditor/scripts/ are
repo-owned governance gates; the TDD rule requires their behavior to be pinned
here. Coverage: drift detection (operators, suffix floors, hidden rulebooks),
per-match junk filtering (real constraints survive unit-word lines), Gate A
allowlisting (including empty-allowlist fail-closed), Gate B path policy
(prose allow, manifest/env/workflow deny, YAML limited to review-config
paths), exit-code contracts, and fail-loud scans on unreadable inputs.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / ".agents" / "skills" / "version-free-rules-auditor" / "scripts"
INVENTORY = SCRIPTS / "vf_inventory.sh"
VERIFY = SCRIPTS / "vf_verify.sh"


def run_inventory(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(INVENTORY), str(root)], capture_output=True, text=True
    )


def run_verify(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(VERIFY), str(root), *args], capture_output=True, text=True
    )


def write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=agent@example.com", "-c", "user.name=agent", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def init_git_repo(tmp_path: Path) -> tuple[Path, str]:
    """Fresh git repo with one base commit; returns (root, base_sha)."""
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, "AGENTS.md", "# rules\n")
    git(tmp_path, "add", "AGENTS.md")
    git(tmp_path, "commit", "-q", "-m", "base")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return tmp_path, head


# ---- vf_inventory.sh: detection ------------------------------------------------------


def test_inventory_exit_code_contract(tmp_path: Path) -> None:
    assert run_inventory(tmp_path).returncode == 0  # clean repo
    write(tmp_path, "rules/prose.md", "pin pydantic>=2.0\n")
    done = run_inventory(tmp_path)
    assert done.returncode == 1  # hits found
    assert "./rules/prose.md:1" in done.stdout
    assert run_inventory(tmp_path / "missing").returncode == 2  # bad root


def test_detects_operator_and_suffix_floors(tmp_path: Path) -> None:
    write(tmp_path, "AGENTS.md", "Use requests>=2.31 for HTTP calls\n")
    write(tmp_path, "docs/platform.md", "Python 3.11+\nuAgents 0.26+\n")
    done = run_inventory(tmp_path)
    assert done.returncode == 1
    # Issue 1 regression: the bare word "requests" must not mask the constraint.
    assert "./AGENTS.md:1" in done.stdout
    # Issue 3: suffix floors ("3.11+", "0.26+") are binding constraints.
    assert "./docs/platform.md:1" in done.stdout
    assert "./docs/platform.md:2" in done.stdout


def test_bare_dotted_suffix_floor_flagged(tmp_path: Path) -> None:
    write(tmp_path, "notes.md", "pinned at 3.11+ upstream\n")
    done = run_inventory(tmp_path)
    assert done.returncode == 1
    assert "./notes.md:1" in done.stdout


def test_hidden_rulebooks_are_scanned(tmp_path: Path) -> None:
    # Issue 4 regression: .greptile/rules.md and .cursor/rules/** are governed prose.
    write(tmp_path, ".greptile/rules.md", "never pin pydantic>=2.14 in prose\n")
    write(tmp_path, ".cursor/rules/deps.mdc", "tabulate>=0.9 forbidden\n")
    done = run_inventory(tmp_path)
    assert done.returncode == 1
    assert "./.greptile/rules.md:1" in done.stdout
    assert "./.cursor/rules/deps.mdc:1" in done.stdout


# ---- vf_inventory.sh: per-match junk filtering ---------------------------------------


def test_duration_noise_not_flagged(tmp_path: Path) -> None:
    write(
        tmp_path,
        "perf.md",
        "cold start ~8 seconds\n"
        "p95 under 16ms\n"
        ">= 80% of calls\n"
        "=== 402 handled\n"
        "cost ~2-5 KB per row\n",
    )
    assert run_inventory(tmp_path).returncode == 0


def test_real_constraint_survives_noise_on_same_line(tmp_path: Path) -> None:
    # Issue 1 regression: a duration token must not discard the whole line.
    write(tmp_path, "mix.md", "took ~8s; pin requests>=2.31\n")
    done = run_inventory(tmp_path)
    assert done.returncode == 1
    assert "./mix.md:1" in done.stdout


def test_unit_suffixed_constraint_survives_percent_elsewhere(tmp_path: Path) -> None:
    # Issue 1 regression: number-and-unit noise elsewhere on the line must not
    # discard a real constraint ("95%" coverage note + real floor).
    write(tmp_path, "cov.md", "tabulate>=0.10.0 (95% coverage)\n")
    done = run_inventory(tmp_path)
    assert done.returncode == 1
    assert "./cov.md:1" in done.stdout


# ---- vf_verify.sh: Gate A ------------------------------------------------------------


def test_verify_gate_a_fail_and_allowlist(tmp_path: Path) -> None:
    write(tmp_path, "rules.md", "pydantic>=2.0\n")
    done = run_verify(tmp_path)
    assert done.returncode == 1
    assert "FAIL living-prose gate" in done.stderr

    allow = tmp_path / "allow.txt"
    allow.write_text("# labeled drift evidence\n./rules.md:1\n")
    done = run_verify(tmp_path, "--allow", str(allow))
    assert done.returncode == 0
    assert "PASS living-prose gate" in done.stdout


def test_verify_empty_allowlist_fails_closed(tmp_path: Path) -> None:
    # Issue 5 regression: an empty or comment-only allow file must exempt nothing.
    write(tmp_path, "rules.md", "pydantic>=2.0\n")
    for content in ("", "# comment only\n"):
        allow = tmp_path / "allow.txt"
        allow.write_text(content)
        done = run_verify(tmp_path, "--allow", str(allow))
        assert done.returncode == 1, f"fail-open for allow={content!r}"
        assert "./rules.md:1" in done.stderr


# ---- vf_verify.sh: Gate B ------------------------------------------------------------


def test_gate_b_prose_only_diff_passes(tmp_path: Path) -> None:
    root, base = init_git_repo(tmp_path)
    write(root, "AGENTS.md", "# rules v2\n")
    write(root, ".agents/tools/notes.sh", "echo hi\n")
    write(root, ".greptile/rules.md", "# review rules\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "docs")
    done = run_verify(root, "--base", base)
    assert done.returncode == 0
    assert "PASS diff gate" in done.stdout


def test_gate_b_denies_manifest_and_workflow(tmp_path: Path) -> None:
    # Issue 2 regression: .github/workflows/*.yml is executable config, not prose.
    root, base = init_git_repo(tmp_path)
    write(root, "pyproject.toml", '[project]\nname = "x"\n')
    write(root, ".github/workflows/ci.yml", "on: push\njobs: {}\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "sneak")
    done = run_verify(root, "--base", base)
    assert done.returncode == 1
    assert "manifest/lockfile" in done.stderr
    assert "workflow" in done.stderr


def test_gate_b_limits_yaml_to_review_config(tmp_path: Path) -> None:
    root, base = init_git_repo(tmp_path)
    write(root, ".coderabbit.yaml", "reviews:\n  path_filters: []\n")
    write(root, "infra/random.yaml", "key: value\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "yaml")
    done = run_verify(root, "--base", base)
    assert done.returncode == 1
    assert "infra/random.yaml" in done.stderr
    assert ".coderabbit.yaml" not in done.stderr


def test_verify_bad_base_ref_is_usage_error(tmp_path: Path) -> None:
    root, _ = init_git_repo(tmp_path)
    assert run_verify(root, "--base", "no-such-ref").returncode == 2


# ---- fail-loud scan contract ---------------------------------------------------------


def test_inventory_fails_loud_on_unreadable_file(tmp_path: Path) -> None:
    # Issue 7 regression: an unreadable rulebook must fail the scan (exit 2),
    # never masquerade as a clean pass.
    write(tmp_path, "ok.md", "no versions here\n")
    locked = write(tmp_path, "locked.md", "pydantic>=2.0\n")
    locked.chmod(0o000)
    try:
        done = run_inventory(tmp_path)
        assert done.returncode == 2
        assert "unreadable" in done.stderr
    finally:
        locked.chmod(0o644)
