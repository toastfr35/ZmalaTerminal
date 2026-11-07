"""Deterministic monotonic clock for portable process tests."""

class Clock:
    def __init__(self):
        self.now = 0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
