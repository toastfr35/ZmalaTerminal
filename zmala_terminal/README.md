# Zmala Terminal

Python terminal with platform adapters. Shared controllers start in `common/main.py`.

| Responsibility | Source |
| --- | --- |
| Application | `common/` owns state, configuration, calls, setup and Tk views |
| Pi hardware | `linux/` owns native media, Bluetooth, HDMI-CEC and Pi services |
| Windows compatibility | `windows/` supplies development adapters outside the Pi baseline |

`common/` means shared by terminal platforms. Shared Pi host identity and storage
policy belongs to the separate Zmala image repository. Native, display and hardware
tests use the explicit commands in the implementation guide.

Read the [implementation guide](../docs/terminal.md) and
[development setup](../docs/general.md). Product requirements are in
[`requirements/terminal/`](../requirements/terminal/); unit and system plans are in
[`tests/terminal/`](../tests/terminal/).

Run from the repository root after installing the development dependencies:

```sh
make test-llt
xvfb-run -a make test-hlt test-hlt-display
make requirements
```

Windows adapters were restored from `toastfr35/ZmalaCall` commit
`0731446f8cd6fcbafb93bbda104a2c3a6765b5fb` after the component split.
The shared settings UI can be accepted without the native SDK using the
[isolated Windows fixture](../docs/terminal.md#windows-settings-acceptance).
