"""CEC is executed by TVControl; this profile adds no network operations."""
from zmala_terminal.linux.tv_plugins.api import TVDriver as BaseTVDriver


# @llr LLR-TERM-TV-033
class TVDriver(BaseTVDriver):
    def get_model(self):
        return None

    def get_capabilities(self):
        return set()
