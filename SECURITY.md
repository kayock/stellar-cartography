# Security

## Reporting

If you discover a vulnerability in Stellar Cartography, please open a private
report with the repository maintainers (or use GitHub private vulnerability
reporting if enabled). Do not file a public issue with exploit details.

## Threat model (summary)

- The UI is a local/LAN educational tool that talks to Stellarium Remote Control
  and optionally to a local TTS HTTPS endpoint.
- TTS URL allowlisting restricts outbound narration requests to configured hosts
  (`STELLAR_CARTOGRAPHY_TTS_HOSTS` plus loopback).
- Do not expose Cartography or Stellarium Remote Control to the public Internet
  without additional hardening (auth, TLS, firewall).
