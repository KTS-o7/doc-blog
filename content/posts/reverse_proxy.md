+++
title = 'End-to-End HTTPS with Cloudflare Origin Certificates and Nginx'
date = 2025-12-27T00:00:00+05:30
draft = false
math = false
+++


Setting up proper SSL/TLS for your web application can be confusing, especially when Cloudflare is in the picture. This guide walks through configuring end-to-end encryption from browser to origin server using Cloudflare Origin Certificates with an Nginx reverse proxy running in Docker.

---

### The Problem: Cloudflare 521 Errors

If you're running Nginx behind Cloudflare and seeing **521 errors**, you likely have a mismatch between your Cloudflare SSL mode and what your origin server supports.

**Common scenario:**
- Nginx is only listening on port 80 (HTTP)
- Cloudflare SSL mode is set to "Full" or "Full (Strict)"
- Cloudflare tries to connect to your origin on port 443
- Origin doesn't respond → **521 Error**

[![](https://mermaid.ink/img/pako:eNplkE1qwzAQha9izNqOZUm2ZAdCnEJ3XXVVvBjLk1jEP0GSQ0Lw3avYpIvOaoZ5H_N4C8i2IshgaPlQ-5x2bum6i-_PvBp4NfmUjWaINofejGeySrXlpZnlZJy8zFfh6G3P_U3-YkCMt_JNJbzTZCz3r-bLdkZOlRQ8Dab3_JYvq9LJ67gHb0fHf7x3Xo9yPAz8ZthZKe8G7ozrLO_F5zd4M8xBBLJiO9qBMvDbsqaEgvYtFKAXr4MSattz1tBh0n4DJYxdw5mz2hicMujV-OfCEzIn-wZS0qTzFDLXrTfOlWdIf6D4AQP0bwI?type=png)](https://mermaid.live/edit#pako:eNplkE1qwzAQha9izNqOZUm2ZAdCnEJ3XXVVvBjLk1jEP0GSQ0Lw3avYpIvOaoZ5H_N4C8i2IshgaPlQ-5x2bum6i-_PvBp4NfmUjWaINofejGeySrXlpZnlZJy8zFfh6G3P_U3-YkCMt_JNJbzTZCz3r-bLdkZOlRQ8Dab3_JYvq9LJ67gHb0fHf7x3Xo9yPAz8ZthZKe8G7ozrLO_F5zd4M8xBBLJiO9qBMvDbsqaEgvYtFKAXr4MSattz1tBh0n4DJYxdw5mz2hicMujV-OfCEzIn-wZS0qTzFDLXrTfOlWdIf6D4AQP0bwI)

---

### Understanding Cloudflare SSL/TLS Modes

Cloudflare offers four SSL modes. Understanding these is crucial:

| Mode | Browser → Cloudflare | Cloudflare → Origin | Certificate Validation |
|------|---------------------|---------------------|------------------------|
| **Off** | HTTP | HTTP | None |
| **Flexible** | HTTPS ✅ | HTTP | None |
| **Full** | HTTPS ✅ | HTTPS ✅ | Accepts any certificate |
| **Full (Strict)** | HTTPS ✅ | HTTPS ✅ | Validates certificate ✅ |

**Key differences:**

- **Flexible**: Quick fix if your origin can't do HTTPS, but traffic between Cloudflare and your server is unencrypted — vulnerable to MITM attacks on that leg.
  
- **Full**: Encrypts both legs, but accepts *any* certificate (even self-signed, expired, or attacker-provided). Provides encryption but not authentication.

- **Full (Strict)**: The gold standard. Cloudflare validates that your origin certificate is either:
  - A valid public CA certificate
  - A Cloudflare Origin Certificate
  
  This prevents MITM attacks where an attacker presents a fake certificate.

---

### Architecture Overview

Our target architecture:

```
┌──────────────────────────────────────────────────────────────────────┐
│                          INTERNET                                    │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTPS (443)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     CLOUDFLARE EDGE                                  │
│              (SSL Termination + CDN + WAF)                           │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTPS (443) - Origin Certificate
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    YOUR EC2 INSTANCE                                 │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    DOCKER NETWORK                               │ │
│  │                                                                 │ │
│  │   ┌─────────────┐    HTTP    ┌─────────────────────────────┐    │ │
│  │   │   NGINX     │───────────▶│     APPLICATION CONTAINERS  │    │ │
│  │   │  (SSL/443)  │            │  - Frontend (Next.js:3000)  │    │ │
│  │   │  (80→443)   │            │  - Backend (FastAPI:8000)   │    │ │
│  │   └─────────────┘            │  - Cloud APIs               │    │ │
│  │         ▲                    └─────────────────────────────┘    │ │
│  │         │                                                       │ │
│  └─────────┼───────────────────────────────────────────────────────┘ │
│            │                                                         │
│     Ports 80, 443                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Traffic flow:**
1. Browser connects to Cloudflare over HTTPS (public SSL certificate)
2. Cloudflare connects to your origin over HTTPS (Origin Certificate)
3. Nginx terminates SSL and proxies to backend containers over HTTP
4. Backend containers communicate on internal Docker network (isolated)

---

### Prerequisites

Before starting, ensure you have:

- A domain proxied through Cloudflare (orange cloud enabled)
- Docker and Docker Compose installed on your server
- An existing Nginx configuration (we'll modify it)
- Access to Cloudflare dashboard
- **Firewall Rules**: Ensure ports 80 and 443 are open in your cloud provider's firewall (AWS Security Group, etc.)

---

### Step 1: Generate a Cloudflare Origin Certificate

Cloudflare Origin Certificates are free, trusted only by Cloudflare, and can be valid for up to 15 years.

1. Log into [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain
3. Navigate to **SSL/TLS** → **Origin Server**
4. Click **Create Certificate**
5. Configure:
   - **Private key type**: RSA (2048)
   - **Hostnames**: `*.yourdomain.com, yourdomain.com`
   - **Validity**: 15 years (recommended)
6. Click **Create**

**⚠️ IMPORTANT**: Copy both the **Origin Certificate** (PEM) and **Private Key** immediately. The private key is shown only once!

Save them to files:

```bash
# Create SSL directory
mkdir -p ssl

# Paste the certificate
cat > ssl/origin.pem << 'EOF'
-----BEGIN CERTIFICATE-----
YOUR_CERTIFICATE_HERE
-----END CERTIFICATE-----
EOF

# Paste the private key
cat > ssl/origin.key << 'EOF'
-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY_HERE
-----END PRIVATE KEY-----
EOF

# Set secure permissions
chmod 600 ssl/origin.key
chmod 644 ssl/origin.pem
```

Add to `.gitignore` to never commit these:

```bash
echo "ssl/*" >> .gitignore
```

---

### Step 2: Configure Nginx for HTTPS

Here's a complete Nginx configuration with SSL, security headers, rate limiting, and reverse proxy setup.

**`nginx/nginx-main.conf`** - Main HTTP block configuration:

```nginx
# Main nginx configuration with security settings
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging format with security information
    log_format security '$real_ip - $remote_user [$time_local] "$request" '
                       '$status $body_bytes_sent "$http_referer" '
                       '"$http_user_agent" "$http_x_forwarded_for" '
                       'rt=$request_time uct="$upstream_connect_time" '
                       'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log security;

    # Pro Tip: use $real_ip in log_format so you see actual visitor IPs, not Cloudflare's.

    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;  # Hide nginx version

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss;

    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=general_limit:10m rate=50r/s;
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
    limit_req_zone $binary_remote_addr zone=burst_limit:10m rate=200r/m;
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    include /etc/nginx/conf.d/*.conf;
}
```

**`nginx/nginx.conf`** - Server block configuration with SSL:

```nginx
# Cloudflare IP handling - extract real client IP
map $http_cf_connecting_ip $real_ip {
    "" $remote_addr;
    default $http_cf_connecting_ip;
}

# Cloudflare protocol handling
map $http_x_forwarded_proto $forwarded_proto {
    "" $scheme;
    default $http_x_forwarded_proto;
}

# HTTP Server (Port 80) - Redirect to HTTPS
server {
    listen 80;
    server_name _;

    # Health check (keep on port 80 for internal monitoring)
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS Server (Port 443)
server {
    listen 443 ssl http2;
    server_name _;

    # SSL Configuration - Cloudflare Origin Certificate
    ssl_certificate /etc/nginx/ssl/origin.pem;
    ssl_certificate_key /etc/nginx/ssl/origin.key;
    
    # Modern SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # Connection and request limits
    limit_conn conn_limit 100;
    client_max_body_size 50M;
    client_body_buffer_size 4M;

    # Timeout limits (prevent slowloris attacks)
    client_body_timeout 10s;
    client_header_timeout 10s;
    send_timeout 10s;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-src 'self';" always;

    # Frontend - Next.js
    location / {
        limit_req zone=general_limit burst=100 nodelay;
        
        proxy_pass http://frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $real_ip;
        proxy_set_header X-Forwarded-For $real_ip;
        proxy_set_header X-Forwarded-Proto $forwarded_proto;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        limit_req zone=api_limit burst=50 nodelay;
        
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $real_ip;
        proxy_set_header X-Forwarded-For $real_ip;
        proxy_set_header X-Forwarded-Proto $forwarded_proto;
        
        # Increased timeouts for long-running requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

> **Docker DNS Caveat**: Nginx caches DNS records at startup. If your backend container restarts and gets a new IP, Nginx might start returning 502 errors. To prevent this, use Docker's internal resolver `resolver 127.0.0.11 valid=30s;` and variables for `proxy_pass` targets.

---

### Step 3: Update Dockerfile

Update your Nginx Dockerfile to expose both ports:

**`nginx/Dockerfile`**:

```dockerfile
FROM nginx:alpine

# Copy configurations
COPY nginx-main.conf /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP and HTTPS ports
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
```

---

### Step 4: Update Docker Compose

Mount the SSL certificates and expose port 443:

**`docker-compose.yml`** (nginx service section):

```yaml
services:
  nginx:
    build:
      context: ./nginx
      dockerfile: Dockerfile
    container_name: my-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - frontend
      - backend
    networks:
      - app-network
    volumes:
      - ./ssl:/etc/nginx/ssl:ro  # Read-only mount
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  app-network:
    driver: bridge
```

---

### Step 5: Deploy

Rebuild and deploy only the nginx container (zero downtime for other services):

```bash
# Build the new nginx image
docker compose build nginx

# Recreate nginx container without touching dependencies
docker compose up -d --no-deps nginx

# Verify nginx is running
docker compose logs nginx --tail=20
```

If you have a deploy script like `prod.sh`, you might need:

```bash
# If container name conflicts exist
docker stop my-nginx && docker rm my-nginx
./prod.sh -d nginx
```

---

### Step 6: Enable Full (Strict) Mode in Cloudflare

Now that your origin supports HTTPS with a valid Origin Certificate:

1. Go to **Cloudflare Dashboard** → **SSL/TLS** → **Overview**
2. Change encryption mode from `Flexible` or `Full` to **`Full (Strict)`**

This change takes effect immediately.

---

### Step 7: Verify

Test the connection:

```bash
curl -I https://yourdomain.com
```

Expected output shows HTTP/2 200 with Cloudflare and security headers:

```
HTTP/2 200 
server: cloudflare
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
content-security-policy: default-src 'self'...
cf-ray: xxxxxxxx-XXX
```

---

### Troubleshooting

#### 521 Error (Web server is down)
- Origin not listening on port 443
- Firewall blocking port 443
- Nginx failed to start (check certificate paths)

```bash
# Check nginx logs
docker compose logs nginx

# Verify nginx config syntax
docker compose exec nginx nginx -t
```

#### 525 Error (SSL handshake failed)
- Certificate/key mismatch
- Invalid certificate format
- Wrong file permissions

```bash
# Verify certificate and key match
openssl x509 -noout -modulus -in ssl/origin.pem | openssl md5
openssl rsa -noout -modulus -in ssl/origin.key | openssl md5
# Both should output the same MD5 hash
```

#### 526 Error (Invalid SSL certificate)
- Only occurs in Full (Strict) mode
- Origin certificate not trusted by Cloudflare
- Certificate expired or for wrong hostname

```bash
# Check certificate details
openssl x509 -in ssl/origin.pem -text -noout | grep -A2 "Subject:"
openssl x509 -in ssl/origin.pem -text -noout | grep -A2 "Validity"
```

---

### Security Considerations

#### What This Setup Protects Against

| Attack | Protected? | How |
|--------|------------|-----|
| MITM (Browser → Cloudflare) | ✅ | Public SSL certificate |
| MITM (Cloudflare → Origin) | ✅ | Origin Certificate + Full (Strict) |
| DDoS | ✅ | Cloudflare absorbs attack traffic |
| SSL Downgrade | ✅ | HTTPS redirect + HSTS (via Cloudflare) |

#### Additional Hardening (Optional)

1. **Authenticated Origin Pulls**: Mutual TLS where Cloudflare presents a client certificate
   
   ```nginx
   ssl_client_certificate /etc/nginx/ssl/cloudflare-origin-pull.pem;
   ssl_verify_client on;
   ```

2. **Restrict Origin to Cloudflare IPs Only**: Configure AWS Security Groups or iptables to only accept connections from [Cloudflare IP ranges](https://www.cloudflare.com/ips/)

3. **Enable HSTS in Cloudflare**: SSL/TLS → Edge Certificates → Always Use HTTPS + HSTS

---

### Quick Reference

| Task | Command |
|------|---------|
| Create SSL directory | `mkdir -p ssl` |
| Set key permissions | `chmod 600 ssl/origin.key` |
| Build nginx | `docker compose build nginx` |
| Deploy nginx only | `docker compose up -d --no-deps nginx` |
| Check nginx logs | `docker compose logs nginx --tail=50` |
| Test nginx config | `docker compose exec nginx nginx -t` |
| Test HTTPS | `curl -I https://yourdomain.com` |

---

### Trade-offs and Limitations

**1. Vendor Lock-in**: 
Cloudflare Origin Certificates are not trusted by major browsers, only by Cloudflare. This means you cannot bypass Cloudflare and connect directly to your origin server IP in a browser without getting severe security warnings. If you ever move away from Cloudflare, you will need to replace these certificates with standard ones (e.g., Let's Encrypt).

**2. Local Development**: 
Since these certificates are for specific public domains, you can't easily use them for `localhost` development. A common pattern is to have a separate `docker-compose.override.yml` for local development that overrides the Nginx config to listen on HTTP only or uses mkcert for locally trusted self-signed certificates.

---

### Conclusion

With this setup, you now have:

✅ **End-to-end encryption** from browser to origin  
✅ **MITM protection** on all network segments  
✅ **Zero-cost SSL** with 15-year Cloudflare Origin Certificate  
✅ **Rate limiting** and security headers  
✅ **Docker-based deployment** for easy management  

The key insight is that **Full (Strict) mode** is what provides actual security. Without it, Cloudflare will accept any certificate from your origin, including one presented by an attacker performing a MITM attack.

---

### Further Reading

- [Cloudflare Origin CA certificates](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/)
- [Cloudflare SSL/TLS encryption modes](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/)
- [Authenticated Origin Pulls](https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/)
- [Nginx SSL configuration best practices](https://ssl-config.mozilla.org/)
