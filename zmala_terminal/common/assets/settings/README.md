# Settings artwork

The nine original SVG pictograms use a shared 128-unit grid, round silhouettes,
soft dark discs and mint, lilac, blue or amber details. Reset uses coral. They
are intentional source artwork; the 256-pixel PNG exports are shipped for both
Windows and Raspberry Pi. `build_tools/render-settings-artwork.cjs` regenerates
PNGs using the development-only Sharp library. The runtime uses its existing
bounded portrait cache and has no new dependencies.

Flags are from [flag-icons v7.3.2](https://github.com/lipis/flag-icons/tree/fe15c16e7463d0c66d6c5730e9d0e832438d98e1/flags/4x3),
commit `fe15c16e7463d0c66d6c5730e9d0e832438d98e1`, under the included
`flags/LICENSE.txt` (MIT). Original SVGs and their PNG exports are retained.
`common/settings_artwork.py` maps the 16 supported language codes to flag files;
the carousel and language editor use the same asset. Native language names
always accompany flags. English uses GB; Portuguese PT; Arabic SA; Urdu PK;
Hindi IN; Bengali BD; simplified Chinese CN.

`portraits-3.png` and `portraits-5.png` are miniature exports of the real contact
card renderer using five fictional contacts and drawn silhouette portraits.
Regenerate with `tests/support/terminal/run_display.py` and
`tests/support/terminal/render_portrait_choices.py`. These previews contain no
personal contacts or photographs. The captions below them show the selectable
counts, independently of the sample names in the miniature UI.

`framing-0.png` and `framing-1.png` are a matched pair of cartoon illustrations
generated with the built-in ImageGen tool, then exported at 640×360 with Sharp.
See `framing-prompts.md` for the complete prompt sequence. The illustrations are
examples; no camera is used on the Settings page.
