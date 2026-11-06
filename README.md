# local-secrets

A small inventory of secret metadata with values stored in secure backends. The MVP includes the macOS Keychain backend and uses Python 3.12+, Click, and PyYAML. Manifest operations work on Linux; Keychain operations require macOS.

## Install

```sh
python -m pip install .
local-secrets --help
```

For development, install the project with its dev dependencies using `uv sync --locked`, then run `uv run pytest` and `uv run ruff check src tests`.

## Use

```sh
local-secrets manifest init
local-secrets manifest add api-token --service local-secrets/example-api --account developer --purpose 'Example API access'
local-secrets manifest list
local-secrets manifest show api-token
local-secrets secret set api-token
local-secrets secret get api-token
local-secrets secret delete api-token
local-secrets manifest update api-token --purpose 'Deployment API access'
local-secrets manifest remove api-token
```

Use `--manifest PATH` before the command to select a manifest (default `secrets.yaml`). See `secrets.example.yaml`. A manifest contains only a version and metadata: name, backend, service, account, and purpose. It is suitable for Git only if you keep secrets and sensitive metadata out of these fields. Never put a secret in an option, including metadata options, or in the YAML. YAML is validated using safe loading and unknown entry fields are rejected.

`secret set` asks Apple's `security` utility to prompt twice with hidden input directly on the terminal. It needs an interactive terminal; stdin pipes and secret arguments are deliberately unsupported. `secret get` intentionally prints the value to stdout; protect terminals, redirection, and pipelines accordingly. Do not record that output. `secret delete` deletes only the backend value. `manifest remove` deletes only metadata. Updating service, account, or backend changes the lookup target and does not migrate or delete the old value. Delete the old value first if desired.

## Keychain behavior and macOS validation

Each entry selects a generic password by service and account. `security add-generic-password -U ... -w` updates or adds an item in the default keychain and prompts for the value; get and delete use the default search list. Keep the intended keychain in that list and avoid duplicate service/account pairs across keychains, where lookup may select a different item. Keychain access may prompt for authorization. The adapter does not use the insecure `-A` option. The backend interface can be implemented by other stores in Python; only `keychain` is registered in this MVP.

The command options were checked against Apple's [security tool source and built-in help](https://github.com/apple-oss-distributions/Security/blob/main/SecurityTool/macOS/security.c). Apple notes that the [security CLI primarily targets file-based keychains](https://developer.apple.com/documentation/technotes/tn3137-on-mac-keychains). Tests mock subprocess calls on Linux. **Real macOS testing remains necessary:** verify hidden prompts and confirmation, add/update/get/delete, Unicode and empty values, Keychain authorization dialogs, locked keychains, duplicate entries, and errors on the macOS versions you support. The CLI handles UTF-8 text values; it is not a binary-secret interface.
