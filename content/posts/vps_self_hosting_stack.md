+++
title = "A $22/Year VPS That Actually Does Things"
date = 2026-04-22T00:00:00+00:00
draft = false
math = false
+++

I've had a domain sitting idle for a while. I finally did something with it. For $22/year I now have a private sync server, a self-hosted chat with video calls, and a personal book library -- all running on a single Ubuntu VM in Dallas.

Here's what I built and how it fits together.

## The server

Provider: budget VPS, $22/year. That's not a typo.

- 1 vCPU, 2.9GB RAM, 30GB disk
- Ubuntu 24.04 LTS
- IP: 192.3.228.223
- Unlimited bandwidth (Dallas datacenter)

First thing I did after SSH'ing in: update packages, disable password login, set up SSH key auth only, and add UFW rules to block everything except SSH, HTTP, HTTPS, and TURN ports. Then added a 2GB swap file -- at 2.9GB of RAM you feel every megabyte.

Credentials go into `pass` on my Mac, encrypted with a GPG key. No plaintext passwords anywhere.

## Three services, one box

### Obsidian LiveSync -- sync.shenthar.me

CouchDB running as the backend for Obsidian's LiveSync plugin. My vault syncs across Mac, iPhone, and anything else with the app installed. The sync is end-to-end encrypted via a LiveSync passphrase -- CouchDB never sees the plaintext.

This replaced iCloud sync, which was flaky and opaque. Now I know exactly where my notes live and who can read them (me, and only me).

### Private chat -- chat.shenthar.me

Matrix homeserver running Conduit in Docker. Element Web as the UI -- no app install needed, works in any browser. Two accounts: sapphire and yellow.

For video and audio calls I set up a coturn TURN server. Without TURN, WebRTC calls often fail when both sides are behind NAT. With it, the media traffic relays through the VPS and calls just work.

Federation is disabled. This is a private instance -- no traffic to matrix.org or anywhere else. Just the two of us.

### Personal library -- books.shenthar.me

Calibre-Web in Docker. Handles EPUB, PDF, MOBI. Two accounts, same as above. I added Pride and Prejudice as a test -- it showed up immediately, clean reader UI.

No more emailing books to a Kindle or dragging files around. Upload once, read anywhere.

## Infrastructure layer

Everything sits behind nginx as a reverse proxy. Cloudflare handles DNS, proxying, and SSL in Full mode. Let's Encrypt issues certs on each subdomain and auto-renews them.

The flow for any request:

```
Browser -> Cloudflare (proxy + SSL termination) -> nginx (routing) -> service
```

Docker isolates Conduit and Calibre-Web. CouchDB runs native (the LiveSync plugin expects standard CouchDB behavior and Docker added complications I didn't need).

## Resource usage

After all three services were up:

- RAM used: about 1.2GB
- Disk used: ~6GB
- Remaining: nearly 1.7GB RAM and 24GB disk free

Plenty of headroom. The box idles comfortably and there's room for a few more experiments -- a small bot, a VPN, whatever comes next.

## What this cost

The domain was already paid for. The VPS is $22/year. Everything else is open source and free. The setup took an evening.

The usual objections to self-hosting are maintenance burden and reliability. For low-stakes personal services -- note sync, private chat, book library -- a single VPS with good backups is fine. If CouchDB goes down for an hour, my notes don't sync. That's acceptable.

The upside is ownership. No subscription. No vendor deciding to change pricing or sunset the service. No questions about who holds the encryption keys.

## What's next

The daily note I wrote after this has a few ideas: running Bifrost on the VPS, a ghost-writing pipeline for blog posts, maybe a VPN since the bandwidth is unlimited. The RAM budget will get tighter, but there's room to work with.

For now, the three services are running and the box earns its $22.

---

Tools used: Ubuntu 24.04, Docker, nginx, Cloudflare, Let's Encrypt, CouchDB, Conduit (Matrix), Element Web, Calibre-Web, coturn, UFW, pass + GPG.
