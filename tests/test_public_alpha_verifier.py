from pathlib import Path
import subprocess


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_public_alpha.sh"


def test_public_alpha_verifier_has_valid_bash_syntax():
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


def test_public_alpha_verifier_preserves_clean_room_contract():
    text = SCRIPT.read_text(encoding="utf-8")
    required = [
        "unset GH_TOKEN GITHUB_TOKEN GIT_ASKPASS SSH_AUTH_SOCK GIT_SSH_COMMAND",
        "export HOME=\"$CLEAN_HOME\"",
        "git ls-remote \"$REPO_URL\" \"refs/heads/$REF\"",
        "RESOLVED_COMMIT_AFTER",
        "if [[ \"$RESOLVED_COMMIT_AFTER\" != \"$EXPECTED_COMMIT\" ]]",
        '"credential_isolation"',
        '"output_sha256"',
    ]
    for marker in required:
        assert marker in text
