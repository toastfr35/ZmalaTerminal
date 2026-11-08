# Terminal and Server interface

This contract describes the wire behavior shared by ZmalaTerminal and
ZmalaServer, including the independently released 0.4.0 components. It is a
local reference for either checkout. The Server owns account, policy, and
persistence decisions. The Terminal owns device enrollment, local recovery,
rendering, and call/device execution. Runtime requirements and verification
traces remain in each repository's Doorstop documents.

## Enrollment and transport

- The administrator issues GET /api/terminal-bootstrap?id=ACCOUNT for an
  enrolled terminal account. The response includes server_url, device_id
  and device_token. GET /api/setup/server.pdf?id=ACCOUNT embeds the equivalent
  credentials in a private QR. Administrative credentials never belong on the
  Terminal.
- The Terminal server QR uses the compact ZMS1 format described below and
  carries those three bootstrap fields. The Terminal admits up
  to 4,096 characters, a server_url of at most 512 characters, a device_id
  matching [A-Za-z0-9_-]{1,80}, and a device_token matching
  [A-Za-z0-9_-]{20,256}. The URL is an HTTP or HTTPS origin with optional port
  and trailing slash. User information, non-root paths, query strings and
  fragments are invalid. The Terminal validates the first configuration
  before committing the enrollment. The account ID, device serial, device
  bearer token and SIP password have different roles.
- For a Terminal account, the administrator-only server PDF download encodes
  `ZMS1:` followed by [RFC 9285 Base45](https://www.rfc-editor.org/rfc/rfc9285.html)
  text, using QR error correction M. Preserve all spaces in the Base45 text.
  App account PDFs use the separate App enrollment contract.
- The decoded compact bytes are one flag byte, a two-byte big-endian authority
  length, the ASCII URL authority (host and optional port, including IPv6
  brackets if present), the device ID, and the token. Flag bit 0 selects HTTPS
  (clear means HTTP). Bit 1 means the ID is 16 raw UUID bytes, restored as
  `ZM-` plus the lowercase hyphenated UUID. When clear, read one ID length
  byte followed by that many ASCII ID bytes. Bit 2 means the rest of the bytes
  are a raw token to restore as unpadded Base64URL. When clear, read the token
  as literal ASCII. Reject reserved flag bits, invalid Base45 and invalid
  field lengths. Apply the enrollment field validation described above.
- Local Wi-Fi setup accepts the escaped WIFI QR format or the Server's
  FAMILY-WIFI:1: compact format. The Server generates Wi-Fi QR PDFs with POST /api/setup/wifi.pdf (4,096-byte
  JSON body with ssid, security, password and hidden). The compact format
  carries base64url-encoded
  bytes without padding. Byte 0 uses bit 0 for WPA and bit 1 for a hidden SSID.
  Byte 1 is the SSID byte count. The UTF-8 SSID and password follow. WPA accepts
  printable passwords of 8–63 characters or 64 hex digits. An open network has
  an empty password. The Wi-Fi QR does not enroll the device.
- Send Authorization: Bearer DEVICE_TOKEN to the enrolled origin. JSON writes
  use Content-Type: application/json. The Server derives the enrolled account
  from the credential. Terminal identity is never chosen by a request-body
  field. The Terminal does not follow redirects for device API requests.
  Secure-relay deployments require HTTPS with valid local trust. Use the
  configured Host and matching Origin when an Origin header is present.
- JSON device replies default to application/json and Cache-Control: no-store.
  Error replies have an error string. Typical results are 400 for malformed
  input, 401 for missing or invalid device credentials, 403 for disallowed
  origin/transport/account/action, 404 for unavailable resources, 409 for a
  state conflict, 413 for a bounded body violation and 503 while restoring
  or when the update service is unavailable. Successful writes must be read
  according to the individual operation's response. Avoid parsing error text
  as a protocol field.
- The ordinary Terminal HTTP request timeout is four seconds. Its response
  cap is 2 MiB, except authenticated /photos/...gif reads, capped at 16 MiB.
  The updater separately caps enrolled-origin JSON replies at 128 KiB and
  disables redirects and proxies for that transport.

## Configuration, settings and presence

| Terminal operation | Request | Server response and invariants |
| --- | --- | --- |
| Fetch configuration | `GET /api/config` | 200 with a full Terminal configuration for the bearer account. |
| Poll with a known revision | `GET /api/config?delta=1&version=N` | 200 with a full configuration or {configuration_version, live}. The Server only emits a live-only response for the exact current revision in LAN mode. |
| Write settings | `POST /api/device/settings` with {settings, expected}, at most 4,096 bytes | 200 with a full current configuration after persistence. The maps must contain the same nonempty key set. A differing value with a stale expectation yields 409. Repeating a write whose values already match does not create a new revision. |
| Check permission before dialing | `GET /api/contacts/ACCOUNT/availability` | 200 with {id, online, presence, can_call, ring_timeout}. A disallowed account appears offline and cannot be dialed. The Terminal requires the returned ID, online=true and can_call=true. |

- Full configuration uses integer schema_version=1, a matching device_id and
  a positive integer configuration_version. It contains display_name,
  auto_answer_seconds in the range 5–600, a call_auth_key, a SIP object with
  username, password, domain and proxy, and contacts. The Server additionally
  emits account_type="terminal", call_photo_sharing, optional secure_calls,
  mutable setting values and administrative profile fields. Keep passwords
  and the proof key private.
- Full Terminal configuration includes account_photo, the authenticated
  account's own portrait. It is empty when no portrait is assigned, or a
  same-origin path matching /photos/[a-f0-9]+\.(png|jpg|gif), fetched using the
  existing authenticated photo route. Older Terminals ignore the added field.
  The live-only response keeps the cached portrait for the matching revision.
- Contacts are an array of at most 40 unique IDs matching
  [a-z][a-z0-9_-]{0,30}. Each has a nonempty name of at most 80 characters,
  sip_uri equal to sip:ID@SIP_DOMAIN, and Boolean can_call, can_receive and
  auto_answer. Auto-answer requires can_receive. Optional photo is empty or
  a same-origin path matching /photos/[a-f0-9]+\.(png|jpg|gif). An omitted
  online value is accepted. Presence uses available for an active SIP
  registration, push for a reachable App without an active registration,
  or offline. For compatibility online is true for available and push.
- A live-only response includes live.contacts with id, online and presence,
  live.callbacks and live.developer_access. It applies only to the matching
  saved revision and does not create new contacts or grant permissions.
  Missing entries are offline. The Terminal rejects older revisions and
  responses for another enrollment. It polls nominally every two seconds
  without overlapping fetches and expires live reachability after about six
  seconds. Offline cache excludes live presence, callbacks and developer
  tunnel credentials. Secure-relay responses remain full snapshots so
  same-revision TURN credential renewal still arrives.
- Settings writable by the Terminal are language, auto_answer,
  auto_answer_seconds, auto_framing, c20_speaker_volume, ringtone_volume,
  action_sound_volume, carousel_portraits, tv_idle_seconds, ringtone,
  usb_power, tv_profile and tv_test_results.
  The shared language catalogue supplies allowed language codes. Volume
  values are integer 0–100, portrait counts are 3 or 5, and TV idle delay
  is 0, 30, 60, 120, 300, 600, 1200 or 1800 seconds. Zero means disabled.
  Video resolutions are 360p, 480p, 720p or 1080p and frame rates are
  10, 15, 20, 25 or 30. These video fields are profile inputs, outside the
  device-write allowlist. The audio profile is normal or speech.
- USB power is always_on, camera or camera_and_dock. The Server defaults to
  always_on for existing profiles. On supported Pi 4 terminals, the two
  automatic modes switch the shared USB supply after 60 seconds idle. Camera
  and dock mode retains or restores power below 25% battery or when the
  reading is unavailable.
- The TV profile is samsung, cec or an empty value for a local selection.
  TV test results are null or a completed summary containing device_id,
  profile, power and source outcomes (passed, failed or skipped) and
  power_attempts and source_attempts as nonnegative integers. The Server
  binds results to the enrolled device and current model. A model change
  clears them. Results are for reporting. Physical TV identity, pairing
  details and capability verification stay on the Terminal.
- ring_timeout is in seconds. The default is 60. A target with enabled
  auto-answer gets max(60, auto_answer_seconds + 30). The Terminal accepts
  60–660 and uses 60 if the field is missing or invalid.

## Callbacks, assets and diagnostics

| Terminal operation | Request | Success response and scope |
| --- | --- | --- |
| Request callback | `POST /api/callbacks` with {to}, at most 4,096 bytes | 201 with the callback object. The Server checks current permissions and reuses an existing pending request for the same direction. |
| Cancel own callback | `POST /api/callbacks/ID/cancel` with {} | 200 {ok:true}. An unknown or other-account request is 404. |
| Read portrait | `GET /photos/HASH.png`, `.jpg` or `.gif` | 200 with corresponding image media type, or 404. Hash-named assets are immutable and privately cacheable. |
| Read ringtone | `GET /api/ringtones/nokia.wav` or /api/ringtones/SHA256.wav | 200 audio/wav, or 404 for missing catalogue content. Paths are same-origin. |
| Read call-photo state | `GET /api/call/photo?call_id=ID` | 200 {revision, sharing, sender, lease_ms, remaining_ms}. |
| Read the active call photo | `GET /api/call/photo?call_id=ID&image=1&revision=N` | 200 image/jpeg for the current shared revision, otherwise 404. |
| Report device status | `POST /api/status` with a JSON object of up to 32,000 bytes | 200 {ok:true}. Telemetry is separate from account settings. |
| Claim maintenance command | `POST /api/console/next` with {} | 200 {job:null} or {job:{id,command,shell,timeout_seconds,lease}}. |
| Return command result | `POST /api/console/result/ID` with {lease,status,exit_code,stdout,stderr,truncated}, up to 400,000 bytes | 200 {ok:true} after persistence. A retry with the same valid lease is acknowledged without executing the command again. |

- The Terminal admits at most 80 pending callbacks involving this account.
  Each has a 36-character lower-case hexadecimal/hyphen ID, from and to
  account IDs, status="pending" and Boolean ready. The Server derives ready
  from availability of both accounts and controls deadlines. Extra timestamp
  and display fields are informational.
- A ringtone catalogue contains 1–65 entries {id,name,url}, including nokia,
  and the selected ringtone must exist. Custom WAVs have the advertised SHA-256
  as their ID, use mono 16 kHz signed 16-bit PCM, and last at most 30 seconds.
  The built-in Nokia sound remains available locally.
- The Terminal is a call-photo receiver only. The bearer account must be an
  authenticated participant in the connected SIP dialog, which must include
  an App account. Percent-encode the SIP Call-ID in the query, bounded to
  256 characters by the Server. The sender controls the 12-second lease.
  The Terminal checks roughly once per second, reuses pixels for an unchanged
  revision, caps its display lifetime at 12 seconds and clears the photo when
  sharing ends or the call closes. Image size is capped at 2 MiB.
- Status can carry state, registered, configuration_version and camera,
  microphone, speaker, ringer and audio-profile strings. Peripheral fields
  include remote_status, nullable battery 0–100 and charging flag, and
  camera_status with nullable connected/powered flags. Optional devices and
  media objects hold bounded device names, audio/video rate, loss, jitter and
  resolution measurements, and codec counters. The Server whitelists typed
  fields, timestamps observations and preserves independent updater status.
- Maintenance jobs are account/device-bound. The Server persists a claim
  before responding and allows a 5–120 second execution timeout. Terminal
  result status is completed, failed, timed_out or cancelled, exit_code is
  integer or null and stdout/stderr total at most 65,536 UTF-8 bytes. A lost
  result acknowledgment triggers a result retry, never command re-execution.
  Use the Pi shell configured for the target. Jobs follow the device serial
  when the Server reassigns it to another account. A replacement serial cannot
  claim the old device’s work.
- A full HTTPS configuration may include developer_access. Null means
  disabled. Enabled data includes terminal_id (the device serial here),
  session_id, host, port=2222, remote_port=22001, host_key and password.
  The enrolled HTTPS hostname and serial must match, and the SSH host key
  is pinned. Treat this data as transient credentials. It does not change
  ordinary device access, SIP permissions or application enrollment.

## SIP and media

- The Terminal registers the supplied SIP identity with SIP Digest through
  the configured proxy. A REGISTER carries the same authenticated account in
  From and To. The Server bounds registrations to 600 seconds, removes a
  zero-expiry registration, and binds traffic to the registered transport
  flow. SIP OPTIONS probes inform reachability independently of configuration
  changes. The Terminal routes SIP using the supplied domain and proxy.
- LAN proxy URI is sip:HOST:PORT;transport=udp. LAN media uses Server RTP/RTCP
  relay. Secure policy mode tls-relay uses sip:HOST:PORT;transport=tls,
  with separate TLS endpoint turn_server="HOST:PORT", turn_username,
  turn_password, turn_realm and integer expires in Unix seconds. Use the
  literal sip URI with transport=tls emitted by the Server. The Terminal
  validates certificate chains and names against local trust, requires
  SRTP and forced ICE relay with TURN over TLS, and does not fall back to
  plaintext. Secure SDP carries ICE credentials and valid SRTP crypto
  for each active audio/video section. The Server emits TURN credentials in
  hourly buckets, expiring eight hours from the start of each bucket. The
  Terminal renews credential-only changes while idle without opening media.
- The Server authorizes and relays INVITE and dialog requests. Call and SDP
  state stays on the authenticated peer flow. An in-dialog INVITE requires
  an SDP offer, and concurrent negotiations may return SIP 491. An
  inadmissible SDP or missing required secure media can return SIP 488.
  The Pi media stack uses H.264 video. Transport admission does not imply
  physical camera, microphone, speaker or remote performance.
- For incoming calls the Server overwrites X-Family-Auth with the lowercase
  hex HMAC-SHA256 of UTF-8 "CALL_ID:CALLER_ACCOUNT", keyed by the receiving
  Terminal's call_auth_key. The Terminal validates the proof and its
  configured contact/domain permissions before offering the call.
- SIP MESSAGE accepts text/plain or message/cpim and a nonempty body bounded
  by the Server to 16,384 JavaScript string characters. The Server emits
  X-Zmala-Message-Id and X-Family-Auth. The latter is the lowercase hex
  HMAC-SHA256 of UTF-8 "message:MESSAGE_ID:FROM_ACCOUNT" with the receiving
  Terminal's proof key. The Terminal checks domain, receive permission, proof
  and replay, and caps the message ID at 256 characters. Do not expose or
  forward the caller's original authorization headers or a caller-supplied
  proof. Server-generated callback notifications also use this proof format.

## Terminal update exchange

- GET /api/terminal-updates/manifest returns 200 {manifest:null} or the
  unmodified signed Terminal manifest envelope. The Server refreshes the public feed at most every five minutes after a
  success and backs off one minute after an error. It does not authorize or
  sign the payload. The Terminal can use the
  public ZmalaTerminal feed when unenrolled or when an older Server returns
  404. Bearer credentials stay on the enrolled origin.
- Envelope fields are payload, key_id and Base64 signature. The Terminal
  verifies Ed25519 over canonical UTF-8 JSON using sorted keys and compact
  separators. It requires schema 1, exact compatibility, a newer integer
  sequence, SemVer, a 40-hex source commit and the exact versioned HTTPS
  GitHub update-package path /toastfr35/ZmalaTerminal/releases/download/vVERSION/ZmalaTerminal-Update.tar.gz.
  package has url, size and sha256. The 0.4.0 compatibility tuple is
  architecture=aarch64, os=trixie, sdk=5.3.105, updater=1, data=1 and host=3.
  Manifest cap is 65,536 bytes and compressed package cap is 256 MiB.
  App updates do not replace the root-owned stable updater or host policy.
- POST /api/terminal-updates/status takes up to 4,096 bytes with phase and
  optional installed, available and error. It returns 200 {ok:true}.
  Phase is idle, request, updating, checking, rollback or recovery_failed.
  Version fields are dotted numeric strings up to 32 characters and an error
  code is up to 48 lower-case letters/underscores. The Server treats a recent
  updating, checking, rollback or recovery_failed report as a call-availability
  fence for up to 60 seconds. Update status does not modify configuration.

## Compatible changes and local verification

Keep wire shapes, credential scope, revision semantics and authentication
compatible with the already released peer. Add optional fields with safe
defaults where possible. Deploy Server support before a Terminal starts
relying on a new field, then verify the previous and current peer behavior.
Coordinate breaking changes and migration or fallback before releasing
either side. Never reset a revision or weaken proof/TLS validation to bridge
an incompatibility. Keep secret-free fixtures with the code that owns them.

| Repository | Requirement and test entry points |
| --- | --- |
| ZmalaTerminal | HLR-TERM-COM-001/002/009, HLR-TERM-SETUP-020/021, LLR-TERM-COM-003 through 008 and LLR-TERM-COM-010, LLR-TERM-CALL-011, LLR-TERM-HISTORY-019/020, LLR-TERM-MAINT-024/034. Local LLTs include test_configuration.py, test_provisioning.py, test_callbacks.py, test_call_photo.py, test_secure_calls.py, test_update_server.py and test_update_package.py. Use make requirements and make test-llt. The provisioning display HLT runs with the pinned isolated Server HTTP fixture described by Verify. |
| ZmalaServer | LLR-SRV-AUTH-019 through 022, LLR-SRV-ENROLL-005, LLR-SRV-CONFIG-021/022/024, LLR-SRV-PRESENCE-005, LLR-SRV-CALL-005/008, LLR-SRV-MEDIA-015/016, LLR-SRV-MESSAGE-004, LLR-SRV-MAINT-014/016/018/022. Local tests include setup-payload.test.js, secure-calls.test.js, terminal-updates.test.js, device-settings.test.js, callbacks.test.js, console.test.js and call-photo-http.test.js. Use make requirements, make test-llt and make test-hlt. |

Use the pinned Zmala network lab for cross-component LAN/NAT and secure-relay
scenarios. Treat skipped, fixture-only and physical qualification results
separately.
