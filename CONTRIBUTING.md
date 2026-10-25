# Contributing to Media Content Guard

Thanks for your interest in improving **Media Content Guard**! This is a custom
[Home Assistant](https://www.home-assistant.io/) integration distributed through
[HACS](https://hacs.xyz/). Contributions of all kinds — bug reports, fixes,
features, translations and documentation — are welcome.

## Repository layout

```
media_content_guard/
├─ custom_components/media_content_guard/   # the integration
│  ├─ __init__.py                        # setup / unload
│  ├─ config_flow.py                     # UI configuration flow
│  ├─ guard.py                           # matching + enforcement
│  ├─ entity.py                          # base entity
│  ├─ matching.py                        # pure keyword matching
│  ├─ sensor.py / switch.py / logbook.py
│  ├─ const.py
│  ├─ services.yaml                      # service definitions
│  ├─ strings.json                       # source UI strings (English)
│  ├─ translations/                      # de, en, es, fr
│  └─ brand/                             # local brand images (HA 2026.3+)
├─ tests/                                # pytest suite
├─ docs/                                 # additional documentation
├─ README.md / README.de.md              # English + German
└─ hacs.json / manifest.json
```

## Development environment

Create a virtual environment and install the tooling:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install ruff pytest pytest-homeassistant-custom-component
```

## Linting and formatting

We use [ruff](https://docs.astral.sh/ruff/) for both linting and formatting:

```bash
ruff check .
ruff format --check .
```

Run `ruff check --fix .` and `ruff format .` to apply fixes automatically.

## Tests

```bash
pytest
```

The test suite is built on
[`pytest-homeassistant-custom-component`](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component).
Please add or update tests for any behavioural change and make sure the suite is
green before opening a pull request.

## Translations

The integration is multilingual:

- **UI strings** live in `custom_components/media_content_guard/translations/`
  (`de`, `en`, `es`, `fr`).
- The English source of truth is `custom_components/media_content_guard/strings.json`.

When you add a new user-facing string, add it to `strings.json` **and** to every
language file under `translations/`. Keep the key structure identical across all
files. Entity names are translatable too — follow the existing `entity` blocks.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: match keywords against the playlist name
fix: keep stopping after a speaker reconnects
docs: explain how to migrate from a YAML automation
chore: bump dev dependencies
```

Common types: `feat`, `fix`, `docs`, `chore`, `ci`, `refactor`, `test`.
These prefixes drive the automatic release notes and version resolution.

## Pull request process

1. Fork the repository and create a feature branch off `main`.
2. Make your change; keep it focused and small where possible.
3. Run `ruff check .`, `ruff format --check .` and `pytest` — all must pass.
4. Update `CHANGELOG.md` under `## [Unreleased]`.
5. Update documentation (`README.md` and its language sections) and translations
   where relevant.
6. Open a pull request against `main` and fill in the pull request template.

A maintainer will review your change. Thank you for contributing!
