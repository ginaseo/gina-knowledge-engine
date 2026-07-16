# Vault Sync (Syncthing)

`HermesVault/` can be mirrored between machines (e.g. a local workstation and a remote
deployment host) with [Syncthing](https://syncthing.net), so wiki edits and freshly
ingested notes stay in sync regardless of which side ran the pipeline.

## Setup

1. Install Syncthing on each machine that should hold a copy of `HermesVault/`
2. On Linux, run it as a `systemd --user` service (`syncthing.service`) with
   `loginctl enable-linger <user>` so it starts without an interactive login
3. Exchange device IDs between the machines (Syncthing GUI, or `syncthing --device-id`
   on the CLI) and add each as a trusted device on the other
4. Share a folder pointing at each machine's local `HermesVault/` path, using the same
   folder ID (e.g. `hermesvault`) on both sides

## Gotchas

- Each side needs a `.stfolder` marker file **inside** `HermesVault/` itself (not the
  repo root) — Syncthing refuses to scan a folder without one, and creates it in the
  wrong place if the folder path is misconfigured
- Windows is case-insensitive, Linux isn't. Entity/wiki pages that differ only by case
  (`Architecture.md` vs `architecture.md`) collide on the Windows side.
  `EntityProcessor` dedups stub creation case-insensitively to prevent *new*
  duplicates, but pre-existing ones must be cleaned up by hand — keep whichever file
  has real content, delete the stub
- Connection details (host, port, credentials) are environment-specific — configure
  them per deployment, not in source control
