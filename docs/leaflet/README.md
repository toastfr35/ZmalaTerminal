# Terminal end user leaflet

This is a four-page manual for the supplied, prepared terminal. It covers physical
connections, Wi-Fi and server QR setup, remote use and local settings. It does not
instruct users to prepare media, install software, administer the server or connect
Ethernet. The back page combines remote operation and local settings.

The authoring sources are `locales/*.json`, `layout.css` and `assets/`, with the
approved official logo reused on all four pages directly from `docs/branding/PNG/`. The locale
set must exactly match `zmala_terminal/common/shared/terminal-languages.json`.
There is no English fallback. Equipment captions use translated generic names
(terminal, camera and remote control). Connection instructions identify the blue
and black USB ports and the supplied power supply, without model names, power
ratings or case-button instructions. The setup page starts with following the
first-start on-screen instructions; TV test detail and reset instructions are
in the technical guide. All instructions are translated. These are initial
translations, with technical/layout checks;
native-speaker editorial review has not been recorded.

## Generate

From the repository root, install the tooling dependencies:

```sh
npm ci --ignore-scripts
npx playwright install chromium
python -m pip install -r build_tools/leaflet/requirements.txt
```

Install suitable fonts before rendering. On Debian/Ubuntu, install `fonts-noto-core`
and `fonts-noto-cjk`. Windows uses Arial/Segoe UI, Nirmala UI, Leelawadee UI,
Microsoft YaHei, MS Gothic/Yu Gothic and Malgun Gothic. The browser performs
Unicode shaping and bidirectional layout. A successful overflow check does not
by itself prove every glyph exists; review the rendered pages on a new build host.

```sh
python build_tools/leaflet/generate.py --language en
python build_tools/leaflet/generate.py --language fr
python build_tools/leaflet/generate.py --language all --bundle
```

Output defaults to `build_tools/dist/leaflets/` and stays out of Git. Each locale
produces a self-contained HTML proof, a four-page PDF and a two-page landscape A4
PDF. `--output PATH` selects a different folder. `--html-only` needs only Python
and creates the HTML proofs. `--node PATH` and `--browser PATH` select an installed
Node runtime and Chromium/Chrome/Edge executable. Otherwise Playwright uses its
installed Chromium. The optional ZIP contains only PDFs from that invocation
and the printing notes, not old PDFs from the output folder.

The PDF build rejects missing/extra locales, missing keys, incomplete sections,
empty strings, broken images, overflowing content and non-four-page reading PDFs.
Text remains live and selectable; hardware and overview graphics contain no
captions or instruction text. The official wordmark is the branding exception.
Numbered port markers are HTML text placed outside the SVG. Physical port
layout and remote buttons are never mirrored for RTL languages.

## Monochrome artwork

The print editions use black text on white paper, vector outline equipment and
the original leaflet cover illustration in grayscale. Button details show the selected button's position
on the remote; translated captions also say top/bottom for green/red. Connector
numbers remain outside the diagram. Color is never needed to interpret the
printed illustrations. The official wordmark is reused with grayscale styling.

## Print

Use the `-A4.pdf` file. Print actual size on **one A4 sheet**, landscape,
double-sided, **flip on the short edge**, then fold in the middle. Disable the
printer driver's booklet and multiple-pages modes. Test one sheet before a run.
The reading PDF is exactly 148.5 × 210 mm per page, so each spread fills A4 at 100%.

Left-to-right editions place pages **4 | 1** outside and **2 | 3** inside. Arabic
and Urdu use right binding, with **1 | 4** outside and **3 | 2** inside. The PDFs
already contain this imposition. See [printing.txt](printing.txt) for the notes
included in the ZIP.

## Impact and verification

The leaflet follows the five-card settings carousel and optional TV setup.
Runtime, `@llr` anchors, Doorstop records and verification plans are updated together. Content was checked against the setup flow,
settings/input controllers and these existing requirements:

- `HLR-TERM-SETUP-019`, `HLR-TERM-SETUP-020`; `LLR-TERM-SETUP-025` through
  `LLR-TERM-SETUP-035` for the setup workflow; the leaflet covers camera/remote
  verification and QR enrollment, without detailing TV tests or reset.
- `HLR-TERM-REMOTE-011`, `HLR-TERM-REMOTE-012` and the associated remote LLRs.
- `HLR-TERM-CONFIG-016`, `HLR-TERM-CONFIG-017` and the associated settings LLRs.
- The connections and user workflows in [the terminal guide](../terminal.md).

Publishing regression checks belong in `tests/adhoc/test_terminal_leaflet.py` because they
verify publishing tooling, not product behavior. Run them with:

```sh
python -m unittest tests.adhoc.test_terminal_leaflet -v
```

After copy/layout changes, generate all locales and inspect the PDFs, including
Arabic/Urdu and every supported script. Automated checks cover layout bounds and
page ordering, not translation approval or physical printer qualification.

Every release generates all language editions and publishes
`ZmalaTerminal-Leaflets.zip` alongside the terminal software package. Verify
builds the same ZIP in CI and retains it as the `terminal-package` workflow
artifact for seven days. The release collector and publisher require exactly the
two PDFs per supported language and `PRINTING.txt`, reject incomplete, unexpected
or duplicate members, and check PDF signatures and ZIP integrity. Loose PDFs and
HTML proofs remain build outputs rather than additional release assets.

See [assets/README.md](assets/README.md) for graphic sources and the cover prompt.
