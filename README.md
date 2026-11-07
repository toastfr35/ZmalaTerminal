# ZmalaTerminal

This repository contains the Zmala Pi terminal.

- [Technical guide](docs/terminal.md)
- [Development and requirements](docs/general.md)
- [Migration provenance](docs/migration/provenance.json)
- [Downloads](https://github.com/toastfr35/ZmalaTerminal/releases)

## Related repositories

- [ZmalaServer](https://github.com/toastfr35/ZmalaServer)
- [ZmalaApp](https://github.com/toastfr35/ZmalaApp)
- [Zmala](https://github.com/toastfr35/Zmala)
- [Original ZmalaCall repository and historical downloads](https://github.com/toastfr35/ZmalaCall)

## Release

Install on Pi OS using the package. The leaflet ZIP contains reading PDFs, folded A4 print PDFs and printing instructions for all supported languages.

After Verify passes on the merged version, dispatch **Release** on main. The release environment requires the existing Ed25519 signing secret `ZMALA_TERMINAL_UPDATE_KEY`. Keep the package and updater signing checks enabled before publishing.
