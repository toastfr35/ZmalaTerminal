"""Built-in TV drivers. Each model family owns a separate directory."""
from importlib import import_module
from dataclasses import dataclass


@dataclass(frozen=True)
class DriverInfo:
    module: str
    brand: str
    model_family: str


# Only bundled plugins can be selected; configuration cannot import arbitrary code.
DRIVERS = {
    'samsung': DriverInfo('zmala_terminal.linux.tv_plugins.samsung.driver', 'Samsung', 'Smart TV'),
    'cec': DriverInfo('zmala_terminal.linux.tv_plugins.cec.driver', 'Generic', 'HDMI-CEC'),
}


# @llr LLR-TERM-TV-033
def load_driver(name, config):
    """Create an isolated operation instance using the seven-method API."""
    try:
        info = DRIVERS[name]
    except (KeyError, TypeError):
        raise ValueError('Unknown TV driver') from None
    return import_module(info.module).TVDriver(config)
