"""Shared USB supply policy, also used by the Windows acceptance fixture."""

USB_POWER_MODES = ('always_on', 'camera', 'camera_and_dock')
IDLE_SECONDS = 60


# @llr LLR-TERM-POWER-013
def should_power_off(now, last_use, active, battery, mode):
    if active or now - last_use < IDLE_SECONDS:
        return False
    return mode == 'camera' or (mode == 'camera_and_dock' and type(battery) is int and 25 <= battery <= 100)
