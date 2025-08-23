# 🎉 FINAL WORKING SOLUTION

## ✅ PROBLEM SOLVED!

**Root Cause:** Bug or incompatibility in **Nextcloud 31** with reverse proxy configuration.

**Solution:** Rollback to **Nextcloud 30** completely resolved the login issue.

## 🎯 TEST RESULTS

- ❌ **Nextcloud 31**: Persistent redirect to `login?direct=1&user=admin`
- ✅ **Nextcloud 30**: Successful login with redirect to `/apps/dashboard/`

## 🚀 WORKING CONFIGURATION

### docker-compose.yml (final version):
```yaml
services:
  traefik:
    image: traefik:v3.5
    container_name: traefik
    command:
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
      - --providers.docker.network=nc-rag_backend
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --entrypoints.web.http.redirections.entryPoint.to=websecure
      - --entrypoints.web.http.redirections.entryPoint.scheme=https
      - --certificatesresolvers.le.acme.email=admin@voronkov.club
      - --certificatesresolvers.le.acme.storage=/letsencrypt/acme.json
      - --certificatesresolvers.le.acme.httpchallenge=true
      - --certificatesresolvers.le.acme.httpchallenge.entrypoint=web
      - --api.dashboard=true
      - --log.level=INFO
      - --accesslog=true
    labels:
      - "traefik.enable=true"
      - "traefik.http.middlewares.nodered-auth.basicauth.usersfile=/etc/traefik/.htpasswd"
    ports:
      - 80:80
      - 443:443
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_letsencrypt:/letsencrypt
      - ./.htpasswd:/etc/traefik/.htpasswd:ro
    restart: unless-stopped
    networks:
      - web
      - backend

  nextcloud:
    image: nextcloud:30-apache  # CRITICAL: Version 30!
    container_name: nextcloud
    depends_on:
      - db
      - redis
      - memcached
    restart: unless-stopped
    environment:
      POSTGRES_HOST: db
      POSTGRES_DB: nextcloud
      POSTGRES_USER: nextcloud
      POSTGRES_PASSWORD: nextcloudpass
      NEXTCLOUD_ADMIN_USER: admin
      NEXTCLOUD_ADMIN_PASSWORD: j*yDCX<4ubIj_.w##>lhxDc?
      NEXTCLOUD_TRUSTED_DOMAINS: ncrag.voronkov.club
      REDIS_HOST: redis
      REDIS_HOST_PORT: 6379
      REDIS_HOST_PASSWORD: 
      MEMCACHED_HOST: memcached
      MEMCACHED_PORT: 11211
    labels:
      - traefik.enable=true
      - "traefik.http.routers.nextcloud.rule=Host(`ncrag.voronkov.club`) && !PathPrefix(`/nodered`)"
      - traefik.http.routers.nextcloud.entrypoints=websecure
      - traefik.http.routers.nextcloud.tls.certresolver=le
      - traefik.http.routers.nextcloud.priority=1
      - traefik.http.services.nextcloud.loadbalancer.server.port=80
      - traefik.docker.network=nc-rag_backend
    volumes:
      - nextcloud_data:/var/www/html
    networks:
      - backend

  node-red:
    image: nodered/node-red:4.1
    container_name: node-red
    environment:
      - TZ=UTC
      - NODE_RED_ENABLE_SAFE_MODE=false
      - TENANT_DEFAULT=default
      - WEBHOOK_SECRET=changeme
    volumes:
      - ./services/node-red/flows.json:/data/flows.json
      - ./services/node-red/settings.js:/data/settings.js
      - node_red_data:/data
    depends_on:
      - traefik
    labels:
      - traefik.enable=true
      # Webhooks WITHOUT authentication (highest priority)
      - "traefik.http.routers.nodered-webhook.rule=Host(`ncrag.voronkov.club`) && PathPrefix(`/nodered/webhooks`)"
      - traefik.http.routers.nodered-webhook.entrypoints=websecure
      - traefik.http.routers.nodered-webhook.priority=1000
      - traefik.http.routers.nodered-webhook.tls.certresolver=le
      # Node-RED UI WITH authentication (high priority)
      - "traefik.http.routers.nodered-ui.rule=Host(`ncrag.voronkov.club`) && PathPrefix(`/nodered`)"
      - traefik.http.routers.nodered-ui.entrypoints=websecure
      - traefik.http.routers.nodered-ui.priority=900
      - traefik.http.routers.nodered-ui.tls.certresolver=le
      - traefik.http.routers.nodered-ui.middlewares=nodered-auth
      # Single service for both routers
      - traefik.http.services.nodered.loadbalancer.server.port=1880
      - traefik.docker.network=nc-rag_backend
    restart: unless-stopped
    networks:
      - backend
```

## 🔧 ESSENTIAL NEXTCLOUD COMMANDS

### Post-installation configuration:
```bash
# Reset brute force protection
docker exec -u www-data nextcloud php occ security:bruteforce:reset

# Configure for reverse proxy
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.0/16'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'

# Generate API token for webhooks
docker exec -u www-data nextcloud php occ user:auth-tokens:add admin --password-from-env
# Set OC_PASS environment variable with the Nextcloud password
```

## 🎯 LOGIN CREDENTIALS

### Web Interface:
- **URL**: https://ncrag.voronkov.club
- **Username**: admin  
- **Password**: j*yDCX<4ubIj_.w##>lhxDc?

### Node-RED UI:
- **URL**: https://ncrag.voronkov.club/nodered
- **Username**: admin
- **Password**: j*yDCX<4ubIj_.w##>lhxDc?

### API Access:
- **Token**: JaJsQQmL8LXV5xsEbRn0PFG251isPuLZobhmvetofnZE9vb3slNby9KJjnXr0vX8QDHbPsHc

## 📝 RECOMMENDATIONS FOR REPOSITORY

1. **Update docker-compose.yml** to use Nextcloud 30
2. **Add documentation** about version compatibility issues  
3. **Include troubleshooting guide** for common proxy problems
4. **Document Node-RED integration** setup steps
5. **Add health checks** for all services

## 🎉 SUCCESS CONFIRMATION

```bash
# Test Nextcloud access
curl -I https://ncrag.voronkov.club
# Expected: HTTP/2 302 (redirect to login)

# Test Node-RED UI
curl -u "admin:j*yDCX<4ubIj_.w##>lhxDc?" https://ncrag.voronkov.club/nodered
# Expected: HTTP/2 301 -> 200 (Node-RED interface)

# Test webhooks
curl https://ncrag.voronkov.club/nodered/webhooks/nextcloud
# Expected: HTTP/2 200 (webhook endpoint ready)
```

**Status: FULLY OPERATIONAL** ✅