+++
title = "A $22/Year VPS Running Three Self-Hosted Services"
date = 2026-05-02T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "Running Obsidian LiveSync, Matrix Synapse, and Calibre-Web on a $22/year VPS — nginx reverse proxy, Docker Compose, Cloudflare tunnels, and what actually fits in 2.9GB RAM."
tags = ["infra", "self-hosting", "vps", "docker", "nginx"]
+++

I wanted three things: a private Obsidian sync server, a Matrix chat instance for personal use, and a self-hosted book library. The obvious path is a cheap VPS, a few Docker containers, and nginx as a reverse proxy in front of everything.

The whole stack runs on a budget VPS -- 1 vCPU, 2.9GB RAM, 30GB disk, $22/year. All three services are running with room to spare.

## Initial Setup

**SSH key auth first, password auth off:**

```bash
# local: generate key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"
# paste ~/.ssh/id_ed25519.pub into your provider's SSH key field

# on the server: disable password login
sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
```

Test key login before disabling password auth. If you lock yourself out, you're recovering via the provider's console.

**Swap -- critical on 3GB RAM:**

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Without this, CouchDB and Conduit together will occasionally OOM under load.

**Firewall:**

```bash
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3478        # TURN (UDP+TCP)
ufw allow 5349        # TURN TLS
ufw allow 49152:65535/udp  # TURN relay range
ufw enable
```

The TURN ports are for Matrix voice/video -- skip them if you're not setting up coturn.

**Docker:**

```bash
curl -fsSL https://get.docker.com | sh
```

## Service 1: Obsidian LiveSync (CouchDB)

LiveSync uses CouchDB as the sync backend. Install it directly on the host rather than in Docker -- it's simpler to configure and easier to troubleshoot.

```bash
apt install -y couchdb
```

The installer prompts for admin credentials. Set them and keep them somewhere safe.

Configure `/opt/couchdb/etc/local.ini`:

```ini
[chttpd]
bind_address = 127.0.0.1

[couch_httpd_auth]
require_valid_user = true

[httpd]
enable_cors = true

[cors]
origins = app://obsidian.md, capacitor://localhost, http://localhost
credentials = true
headers = accept, authorization, content-type, origin, referer
methods = GET, PUT, POST, HEAD, DELETE
max_age = 3600
```

```bash
systemctl restart couchdb
curl -X PUT http://admin:PASSWORD@localhost:5984/obsidian-sync
```

nginx config:

```nginx
server {
    listen 80;
    server_name sync.your.domain;
    location / {
        proxy_pass http://127.0.0.1:5984;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Get a cert: `certbot --nginx -d sync.your.domain`

In Obsidian: install the LiveSync community plugin, set the CouchDB URI to your domain, enter credentials, set a database name and an E2E passphrase. Enable sync. The passphrase encrypts vault content before it leaves your device -- CouchDB never sees plaintext.

## Service 2: Private Matrix Chat (Conduit + coturn)

Conduit is a Matrix homeserver written in Rust -- much lighter than Synapse, which would be too heavy for 3GB RAM. I run it with federation disabled -- this is a personal instance, not connected to the public Matrix network.

`/opt/conduit/docker-compose.yml`:

```yaml
services:
  conduit:
    image: matrixconduit/matrix-conduit:latest
    restart: unless-stopped
    volumes:
      - conduit_data:/var/lib/matrix-conduit
    environment:
      CONDUIT_SERVER_NAME: "chat.your.domain"
      CONDUIT_DATABASE_BACKEND: "rocksdb"
      CONDUIT_ALLOW_REGISTRATION: "true"      # flip to false after accounts created
      CONDUIT_ALLOW_FEDERATION: "false"
      CONDUIT_MAX_REQUEST_SIZE: "20000000"
      CONDUIT_LOG: "warn"
    ports:
      - "127.0.0.1:6167:6167"

volumes:
  conduit_data:
```

```bash
cd /opt/conduit && docker compose up -d
```

For voice and video calls, Matrix uses WebRTC -- which needs a TURN server to traverse NAT. coturn handles this:

```bash
apt install -y coturn
openssl rand -hex 32   # generate a static auth secret, keep it
```

`/etc/turnserver.conf`:

```
listening-port=3478
tls-listening-port=5349
fingerprint
use-auth-secret
static-auth-secret=YOUR_SECRET
realm=chat.your.domain
cert=/etc/letsencrypt/live/chat.your.domain/fullchain.pem
pkey=/etc/letsencrypt/live/chat.your.domain/privkey.pem
min-port=49152
max-port=65535
```

nginx config:

```nginx
server {
    listen 80;
    server_name chat.your.domain;
    location / {
        proxy_pass http://127.0.0.1:6167;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Once Conduit is up: go to Element Web, set homeserver to your domain, register your accounts while `ALLOW_REGISTRATION` is true, then flip it to false and restart the container. Anyone who finds your homeserver URL can register while it's open.

## Service 3: Calibre-Web

Calibre-Web gives you a browser-based library for EPUB, PDF, and MOBI files. The Docker image is from linuxserver.io.

**Critical step before starting the container:** Calibre-Web needs a properly initialized `metadata.db`. Not an empty file, not a directory -- a valid Calibre library database. It must be created by `calibredb`.

```bash
apt install -y calibre   # ~300MB, takes a few minutes
mkdir -p /opt/calibre/books
calibredb --with-library /opt/calibre/books list   # initializes metadata.db
chown -R 1000:1000 /opt/calibre/books              # container runs as uid 1000
chmod -R 755 /opt/calibre/books
```

Do this before starting the container. If you start it first and hit "invalid path" or "DB not writable", this is why.

`/opt/calibre/docker-compose.yml`:

```yaml
services:
  calibre-web:
    image: lscr.io/linuxserver/calibre-web:latest
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Asia/Kolkata
    volumes:
      - calibre_config:/config
      - /opt/calibre/books:/books
    ports:
      - "127.0.0.1:8083:8083"

volumes:
  calibre_config:
```

nginx config:

```nginx
server {
    listen 80;
    server_name books.your.domain;
    location / {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Default login is `admin` / `admin123`. Change it immediately. Set library path to `/books`.

## Cloudflare in Front

All three subdomains go through Cloudflare. DNS A records point to the VPS IP, proxy status set to orange cloud (proxied) for all three. SSL mode set to Full -- not Full Strict, since the Let's Encrypt cert on origin is valid enough and Full Strict adds complexity for no real benefit here.

certbot handles the Let's Encrypt certs on the origin:

```bash
certbot --nginx -d sync.your.domain
certbot --nginx -d chat.your.domain
certbot --nginx -d books.your.domain
```

## Resource Usage

All three services running simultaneously:

| Service | RAM |
|---|---|
| Calibre-Web | ~159MB |
| Conduit | ~62MB |
| CouchDB | ~80MB |
| nginx + OS | ~453MB |
| **Total** | **~754MB / 2.9GB (26%)** |

Swap barely touched. Disk at ~6GB of 30GB. Plenty of headroom for adding services.

## Pitfalls

| Problem | Cause | Fix |
|---|---|---|
| SSH asks for password after key setup | Public key not on server | `ssh-copy-id` or paste key in provider panel |
| Calibre-Web says "invalid path" | metadata.db missing or wrong schema | Install calibre on host, run `calibredb list` to init |
| Calibre-Web says "DB not writable" | Files owned by root, container runs as uid 1000 | `chown -R 1000:1000 /opt/calibre/books` |
| Voice/video calls fail in Matrix | WebRTC can't traverse NAT | Install coturn, configure static-auth-secret |
| CouchDB sync drops randomly | Missing CORS headers | Double-check the `[cors]` section in local.ini |

The whole thing took an afternoon to set up. $22/year for services I fully control and can inspect end to end.
