# Terminal and local update service

Settings and its privileged update owner exchange bounded JSON records.
Standalone and appliance hosts have one updater owner each.

- `/run/zmalacall-updater/offer.json` is a root-owned regular file. Schema `1`
  replies include `request` and `state` (`available`, `current`, `error`,
  `unavailable` or `queued`). `available` also supplies a three-part `version`
  and `release` with 64 lowercase hex characters. Offer only a verified release
  that the owner can install. Settings accepts only its current request ID.
- `/run/zmalacall/update-command.json` is written atomically by the Terminal
  service. It contains `schema`, `request` (32 lowercase hex characters),
  monotonic `issued` and `action` (`check` or `apply`). `apply` includes the exact
  `release` from the offer. Validate file type, UID, mode, size, freshness and
  identity. A command never supplies a path, URL or trust root. `queued` means
  the owner accepted the request.
- Activation uses the existing root-owned `state.json` and Terminal-owned
  `update.json` lease. A fresh root request may include `immediate: true` for a
  manual offer. This waives the inactivity timer. All other call, setup, worker,
  peripheral and input guards remain in force. The owner validates the fresh
  lease and process identity before activation. Old requests omit this field.
