# Local Hosting Guidance

- ALFRED is a local or LAN-hosted application in this repository.
- Do not add cloud deployment wiring, cloud credentials, or cloud-specific
  runtime templates without an explicit new decision.
- Keep runtime secrets in untracked local environment files such as
  `config/local.env`.
