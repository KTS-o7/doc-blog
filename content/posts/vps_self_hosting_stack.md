+++
title = "Three Useful Services on a $22/Year VPS"
date = 2026-04-22T00:00:00+05:30
draft = false
math = false
+++

I bought a budget VPS for $22/year -- 1 vCPU, 2.9GB RAM, 30GB disk, Dallas datacenter, Ubuntu 24.04. The plan was to run bots and experiments. I ended up setting up three services that are immediately useful: Obsidian note sync, a private Matrix chat server, and a personal book library.

This post covers what I set up, what broke, and what actually works now.

## Starting point

The provider gives you a root password on first boot. First thing I did was generate an ed25519 SSH key pair locally, paste the public key into the VPS control panel, add a `Host personal` entry to `~/.ssh/config`, and verify key auth works before touching anything else. Then disabling password login:

```bash
sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
```

Don't close your existing SSH session before confirming you can open a new one with key auth. Classic footgun.

Before any services: add swap. 2.9GB of RAM is workable but tight once Docker gets involved.

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Then update packages, set up UFW to allow SSH, HTTP, HTTPS, and the TURN port range (3478, 5349, 49152:65535), and drop everything else.

After all that, the box looked like this:

```
OS: Ubuntu 24.04 LTS
RAM: 2.9GB (470MB used, 2.4GB free)
Disk: 30GB (2.4GB used, 26GB free)
Swap: 2GB (none used yet)
CPU: 1 core
```

Plenty of room to work with.

## Service 1: Obsidian LiveSync

CouchDB as the backend for Obsidian's LiveSync community plugin. The plugin syncs your vault across devices using a CouchDB instance you control. End-to-end encrypted via a passphrase set in the plugin -- CouchDB stores ciphertext only.

Install CouchDB natively (not Docker -- LiveSync requires specific CouchDB config that's simpler to manage directly):

```bash
apt install -y couchdb
```

The installer asks for admin credentials. Set them and remember them. Then configure CouchDB to accept external connections by editing `/opt/couchdb/etc/local.ini`:

```ini
[chttpd]
bind_address = 127.0.0.1  ; nginx will proxy, no need to expose directly

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

Then create the sync database:

```bash
curl -X PUT http://admin:password@localhost:5984/obsidian-sync
```

nginx proxies the sync subdomain to `localhost:5984`. Cloudflare sits in front with Full SSL mode. In the Obsidian LiveSync plugin settings, point it at your CouchDB subdomain, enter the credentials, set your E2E passphrase, and enable sync.

It just works after that. Notes push from Mac, pull on iPhone, no iCloud dependency.

## Service 2: Private Matrix Chat

Conduit is a Matrix homeserver written in Rust. It's small (62MB RAM), single-binary, and handles everything a private two-person server needs. Element Web as the client -- works in any browser, no app required.

Docker Compose setup:

```yaml
services:
  conduit:
    image: matrixconduit/matrix-conduit:latest
    restart: unless-stopped
    volumes:
      - conduit_data:/var/lib/matrix-conduit
    environment:
      CONDUIT_SERVER_NAME: "your.chat.domain"
      CONDUIT_DATABASE_BACKEND: "rocksdb"
      CONDUIT_ALLOW_REGISTRATION: "true"
      CONDUIT_ALLOW_FEDERATION: "false"
      CONDUIT_MAX_REQUEST_SIZE: "20000000"
      CONDUIT_TRUSTED_SERVERS: '["matrix.org"]'
      CONDUIT_LOG: "warn"
    ports:
      - "127.0.0.1:6167:6167"

volumes:
  conduit_data:
```

`ALLOW_FEDERATION: false` is important for a private server. No traffic leaves your machine to federate with matrix.org or anyone else.

For Element Web, the easiest route is the hosted version at `app.element.io` -- just point it at your homeserver URL when logging in. If you want it self-hosted too, serve the static build from nginx.

For voice and video calls, WebRTC needs a TURN server or calls fail behind NAT. coturn handles this:

```bash
apt install -y coturn
```

Configure `/etc/turnserver.conf`:

```
listening-port=3478
tls-listening-port=5349
fingerprint
use-auth-secret
static-auth-secret=<generate with: openssl rand -hex 32>
realm=your.chat.domain
cert=/etc/letsencrypt/live/your.chat.domain/fullchain.pem
pkey=/etc/letsencrypt/live/your.chat.domain/privkey.pem
```

Add the TURN server details in Conduit's config, then tell Element where to find it in the Synapse well-known file. After that, voice and video calls work reliably regardless of NAT.

Create user accounts via the Conduit admin API or by registering through Element while `ALLOW_REGISTRATION: true`. After both accounts are created, set `ALLOW_REGISTRATION: false` so no new accounts can be made.

## Service 3: Personal Book Library

Calibre-Web in Docker. Serves EPUB, PDF, MOBI with a clean browser interface. Can read books directly in the browser without downloading.

The setup hit two non-obvious problems worth documenting.

**Problem 1: Calibre-Web needs a real metadata.db**

The container starts and asks for a library path. I pointed it at `/books` (mapped to `/opt/calibre/books` on the host). It said "invalid path."

The issue is that Calibre-Web expects a valid Calibre library database (`metadata.db`) to already exist at that path. An empty directory is not enough. The database needs to have the correct schema -- not just the file.

The fix is to install Calibre on the host and use `calibredb` to initialize the library properly:

```bash
apt install -y calibre  # takes a while, ~300MB
calibredb --with-library /opt/calibre/books list
```

The `calibredb list` call creates a properly initialized `metadata.db` if one doesn't exist. After this, `/books` becomes a valid library path.

**Problem 2: Permissions**

Even after the database exists, Calibre-Web may refuse to write to it. The linuxserver/calibre-web Docker image runs as user 1000 internally. If the files on the host are owned by root, the container can't write.

```bash
chown -R 1000:1000 /opt/calibre/books
chmod -R 755 /opt/calibre/books
```

After both fixes, the setup page accepted `/books` and the library came up clean.

Docker Compose:

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

Default login after first start: `admin` / `admin123`. Change it immediately.

## nginx and Cloudflare

All three services sit behind nginx. Each subdomain gets a server block that proxies to the local port:

```nginx
server {
    listen 80;
    server_name your.sync.domain;
    location / {
        proxy_pass http://127.0.0.1:5984;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Cloudflare handles DNS and acts as the TLS terminator in Full mode. Let's Encrypt issues certs on each subdomain via certbot. The certs auto-renew -- I won't have to touch them.

Credentials stored in `pass` on the Mac, encrypted with a GPG key. No plaintext passwords in config files or notes.

## Resource usage after all three services

```
Service          RAM
---------        ----
Calibre-Web      159MB
Conduit          62MB
CouchDB          ~80MB
nginx + system   ~453MB
---------        ------
Total            754MB / 2.9GB  (26% used)
Swap used        780KB
Disk used        ~6GB / 30GB
```

74% of RAM still free. The 2GB swap sits untouched. There's room for more things.

## What's next

The daily note has some ideas: run Bifrost on the VPS and wire up a blog-writing pipeline, use the unlimited bandwidth for a VPN, set up a small agent. The RAM budget will tighten but there's headroom to experiment.

For $22/year, the box is already earning its keep.

---

Tools: Ubuntu 24.04, Docker, nginx, Cloudflare, Let's Encrypt, CouchDB, Conduit (Matrix), Element Web, Calibre-Web, coturn, UFW, pass + GPG, certbot.

## References

- LandChad.net -- practical self-hosting guides, covers nginx, certbot, and many services: https://landchad.net
- Conduit (Matrix homeserver in Rust): https://conduit.rs
- Obsidian LiveSync plugin: https://github.com/vrtmrz/obsidian-livesync
- Calibre-Web: https://github.com/janeczku/calibre-web
- coturn TURN server: https://github.com/coturn/coturn
