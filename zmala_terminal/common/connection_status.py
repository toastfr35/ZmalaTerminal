"""Presentation-only connection history, driven by monotonic observations."""
from dataclasses import dataclass


# @llr LLR-TERM-NET-005
@dataclass
class ConnectionStatus:
    connected_once: bool = False
    disconnected_at: float | None = None

    def observe(self, now, connected, wifi):
        if connected:
            self.connected_once = True
            self.disconnected_at = None
            return 'connection_connected', 'green'
        if self.disconnected_at is None:
            self.disconnected_at = now
        color = 'red' if now - self.disconnected_at >= 60 else 'amber'
        if wifi is False:
            return 'connection_wifi', color
        if color == 'red':
            return 'connection_retrying', color
        return ('connection_reconnecting' if self.connected_once else 'connection_connecting'), color
