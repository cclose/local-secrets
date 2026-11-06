"""macOS Keychain adapter using Apple's security utility."""

import subprocess
import sys

from .application import AppError, Entry


class Keychain:
    def _run(self, args: list[str], *, capture: bool = True) -> str:
        if sys.platform != "darwin":
            raise AppError("The keychain backend requires macOS")
        try:
            result = subprocess.run(
                ["/usr/bin/security", *args],
                check=False,
                stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            raise AppError("Could not start the macOS security utility") from exc
        if result.returncode:
            # Do not relay subprocess output: it could contain sensitive data.
            raise AppError(
                f"Keychain operation failed (security exit {result.returncode})"
            )
        if not capture:
            return ""
        try:
            value = result.stdout.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AppError("Keychain value is not UTF-8 text") from exc
        return value.removesuffix("\n")

    @staticmethod
    def _identity(entry: Entry) -> list[str]:
        return ["-a", entry.account, "-s", entry.service]

    def get(self, entry: Entry) -> str:
        return self._run(["find-generic-password", *self._identity(entry), "-w"])

    def set(self, entry: Entry) -> None:
        if not sys.stdin.isatty():
            raise AppError("Setting a secret requires an interactive terminal")
        self._run(
            ["add-generic-password", *self._identity(entry), "-U", "-w"], capture=False
        )

    def delete(self, entry: Entry) -> None:
        self._run(["delete-generic-password", *self._identity(entry)], capture=False)
