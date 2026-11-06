from click.testing import CliRunner

from local_secrets.cli import cli


class FakeBackend:
    def __init__(self):
        self.calls = []

    def set(self, entry):
        self.calls.append(("set", entry))

    def get(self, entry):
        self.calls.append(("get", entry))
        return "test-value"

    def delete(self, entry):
        self.calls.append(("delete", entry))


def test_manifest_and_secret_lifecycle(tmp_path):
    path = tmp_path / "secrets.yaml"
    runner = CliRunner()
    backend = FakeBackend()
    obj = {"backends": {"keychain": backend}}

    def run(*args):
        result = runner.invoke(cli, ["--manifest", str(path), *args], obj=obj)
        assert result.exit_code == 0, result.output
        return result.output

    run("manifest", "init")
    run(
        "manifest",
        "add",
        "api",
        "--service",
        "example",
        "--account",
        "dev",
        "--purpose",
        "API access",
    )
    assert run("manifest", "list") == "api\n"
    assert "API access" in run("manifest", "show", "api")
    run("secret", "set", "api")
    assert run("secret", "get", "api") == "test-value\n"
    assert "test-value" not in path.read_text()
    run("manifest", "update", "api", "--purpose", "deployment")
    assert "deployment" in path.read_text()
    run("secret", "delete", "api")
    assert "api:" in path.read_text()
    run("manifest", "remove", "api")
    assert [call[0] for call in backend.calls] == ["set", "get", "delete"]


def test_errors_are_reported(tmp_path):
    path = tmp_path / "secrets.yaml"
    runner = CliRunner()
    args = ["--manifest", str(path)]
    assert runner.invoke(cli, [*args, "manifest", "init"]).exit_code == 0
    assert runner.invoke(cli, [*args, "manifest", "init"]).exit_code != 0
    assert runner.invoke(cli, [*args, "secret", "get", "missing"]).exit_code != 0
    path.write_text("version: 1\nsecrets:\n  foo:\n    value: not-allowed\n")
    result = runner.invoke(cli, [*args, "manifest", "list"])
    assert result.exit_code != 0
    assert "not-allowed" not in result.output
