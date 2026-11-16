# Local Bluetooth remote reset

The application persists an explicit factory-reset request in
`/var/lib/zmalacall/remote-reset.json` before clearing its setup state. Schema 1
contains `request`, a fresh 32-character lowercase hexadecimal identifier. The
file is private to the configured application user. It contains no device path
or command to execute.

The root-owned pairing service accepts only a bounded regular file owned by the
`ZMALA_USER` from `/etc/zmalacall/terminal.conf`, beneath that user's fixed data
directory. It rejects symlinks and unsafe permissions. It selects the current
Presenter from its own bond identity and BlueZ state, journals that selection in
`/var/lib/zmalacall-pairing/reset.json`, then uses BlueZ `RemoveDevice` and removes
its saved bond identity. Other Bluetooth devices are unaffected.

Interrupted removal retries the journaled target before pairing can continue.
Only completed removal produces `reset_request` in the root-owned pairing status
file. The application waits for that matching acknowledgement before removing
its request and accepting normal pairing status. Duplicate completed requests
do not remove a subsequently paired remote. Older status producers without the
acknowledgement leave reset pending; a system OTA must install both components.

This interface does not change server or Android messages. The remote itself
must still be placed into pairing mode using its Bluetooth button.
