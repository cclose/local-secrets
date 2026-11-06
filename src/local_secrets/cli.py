"""Command-line interface for local-secrets."""

from pathlib import Path

import click
import yaml

from .application import AppError, Entry, Manifest, entry_for
from .keychain import Keychain


class CommandGroup(click.Group):
    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except AppError as exc:
            raise click.ClickException(str(exc)) from exc


@click.group(cls=CommandGroup)
@click.option(
    "--manifest",
    "path",
    type=click.Path(path_type=Path),
    default="secrets.yaml",
    show_default=True,
)
@click.pass_context
def cli(ctx, path):
    """Track secret metadata and manage values in secure backends."""
    ctx.ensure_object(dict)
    ctx.obj.setdefault("manifest", Manifest(path))
    ctx.obj.setdefault("backends", {"keychain": Keychain()})


@cli.group()
def manifest():
    """Create and edit the commit-safe inventory."""


@manifest.command("init")
@click.pass_obj
def manifest_init(obj):
    """Create a new empty manifest."""
    obj["manifest"].init()
    click.echo("Manifest created.")


@manifest.command("list")
@click.pass_obj
def manifest_list(obj):
    """List entries."""
    for name in sorted(obj["manifest"].load()):
        click.echo(name)


@manifest.command("show")
@click.argument("name")
@click.pass_obj
def manifest_show(obj, name):
    """Show one entry's metadata."""
    from dataclasses import asdict

    entry = entry_for(obj["manifest"].load(), name)
    click.echo(
        yaml.safe_dump({name: asdict(entry)}, sort_keys=False, allow_unicode=True),
        nl=False,
    )


@manifest.command("add")
@click.argument("name")
@click.option("--backend", default="keychain", show_default=True)
@click.option("--service", required=True)
@click.option("--account", required=True)
@click.option("--purpose", required=True)
@click.pass_obj
def manifest_add(obj, name, backend, service, account, purpose):
    """Add metadata; do not enter secret values here."""
    entries = obj["manifest"].load()
    if name in entries:
        raise AppError("Entry already exists")
    if any(
        not value.strip() or "\x00" in value
        for value in (name, backend, service, account, purpose)
    ):
        raise AppError("Entry fields must be nonempty text")
    entries[name] = Entry(backend, service, account, purpose)
    obj["manifest"].save(entries)
    click.echo("Entry added.")


@manifest.command("update")
@click.argument("name")
@click.option("--backend")
@click.option("--service")
@click.option("--account")
@click.option("--purpose")
@click.pass_obj
def manifest_update(obj, name, backend, service, account, purpose):
    """Update metadata without moving the stored value."""
    from dataclasses import replace

    entries = obj["manifest"].load()
    entry = entry_for(entries, name)
    changes = {
        k: v
        for k, v in {
            "backend": backend,
            "service": service,
            "account": account,
            "purpose": purpose,
        }.items()
        if v is not None
    }
    if not changes or any(not v.strip() or "\x00" in v for v in changes.values()):
        raise AppError("Provide at least one nonempty field")
    entries[name] = replace(entry, **changes)
    obj["manifest"].save(entries)
    click.echo("Entry updated.")


@manifest.command("remove")
@click.argument("name")
@click.pass_obj
def manifest_remove(obj, name):
    """Remove metadata only; the backend value is untouched."""
    entries = obj["manifest"].load()
    entry_for(entries, name)
    del entries[name]
    obj["manifest"].save(entries)
    click.echo("Entry removed.")


@cli.group()
def secret():
    """Read or change a value in its configured backend."""


def resolve(obj, name):
    entry = entry_for(obj["manifest"].load(), name)
    try:
        return entry, obj["backends"][entry.backend]
    except KeyError as exc:
        raise AppError(f"Unsupported backend: {entry.backend}") from exc


@secret.command("get")
@click.argument("name")
@click.pass_obj
def secret_get(obj, name):
    """Print the secret value to stdout."""
    entry, backend = resolve(obj, name)
    click.echo(backend.get(entry))


@secret.command("set")
@click.argument("name")
@click.pass_obj
def secret_set(obj, name):
    """Enter a value at the backend's secure prompt."""
    entry, backend = resolve(obj, name)
    backend.set(entry)
    click.echo("Secret stored.")


@secret.command("delete")
@click.argument("name")
@click.pass_obj
def secret_delete(obj, name):
    """Delete the backend value, preserving the manifest entry."""
    entry, backend = resolve(obj, name)
    backend.delete(entry)
    click.echo("Secret deleted.")
