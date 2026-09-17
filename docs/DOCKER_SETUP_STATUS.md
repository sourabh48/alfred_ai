# Docker setup status

Checked 17 September 2026 after the host restarted.

Docker is optional for ALFRED. The [native Windows application](NATIVE_WINDOWS.md)
runs Django with Waitress, Huey and SQLite without Docker or WSL. The Compose configuration provides a
separate PostgreSQL, Redis, web, Celery worker and beat runtime. Those services
still require operational verification.

Completed during the requested Docker setup:

- Installed Docker Desktop 4.91.0 for the current Windows user.
- Verified the installer against the published SHA-256 checksum and its valid
  Docker publisher signature.
- Confirmed Docker CLI 29.8.0 and Compose 5.5.1 are available.
- Passed `docker compose --env-file config/local.env -f docker-compose.local.yml config --quiet`.
- Installed WSL 2.7.14.0. The elevated feature-setup script did not leave a
  completion report before the host restarted, so full Windows feature
  readiness has not been independently accepted.

Windows still reports `VirtualizationFirmwareEnabled: false` and
`HypervisorPresent: false` on this AMD Ryzen/Gigabyte B550 AORUS PRO AC host.
The Linux engine, ALFRED containers and PostgreSQL recovery checks have not
passed. Evidence: `artifacts/ops/docker_desktop_setup.json`.

If continuing with Docker, enable **SVM Mode** in the BIOS. Gigabyte's B550/A520
guide places it under **Advanced Mode → Tweaker → Advanced CPU Settings**;
menu names can vary by BIOS revision. Enter BIOS with Delete during startup,
enable SVM, and save with F10. Then open Docker Desktop and verify that the
Linux engine starts before starting ALFRED's Compose stack.

Sources: [Docker Windows requirements](https://docs.docker.com/desktop/setup/install/windows-install/)
and [Gigabyte B550/A520 BIOS guide](https://www.gigabyte.com/FileUpload/Global/WebPage/954/images/B550_A520%20BIOS_e_Web.pdf).

The native application was restarted and its readiness and login routes
returned HTTP 200 at `http://127.0.0.1:8000/`. Starting the Compose web service
on port 8000 would conflict with that native server; choose a separate local
port or stop the native server when switching runtimes. Their databases are
separate, and starting Compose does not migrate the existing SQLite data.
