# Terminal and local update service

Settings and its privileged update owner exchange bounded JSON records.
Standalone and appliance hosts have one updater owner each.

- `/run/zmalacall-updater/offer.json` is a root-owned regular file. Schema `1`
  replies include `request` and `state` (`available`, `current`, `error`,
  `unavailable` or `queued`). `available` also supplies a three-part `version`
  and `release` with 64 lowercase hex characters. Offer only a verified release
  that the owner can install. Settings accepts only its current request ID.
- On an appliance, `version` identifies the complete OTA release. The running
  release is provided by the image in `/usr/lib/zmala/system-release.json`
  (`schema: 1`, `role: "terminal"`, `version`). The dated form is
  `YYYYMMDD.0.N` with a positive revision `N`, and can advance when either the
  OS or the app changes. Settings displays the ISO date and shows the revision
  for releases after the first of the day. Existing numeric release versions
  remain displayable. Installer-based Terminals use the app version.
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
- During the appliance bundle transfer, the root-owned `state.json` can include
  `download_percent`, an integer from 0 to 100, with phase `updating`. The
  display uses it for transfer progress and falls back to the normal update
  message when it is absent. The field has no effect on the activation lease.
