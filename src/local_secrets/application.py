"""Manifest operations and the backend interface."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml


class AppError(Exception):
    """An expected application error."""


@dataclass(frozen=True)
class Entry:
    backend: str
    service: str
    account: str
    purpose: str


class Backend(Protocol):
    def get(self, entry: Entry) -> str: ...
    def set(self, entry: Entry) -> None: ...
    def delete(self, entry: Entry) -> None: ...


class Manifest:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, Entry]:
        try:
            with self.path.open(encoding="utf-8") as stream:
                data = yaml.safe_load(stream)
        except FileNotFoundError as exc:
            raise AppError(
                f"Manifest not found: {self.path}; run manifest init first"
            ) from exc
        except (OSError, yaml.YAMLError) as exc:
            raise AppError("Cannot read manifest or parse YAML") from exc
        if not isinstance(data, dict) or set(data) != {"version", "secrets"}:
            raise AppError("Manifest must contain only version and secrets")
        if type(data["version"]) is not int or data["version"] != 1:
            raise AppError("Unsupported manifest version")
        if not isinstance(data["secrets"], dict):
            raise AppError("Manifest secrets must be a mapping")
        entries = {}
        for name, fields in data["secrets"].items():
            if (
                not isinstance(name, str)
                or not name.strip()
                or not isinstance(fields, dict)
            ):
                raise AppError("Invalid secret entry")
            if set(fields) != {"backend", "service", "account", "purpose"}:
                raise AppError(f"Invalid fields for entry {name!r}")
            if any(
                not isinstance(v, str) or not v.strip() or "\x00" in v
                for v in fields.values()
            ):
                raise AppError(f"Entry {name!r} must have nonempty text fields")
            entries[name] = Entry(**fields)
        return entries

    def save(self, entries: dict[str, Entry]) -> None:
        from dataclasses import asdict

        data = {"version": 1, "secrets": {k: asdict(v) for k, v in entries.items()}}
        try:
            self.path.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        except OSError as exc:
            raise AppError("Cannot write manifest") from exc

    def init(self) -> None:
        try:
            with self.path.open("x", encoding="utf-8") as stream:
                stream.write("version: 1\nsecrets: {}\n")
        except FileExistsError as exc:
            raise AppError("Manifest already exists") from exc
        except OSError as exc:
            raise AppError("Cannot create manifest") from exc


def entry_for(entries: dict[str, Entry], name: str) -> Entry:
    try:
        return entries[name]
    except KeyError as exc:
        raise AppError(f"No manifest entry named {name!r}") from exc
