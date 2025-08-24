# 🔧 Troubleshooting Guide

## Login Issues

### Problem: Login Redirect Loop

**Symptoms:**
- After entering correct credentials, redirected back to login page
- URL shows `login?direct=1&user=admin`
- No error messages visible

**Root Cause:**
Bug/incompatibility in **Nextcloud 31** with reverse proxy configuration.

**Solution:**
Use **Nextcloud 30** instead of version 31.

### Quick Fix

```bash
cd /srv/docker/nc-rag

# 1. Stop services
docker compose down

# 2. Change version in docker-compose.yml
sed -i 's/nextcloud:31-apache/nextcloud:30-apache/g' docker-compose.yml

# 3. Remove data volumes for clean install
docker volume rm nc-rag_nextcloud_data nc-rag_db_data

# 4. Start with Nextcloud 30
docker compose up -d
sleep 120

# 5. Configure for reverse proxy
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.0/16'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
```

### Verification

Test login after fix:
```bash
curl -s -o /dev/null -w "Status: %{http_code}\n" "https://ncrag.voronkov.club/login"
# Should return: Status: 200

# Manual login test should now work at https://ncrag.voronkov.club
```

## Password Configuration

### Environment Variables
- `NEXTCLOUD_PASSWORD` - Frontend web login password
- `NEXTCLOUD_APP_PASSWORD` - API access token (different from web login)

### Correct Usage
- **Web login**: Use password from `NEXTCLOUD_PASSWORD` environment variable
- **API calls**: Use token from `NEXTCLOUD_APP_PASSWORD` environment variable

### Reset Password
```bash
docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:resetpassword admin --password-from-env
```

## Common Issues

### Redis Connection Errors
```bash
# Check Redis
docker exec nc-redis redis-cli ping

# Disable Redis caching if problematic
docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed
docker exec -u www-data nextcloud php occ config:system:delete memcache.locking
docker restart nextcloud
```

### Traefik Routing Issues
```bash
# Check Traefik logs
docker logs traefik --tail 20

# Verify routing rules
grep "traefik.http.routers" docker-compose.yml
```

### SSL Certificate Issues
```bash
# Check certificates
docker exec traefik ls -la /letsencrypt/

# Force certificate renewal
docker restart traefik
```

## Proxy Configuration

### Required Settings for Reverse Proxy

```bash
# Essential proxy settings
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.0/16'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'

# Optional: Forwarded headers
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 0 --value='HTTP_X_FORWARDED_FOR'
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 1 --value='HTTP_X_REAL_IP'
```

### Traefik Labels for Nextcloud

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.nextcloud.rule=Host(`ncrag.voronkov.club`)"
  - "traefik.http.routers.nextcloud.entrypoints=websecure"
  - "traefik.http.routers.nextcloud.tls.certresolver=le"
  - "traefik.http.routers.nextcloud.priority=100"
  - "traefik.http.services.nextcloud.loadbalancer.server.port=80"
  - "traefik.docker.network=nc-rag_backend"
```

## Version Compatibility

### Tested Versions
- ✅ **Nextcloud 30**: Fully compatible with Traefik v3.5
- ❌ **Nextcloud 31**: Known issues with reverse proxy login

### Recommended Configuration
```yaml
# Use Nextcloud 30 for stability
nextcloud:
  image: nextcloud:30-apache
  
nextcloud-cron:
  image: nextcloud:30-apache
```

## Logs and Debugging

### Check Container Status
```bash
docker compose ps
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### View Logs
```bash
# Nextcloud logs
docker logs nextcloud --tail 50

# Traefik logs
docker logs traefik --tail 50

# Nextcloud application logs
docker exec nextcloud tail -20 /var/www/html/data/nextcloud.log
```

### Test Connectivity
```bash
# Test site accessibility
curl -I "https://ncrag.voronkov.club/"

# Test direct container access
NEXTCLOUD_IP=$(docker inspect nextcloud | grep '"IPAddress"' | head -1 | grep -oP '\d+\.\d+\.\d+\.\d+')
curl -H "Host: ncrag.voronkov.club" -I "http://$NEXTCLOUD_IP/"
```

## Emergency Recovery

### Restore from Backup
```bash
# If you have backups
docker compose down
docker volume rm nc-rag_nextcloud_data nc-rag_db_data
# Restore your backup volumes
docker compose up -d
```

### Factory Reset
```bash
# Complete reset (WARNING: loses all data)
docker compose down
docker volume rm nc-rag_nextcloud_data nc-rag_db_data nc-rag_node_red_data
docker system prune -f
docker compose up -d
```