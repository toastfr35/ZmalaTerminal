# Terminal requirements

Read the [Terminal and Server interface](interfaces/terminal-server.md) before
changing enrollment, management HTTP, SIP, media, or update reporting. Keep
the already released peer compatible and use local fixtures to verify
changes. Coordinate deliberate wire changes with the Server.

The [local update interface](interfaces/terminal-host-update.md) covers the
Updates settings page and its standalone or appliance updater.

The Terminal owns the Doorstop requirements under terminal/. Product parents
and shared-host ownership are identified in ownership.json. Run make requirements
to validate the requirement and test traceability.
