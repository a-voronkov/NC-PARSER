# Troubleshooting

## Login Issues

If you cannot log in to the Nextcloud web interface:

### Quick Fix
```bash
cd /srv/docker/nc-rag
./scripts/fix-nextcloud-login.sh
```

### Manual Fix Steps

1. **Check Password Configuration**:
   ```bash
   # Ensure NEXTCLOUD_PASSWORD environment variable is set correctly
   echo $NEXTCLOUD_PASSWORD
   
   # Reset admin password
   docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:resetpassword admin --password-from-env
   ```

2. **Configure Redis for Sessions**:
   ```bash
   docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\OC\Memcache\Redis'
   docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\OC\Memcache\Redis'
   ```

3. **Set HTTPS Configuration**:
   ```bash
   docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
   docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
   ```

4. **Clear Cache and Restart**:
   ```bash
   docker exec nc-redis redis-cli FLUSHALL
   docker restart nextcloud
   ```

### Common Issues

- **Wrong Password**: Ensure you're using `NEXTCLOUD_PASSWORD` for web login, not `NEXTCLOUD_APP_PASSWORD` (which is for API access)
- **Redis Connection Errors**: Check if Redis container is running: `docker exec nc-redis redis-cli ping`
- **Session Issues**: Clear browser cache and cookies, try incognito mode
- **CSRF Token Errors**: Usually fixed by proper Redis configuration

### Logs

Check logs for debugging:
```bash
# Container logs
docker logs nextcloud --tail 20

# Nextcloud application logs
docker exec nextcloud tail -20 /var/www/html/data/nextcloud.log
```

## Redis Issues

If Redis is causing problems, you can temporarily disable it:

```bash
docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed
docker exec -u www-data nextcloud php occ config:system:delete memcache.locking
docker restart nextcloud
```

## Password Management

### Environment Variables
- `NEXTCLOUD_PASSWORD` - Frontend web login password
- `NEXTCLOUD_APP_PASSWORD` - API access token (different from web login)

### Resetting Passwords
```bash
# Reset web login password
docker exec -e OC_PASS="new_password" -u www-data nextcloud php occ user:resetpassword admin --password-from-env

# Generate new API token
docker exec -u www-data nextcloud php occ user:add-app-password admin
```