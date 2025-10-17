# 🔒 SSL/HTTPS Setup Guide

Complete guide for setting up HTTPS encryption for the Expense Analyzer application.

---

## Overview

This setup provides:
- ✅ SSL/TLS encryption (HTTPS)
- ✅ Automatic HTTP to HTTPS redirect
- ✅ Nginx reverse proxy with security headers
- ✅ Rate limiting protection
- ✅ WebSocket support for Streamlit
- ✅ Self-signed certificate for development/personal use

---

## Quick Start

### Option 1: Automatic Setup (Recommended)

Run the setup script:

```bash
./setup_ssl.sh
```

Then restart the application:

```bash
docker-compose down
docker-compose up -d
```

Access at: **https://localhost**

### Option 2: Manual Setup

Already done! The SSL certificates have been generated in the `ssl/` directory.

---

## What Was Created

### 1. SSL Certificates (`ssl/` directory)

- `certificate.crt` - Public SSL certificate (valid for 365 days)
- `private.key` - Private key (keep secure!)

### 2. Nginx Configuration (`nginx.conf`)

Reverse proxy with:
- SSL termination
- HTTP to HTTPS redirect
- Security headers
- Rate limiting
- WebSocket support
- File upload limits (50MB)

### 3. Updated Docker Compose (`docker-compose.yml`)

Two services:
- `expense-analyzer` - Streamlit app (internal only)
- `nginx` - Reverse proxy with SSL (public facing)

---

## Architecture

```
Client (Browser)
    ↓
    ↓ HTTPS (443) / HTTP (80)
    ↓
Nginx Reverse Proxy
    ↓ SSL Termination
    ↓ HTTP (8501) - internal network
    ↓
Streamlit App
```

---

## Usage

### Starting the Application

```bash
# Start with HTTPS
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### Accessing the Application

**HTTPS (Secure):**
```
https://localhost
```

**HTTP (Redirects to HTTPS):**
```
http://localhost
```

### Browser Security Warning

Since this is a self-signed certificate, browsers will show a warning. This is normal for development/personal use.

**How to proceed:**

- **Chrome/Edge:**
  1. Click "Advanced"
  2. Click "Proceed to localhost (unsafe)"

- **Firefox:**
  1. Click "Advanced"
  2. Click "Accept the Risk and Continue"

- **Safari:**
  1. Click "Show Details"
  2. Click "visit this website"

---

## Security Features

### 1. Encryption
- TLS 1.2 and 1.3 only
- Strong cipher suites
- Perfect Forward Secrecy

### 2. Security Headers
```
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

### 3. Rate Limiting
- Login endpoints: 5 requests/minute
- General endpoints: 100 requests/minute
- Burst protection

### 4. Upload Limits
- Maximum file size: 50MB
- Prevents denial of service attacks

---

## Certificate Details

View certificate information:

```bash
# View certificate
openssl x509 -in ssl/certificate.crt -text -noout

# Check validity
openssl x509 -in ssl/certificate.crt -noout -dates

# Verify certificate matches key
openssl x509 -noout -modulus -in ssl/certificate.crt | openssl md5
openssl rsa -noout -modulus -in ssl/private.key | openssl md5
```

Certificate properties:
- **Type:** Self-signed X.509
- **Algorithm:** RSA 2048-bit
- **Validity:** 365 days
- **Subject:** CN=localhost
- **SAN:** DNS:localhost, IP:127.0.0.1

---

## Regenerating Certificates

### Quick Regeneration

```bash
./setup_ssl.sh
```

### Manual Regeneration

```bash
# Generate new certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/private.key \
  -out ssl/certificate.crt \
  -subj "/C=IL/ST=Israel/L=TelAviv/O=Personal/OU=ExpenseAnalyzer/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1"

# Set permissions
chmod 600 ssl/private.key
chmod 644 ssl/certificate.crt

# Restart services
docker-compose restart nginx
```

---

## Production Deployment

### Using Let's Encrypt (Free, Trusted Certificate)

For production, replace self-signed certificate with Let's Encrypt:

#### 1. Install Certbot

```bash
# On Ubuntu/Debian
apt-get update
apt-get install certbot python3-certbot-nginx

# On macOS
brew install certbot
```

#### 2. Get Certificate

```bash
# For a domain (e.g., expenses.yourdomain.com)
certbot certonly --standalone -d expenses.yourdomain.com

# Certificates will be in:
# /etc/letsencrypt/live/expenses.yourdomain.com/
```

#### 3. Update nginx.conf

```nginx
ssl_certificate /etc/letsencrypt/live/expenses.yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/expenses.yourdomain.com/privkey.pem;
```

#### 4. Update docker-compose.yml

```yaml
nginx:
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

#### 5. Setup Auto-Renewal

```bash
# Test renewal
certbot renew --dry-run

# Add to crontab (renew twice daily)
0 0,12 * * * certbot renew --quiet --post-hook "docker-compose restart nginx"
```

---

## Custom Domain Setup

### 1. Update Hosts File (Development)

```bash
# On Linux/Mac: /etc/hosts
# On Windows: C:\Windows\System32\drivers\etc\hosts

127.0.0.1 expenses.local
```

### 2. Generate Certificate for Custom Domain

```bash
./setup_ssl.sh
# When prompted, enter: expenses.local
```

### 3. Update nginx.conf

```nginx
server {
    listen 443 ssl http2;
    server_name expenses.local;
    # ... rest of config
}
```

### 4. Access

```
https://expenses.local
```

---

## Troubleshooting

### Certificate Not Trusted

**Problem:** Browser shows "Not Secure"

**Solution:** This is expected for self-signed certificates. You can:
1. Click through the warning (safe for personal use)
2. Add certificate to your system's trusted store
3. Use Let's Encrypt for production

### Adding to System Trust Store

**macOS:**
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ssl/certificate.crt
```

**Linux:**
```bash
sudo cp ssl/certificate.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

**Windows:**
1. Double-click `certificate.crt`
2. Click "Install Certificate"
3. Select "Local Machine"
4. Place in "Trusted Root Certification Authorities"

### Connection Refused

**Check nginx is running:**
```bash
docker-compose ps nginx
docker-compose logs nginx
```

**Check ports:**
```bash
# Should show 80 and 443
docker port expense-analyzer-nginx
```

### SSL Handshake Error

**Check certificate validity:**
```bash
openssl x509 -in ssl/certificate.crt -noout -dates
```

**Test SSL connection:**
```bash
openssl s_client -connect localhost:443 -servername localhost
```

### Rate Limiting Issues

If you're getting 429 errors, temporarily disable rate limiting:

Comment out in `nginx.conf`:
```nginx
# limit_req zone=general_limit burst=20 nodelay;
```

Restart:
```bash
docker-compose restart nginx
```

---

## Nginx Configuration Reference

### Key Directives

| Directive | Purpose |
|-----------|---------|
| `ssl_protocols` | Allowed TLS versions (1.2, 1.3) |
| `ssl_ciphers` | Encryption algorithms |
| `client_max_body_size` | Max upload size (50MB) |
| `limit_req_zone` | Rate limiting rules |
| `proxy_pass` | Forward to Streamlit |
| `proxy_set_header Upgrade` | WebSocket support |

### Customization

Edit `nginx.conf` to customize:

**Change upload limit:**
```nginx
client_max_body_size 100M;  # Increase to 100MB
```

**Adjust rate limits:**
```nginx
limit_req_zone $binary_remote_addr zone=general_limit:10m rate=200r/m;  # 200 req/min
```

**Add custom headers:**
```nginx
add_header X-Custom-Header "value" always;
```

After changes:
```bash
docker-compose restart nginx
```

---

## Monitoring

### Check SSL Status

```bash
# Test HTTPS connection
curl -k https://localhost/_stcore/health

# Check certificate
echo | openssl s_client -connect localhost:443 2>/dev/null | openssl x509 -noout -dates

# Monitor nginx logs
docker-compose logs -f nginx
```

### Performance Testing

```bash
# Test response time
curl -w "@-" -o /dev/null -s https://localhost <<'EOF'
time_namelookup:  %{time_namelookup}\n
time_connect:  %{time_connect}\n
time_appconnect:  %{time_appconnect}\n
time_pretransfer:  %{time_pretransfer}\n
time_redirect:  %{time_redirect}\n
time_starttransfer:  %{time_starttransfer}\n
time_total:  %{time_total}\n
EOF
```

---

## Security Best Practices

### ✅ Current Implementation

- [x] SSL/TLS encryption
- [x] Strong cipher suites
- [x] Security headers
- [x] Rate limiting
- [x] HTTP to HTTPS redirect
- [x] Upload size limits
- [x] WebSocket security

### 📋 Additional Recommendations

#### For Production:

1. **Use Trusted Certificate**
   - Let's Encrypt (free)
   - Commercial CA (DigiCert, etc.)

2. **Enable HSTS**
   ```nginx
   add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
   ```

3. **Add CSP Header**
   ```nginx
   add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;
   ```

4. **Enable OCSP Stapling**
   ```nginx
   ssl_stapling on;
   ssl_stapling_verify on;
   ```

5. **Implement Fail2ban**
   - Ban IPs after repeated failed logins

6. **Regular Updates**
   - Keep nginx and certificates updated
   - Monitor security advisories

---

## Files Reference

### Created Files

```
expense_analyzer/
├── ssl/
│   ├── certificate.crt      # Public certificate
│   └── private.key          # Private key (KEEP SECURE!)
├── nginx.conf               # Nginx configuration
├── docker-compose.yml       # Updated with nginx service
├── setup_ssl.sh            # SSL setup script
└── SSL_SETUP.md            # This file
```

### Security Note

**NEVER commit `ssl/private.key` to git!**

The file is automatically added to `.gitignore`.

---

## Support

### Common Commands

```bash
# Start with HTTPS
docker-compose up -d

# Stop services
docker-compose down

# Restart nginx only
docker-compose restart nginx

# View nginx config
cat nginx.conf

# Check certificate
openssl x509 -in ssl/certificate.crt -text -noout

# Test HTTPS
curl -k https://localhost/_stcore/health
```

### Getting Help

1. Check logs: `docker-compose logs nginx`
2. Verify certificate: `openssl x509 -in ssl/certificate.crt -noout -dates`
3. Test connection: `curl -v -k https://localhost`

---

## Summary

**✅ HTTPS is now enabled!**

- Access at: https://localhost
- Self-signed certificate (valid for 1 year)
- All traffic encrypted
- Rate limiting enabled
- Security headers active

**For Production:**
- Use Let's Encrypt for trusted certificate
- Configure firewall rules
- Set up monitoring
- Enable HSTS

🔒 Your financial data is now encrypted in transit!
