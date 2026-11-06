from types import SimpleNamespace
from unittest.mock import patch

import pytest

from local_secrets.application import AppError, Entry
from local_secrets.keychain import Keychain

ENTRY = Entry("keychain", "service", "account", "purpose")


def test_commands_and_secure_set():
    with (
        patch("local_secrets.keychain.sys.platform", "darwin"),
        patch("local_secrets.keychain.sys.stdin.isatty", return_value=True),
        patch("local_secrets.keychain.subprocess.run") as run,
    ):
        run.return_value = SimpleNamespace(returncode=0, stdout=b"secret\n")
        backend = Keychain()
        backend.set(ENTRY)
        assert backend.get(ENTRY) == "secret"
        backend.delete(ENTRY)
        assert run.call_args_list[0].args[0] == [
            "/usr/bin/security",
            "add-generic-password",
            "-a",
            "account",
            "-s",
            "service",
            "-U",
            "-w",
        ]
        assert run.call_args_list[1].args[0][-1] == "-w"
        assert run.call_args_list[2].args[0][1] == "delete-generic-password"
        assert all("secret" not in call.args[0] for call in run.call_args_list)


def test_errors_do_not_leak_subprocess_output():
    with (
        patch("local_secrets.keychain.sys.platform", "darwin"),
        patch(
            "local_secrets.keychain.subprocess.run",
            return_value=SimpleNamespace(returncode=1, stderr=b"sensitive"),
        ),
    ):
        with pytest.raises(AppError, match="exit 1") as exc:
            Keychain().get(ENTRY)
        assert "sensitive" not in str(exc.value)


def test_set_requires_tty():
    with patch("local_secrets.keychain.sys.stdin.isatty", return_value=False):
        with pytest.raises(AppError, match="interactive terminal"):
            Keychain().set(ENTRY)
