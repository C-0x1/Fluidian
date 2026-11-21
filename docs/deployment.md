<p align="right"><a href="../README.md"><img src="assets/wordmark.svg" height="28" alt="Fluidian"></a></p>

# Deployment

A Fluidian deployment is one engine process that starts one app process. Both are yours to run wherever you run services.

## Production mode

```bash
export OPENAI_API_KEY=sk-...                 # optional
export FLUIDIAN_ALLOWED_HOSTS=app.example.com
./fluidian run --production --host 127.0.0.1 --port 8787 -- python3 app.py
```

`--production` disables the developer tools and detailed errors and enables caching of static assets. Read the [security checklist](security.md#production-checklist) before exposing the port.

## Behind a reverse proxy

The engine serves HTTP and one long-lived server-sent-events stream per tab. The proxy must not buffer that stream.

```nginx
server {
    listen 443 ssl;
    server_name app.example.com;

    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
    }

    location /_fluidian/events {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 1h;
    }
}
```

The engine also sends `X-Accel-Buffering: no` on the stream, which nginx honours without extra configuration. Add your authentication at this layer.

## systemd

```ini
# /etc/systemd/system/fluidian.service
[Unit]
Description=Fluidian
After=network.target

[Service]
User=fluidian
WorkingDirectory=/opt/fluidian
EnvironmentFile=/etc/fluidian.env
ExecStart=/opt/fluidian/fluidian run --production -- python3 /opt/app/app.py
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/fluidian/.fluidian

[Install]
WantedBy=multi-user.target
```

## Containers

```dockerfile
FROM python:3.12-slim
WORKDIR /opt/fluidian
COPY . .
# add your app's language runtime here if it is not Python
COPY app/ /opt/app/
ENV FLUIDIAN_HOST=0.0.0.0 FLUIDIAN_DATA_DIR=/var/lib/fluidian
EXPOSE 8787
USER nobody
CMD ["./fluidian", "run", "--production", "--", "python3", "/opt/app/app.py"]
```

Set `FLUIDIAN_ALLOWED_HOSTS` to the name people use to reach the container; binding to `0.0.0.0` without it accepts any `Host`.

## Installable app, embedding and native shells

- **HTTPS makes the app installable.** Browsers offer installation and run the service worker only on HTTPS (or `localhost`). With the proxy above terminating TLS, people can add the app to a phone's home screen or install it on a desktop; nothing else is needed.
- **Embedding needs an allow-list.** To show the app inside another site with `<fluidian-app>`, set `FLUIDIAN_EMBED_ORIGINS` to the sites that may frame it.
- **Native shells point at your deployment.** `./fluidian package all --name "My App" --url https://app.example.com` writes iOS, Android and desktop projects that open that address.

All three are described in [Cross-platform](cross-platform.md).

## State and scaling

- **Session state lives in the app process's memory.** A restart starts every session fresh. Persist what matters in your own store, keyed by your own identifiers.
- **One engine serves one app instance.** To scale out, run several pairs behind a load balancer with **session affinity**, because a tab's event stream and its requests must reach the same engine.
- **The kernel's cache and budgets are per process.** Size budgets per instance.
- **AI calls run on worker threads** and do not block other sessions. A handler that blocks inside your app blocks that app process's other sessions, since handlers run one at a time.

## Health and observability

| Endpoint or file | Use |
| --- | --- |
| `GET /healthz` | Liveness; returns `{"ok": true}` |
| `FLUIDIAN_AUDIT_PATH` | One JSON line per AI call |
| `./fluidian ai perf.telemetry` | Call counts, error counts and latency percentiles per capability |
| stderr | Engine log and the app's stderr, relayed with a prefix |

## Running without a provider

Leave the key unset, or set `FLUIDIAN_OFFLINE=1`. Every capability is then answered by the Reflex engine with no outbound connection, which suits air-gapped installations, kiosks and compliance-restricted environments.
