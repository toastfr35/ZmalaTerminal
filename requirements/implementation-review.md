# Terminal requirements review

Reviewed against `main` at `80c4309` on 9 November 2026, component 0.4.18,
sequence 131. Tracked by GitHub issue #42.

The review starts from the Terminal-owned requirements, the two local interface
contracts and ownership.json. The baseline contains 43 high-level and 143
low-level Terminal requirements, with 15 imported product parents. The requirement
validator maps 167 source files, finds code anchors for every low-level requirement
and finds direct test plans for every Terminal requirement.

These trace links establish coverage of the inventory. Behavioral conclusions
also require source inspection and executed tests. Physical performance and
installed appliance behavior require their specified hardware checks.

## Reconciled differences

| Requirement | Difference | Implementation evidence and resolution |
| --- | --- | --- |
| LLR-TERM-CONFIG-021 | TV return omitted 1800 seconds and stated a 30-second default. | `local_settings.py`, `config_validation.py`, `test_idle_return.py` and LLR-TERM-TV-029 use a 30-minute default and retain explicit saved choices. Correct the settings requirement. |
| LLR-TERM-CONFIG-021 | The editor choices omitted USB power. | `SettingsDraft.open`, `SettingsDraft.move` and `usb_policy.py` expose Always on, Camera only and Camera and dock, with wrapping and an Always on default. Include these choices and their verification steps. |
| HLR-TERM-POWER-009 | Any user activity was required to wake USB. | `input_control.py`, `management.py`, `usb_power.py`, LLR-TERM-POWER-013/014 and the peripheral tests preserve USB sleep during navigation. Require wake for activities that need USB media. Review the six child requirements and refresh only their links to this parent. |
| LLR-TERM-POWER-010 | Unqualified C10/C20-only wording also appeared to prohibit HDMI button feedback. | The native call route remains C10/C20-only. `action_sounds.py` and LLR-TERM-AUDIO-010 route button feedback over HDMI. Scope the device restriction to calls and reference the separate feedback requirement. |

The existing behavior provides the baseline for these corrections. IDs and
ownership remain stable. This change is limited to requirements and their
verification guidance.

## Review coverage

The normative text was reviewed across startup, communication, configuration,
navigation, calls, history, UI, audio, video, networking, setup, remotes, TV,
power and maintenance. Particular attention went to recent settings and peripheral
changes, numeric defaults, supported choices and contradictions between parent
and child requirements. The local interface contracts were checked for the
existing enrollment, settings, media and updater constraints.

The automated requirement check passes. All 656 discovered low-level Python tests
pass under Linux. An initial run on Windows-backed temporary storage failed eight
permission-sensitive cases. Repeating the suite with Linux temporary storage under
the workspace tmp directory passed all cases.

The discovered high-level Python suite also passes under a virtual display,
with 35 tests run and three explicit skips. The skipped checks require a physical
Terminal SSH alias, an installed Pi after reboot, or root network namespaces for
firewall ingress. They remain qualification gaps for this local run.

Physical C10/C20 audio and camera behavior, Presenter reports, TV picture/routing,
USB hub switching and Pi thermal behavior were not exercised on hardware in this
review. The native SDK and separately launched display scenarios require the
repository's full Verify workflow and hardware qualification plans. Existing
Samsung wake/picture and TV restoration investigations remain tracked in issues
#1 and #2. Passing fixture tests does not resolve those physical observations.
