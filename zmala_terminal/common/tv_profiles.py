"""Local TV profile selection and bundled brand artwork, without device I/O."""
import json
from pathlib import Path

from zmala_terminal.linux.tv_plugins import DRIVERS
from zmala_terminal.linux.tv_plugins.samsung.driver import save_config


BRANDS = ('Samsung', 'Sony', 'LG', 'Toshiba', 'Panasonic', 'Philips', 'Sharp', 'TCL', 'Hisense', 'Vizio')
ASSETS = Path(__file__).parent / 'assets' / 'tv-brands'


def brand_artwork(brand):
    name = next((item.lower() for item in BRANDS if item.casefold() == brand.casefold()), None)
    return ASSETS / (name + '.png') if name else Path(__file__).parent / 'assets/settings/tv_setup.png'


# @llr LLR-TERM-TV-019, LLR-TERM-TV-033
def read_profile(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        name = value.get('driver') if isinstance(value, dict) else None
        return name if isinstance(name, str) and name in DRIVERS else 'samsung'
    except (OSError, ValueError):
        return 'samsung'  # Existing installations used this fallback implicitly.


def write_profile(path, name):
    if name not in DRIVERS:
        raise ValueError('Unknown TV driver')
    save_config(path, {'version': 1, 'driver': name})
