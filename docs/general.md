# ZmalaTerminal engineering

The [technical guide](terminal.md) describes runtime behavior and hardware checks.
Start changes with the [requirements and interface contracts](../requirements/README.md).

## Requirements and tests

From the normal `ZmalaTerminal/` checkout beneath the workspace root, install
development dependencies under the workspace `tmp/`. For worktrees, set
`ZMALA_WORK_TMP` to that same workspace location explicitly.

```sh
mkdir -p ../tmp/terminal-dev
export ZMALA_WORK_TMP="$(cd ../tmp/terminal-dev && pwd)"
export TMPDIR="$ZMALA_WORK_TMP"
export PYTHONDONTWRITEBYTECODE=1
python3 -m venv --system-site-packages "$ZMALA_WORK_TMP/venv"
. "$ZMALA_WORK_TMP/venv/bin/activate"
python -m pip install -r requirements-dev.txt -r build_tools/doorstop-requirements.txt
make requirements REQUIREMENTS_OUTPUT="$ZMALA_WORK_TMP/requirements"
```

Linux display tests also need Tk, Pillow/ImageTk, GI, Cairo, Pango, Xvfb and xauth.
The system-site-packages environment exposes the distribution's GI bindings.
The full dependency installation is maintained in [Verify](../.github/workflows/verify.yml).
Use Linux filesystem permissions for updater and ownership tests. A Windows-backed
temporary directory can fail private-file checks even when tests call chmod.
In WSL, a Linux scratch mount beneath the workspace `tmp/` supplies these semantics.

`requirements/ownership.json` identifies the authoritative owner of each stable ID.
Imported parents retain their IDs. Update imported copies in a reviewed change
from their owner. Use `python build_tools/requirements.py --next-id LLR COMPONENT GROUP`
for a new ID. Keep requirement text, code references and test references in sync.

Implementation uses a standalone language comment such as
`# @llr LLR-TERM-REMOTE-016` immediately before the owning declaration or
cohesive block. Separate multiple IDs with a comma and a space.

A test begins with one each of the standalone `@test`, `@requirements`, `@environment`,
`@plan` and `@pass` comments. Link LLT directly to an LLR and HLT directly to
an HLR. State inputs, procedure and expected assertions. Refer to the test from
each Doorstop item. An inventory or a plan does not record an execution.

| Command | Coverage |
| --- | --- |
| `make test-llt` | Discovered low-level Python tests |
| `xvfb-run -a make test-hlt` | Discovered high-level Python tests, including Tk fixtures |
| `xvfb-run -a make test-hlt-display` | Additional standalone display scenarios |
| `make test-adhoc` | Installer, package and development-tool tests |
| `python -m ruff check --no-cache .` | Python correctness lint |
| `make requirements REQUIREMENTS_OUTPUT="$ZMALA_WORK_TMP/requirements"` | Doorstop validation and trace reports |

Hardware, privileged namespace and installed-host tests declare prerequisites in
their leading plans. Inspect skipped tests before reporting qualification.
Native media checks use the Pi SDK environment defined in Verify.


## Cross-component tests

The display provisioning test uses the real HTTP test service from a separate
ZmalaServer checkout under the workspace `tmp/`. Prepare the server revision pinned
in Verify by running `npm --prefix zmala_server ci --ignore-scripts` in that checkout.
Set `ZMALA_TEST_SERVER_ROOT` to its absolute checkout path and run
`xvfb-run -a make test-hlt-display` from this repository. The service uses
temporary account state and an ephemeral loopback port.


The Docker NAT and secure-network HLTs run in the separate Zmala image-builder
checkout. Prepare the lab as documented there, then set ZMALA_IMAGE_BUILDER_ROOT
before invoking either HLT wrapper. These cases use synthetic media and run
separately from the display and portable suites.

## Packages, leaflets and pull requests

The package includes `docs/general.md` and `docs/terminal.md`. Build a disposable
archive with the following command.

```sh
python build_tools/linux/package-terminal.py --output "$ZMALA_WORK_TMP/terminal-package.tar.gz"
```

Leaflet generation and visual checks are described in the [leaflet guide](leaflet/README.md).
Pass its `--output` option to keep generated PDFs under the workspace `tmp/`.

Use an issue, a `codex/` branch and a pull request to `main`. Run relevant local
checks, then wait for Verify on the current pull request commit before merging
through GitHub. Runtime, package and release changes require an increased component
version and update sequence. The current version gate also applies to packaged
documentation and leaflets. Requirements-only changes are exempt. Release publishing
is a separate manual workflow described in the repository README.
