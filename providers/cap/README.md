# Cap Standalone

The Compose file reads `CAP_ADMIN_KEY` from the repository's root `.env` and
passes it to Cap as `ADMIN_KEY`.

From the repository root:

```sh
printf '\nCAP_ADMIN_KEY=%s\n' "$(openssl rand -hex 32)" >> .env
docker-compose --env-file .env -f providers/cap/docker-compose.yml up -d
```

Open <http://localhost:3069> and sign in with the value of `CAP_ADMIN_KEY`.

On installations with Docker's Compose plugin, the equivalent command is:

```sh
docker compose --env-file .env -f providers/cap/docker-compose.yml up -d
```

This Mac has Podman rather than a running Docker daemon. Start its VM and use
its Compose wrapper (which invokes the installed `docker-compose` command):

```sh
podman machine start
podman compose --env-file .env -f providers/cap/docker-compose.yml up -d
```

Run these commands from the repository root. The explicit `--env-file` is
required because Compose otherwise looks beside the Compose file and reads
`providers/cap/.env` instead.
