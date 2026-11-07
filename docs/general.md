# ZmalaTerminal engineering

Read the [technical guide](terminal.md).

## Requirements and tests

Install Python development dependencies and the pinned Doorstop tooling:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt -r build_tools/doorstop-requirements.txt
make requirements
```

`requirements/ownership.json` identifies the authoritative owner of each stable ID.
Imported parents retain their IDs. Update imported copies in a reviewed change
from their owner. Use `python build_tools/requirements.py --next-id LLR COMPONENT GROUP`
for a new ID. Keep requirement text, code references and test references in sync.

Implementation uses a standalone language comment such as
`# @llr LLR-TERM-REMOTE-016` immediately before the owning declaration or
cohesive block. Separate multiple IDs with a comma and a space.

A test begins with standalone `@test`, `@requirements`, `@environment`,
`@plan` and `@pass` comments. Link LLT directly to an LLR and HLT directly to
an HLR. State inputs, procedure and expected assertions. Refer to the test from
each Doorstop item. An inventory or a plan does not record an execution.


## Cross-component tests

The display provisioning test uses the real HTTP test service from a separate
ZmalaServer checkout. Prepare the server revision pinned in Verify by running
npm --prefix zmala_server ci --ignore-scripts in that checkout. Set
ZMALA_TEST_SERVER_ROOT to its checkout path and run
xvfb-run -a make test-hlt-display from this repository. The service uses
temporary account state and an ephemeral loopback port.


The Docker NAT and secure-network HLTs run in the separate Zmala image-builder
checkout. Prepare the lab as documented there, then set ZMALA_IMAGE_BUILDER_ROOT
before invoking either HLT wrapper. These cases use synthetic media and run
separately from the display and portable suites.
