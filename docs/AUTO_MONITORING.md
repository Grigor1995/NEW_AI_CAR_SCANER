# Automatic monitoring — eligibility policy only

The pure eligibility function distinguishes Scheduled from Deferred based on consent, device presence, ignition and OS background eligibility. It does not execute or schedule a scan. The UI explicitly says no unattended scan has been performed. Planned daily default, time-zone/DST handling, weekly/custom/quiet-hour settings, idempotent jobs, missed/failed/completed states and actual gateway orchestration are not implemented.

Never wake ECUs unnecessarily or perform unattended writes. iOS/Android background restrictions require platform-aware deferral or a supported vehicle gateway. No disconnected/off-ignition scan may be called successful.
