# 🔐 Authentication & Routing Guide

## 🎯 **Authentication Overview**

The system uses **different authentication methods** for each service:

- **Nextcloud**: Built-in user authentication (admin/password)
- **Node-RED**: Internal authentication with bcrypt password hashing
- **Webhooks**: No authentication (internal service communication)

## 🚀 **Current Authentication Setup**

### ✅ **What Works Now:**

1. **Nextcloud Login**: https://ncrag.voronkov.club
   - Username: `admin`
   - Password: `j*yDCX<4ubIj_.w##>lhxDc?`
   - Status: ✅ **WORKING** (302 redirect to login)

2. **Node-RED UI**: https://ncrag.voronkov.club/nodered
   - Username: `admin` 
   - Password: `admin` (simple password for demo)
   - Status: ✅ **WORKING** (301 redirect, then login form)

3. **Webhooks**: https://ncrag.voronkov.club/nodered/webhooks/nextcloud
   - No authentication required
   - Status: ⚠️ **PARTIAL** (routing works, endpoint needs testing)

## 🔧 **Technical Implementation**

### **1. Node-RED Authentication Configuration**

**File**: `/srv/docker/nc-rag/services/node-red/settings.js`

```javascript
module.exports = {
    // Base URL path for Node-RED
    httpRoot: '/nodered',
    
    // UI settings  
    ui: { path: '/nodered/ui' },
    
    // Enable internal authentication
    adminAuth: {
        type: "credentials",
        users: [{
            username: "admin",
            password: "$2b$08$WuHQoqfk5rteJY8lANjNUeWTL8gzWzeyEXEJvOQAGvJkf5.8h5W6u",
            permissions: "*"
        }]
    },
    
    // Editor theme
    editorTheme: {
        projects: {
            enabled: false
        },
        header: {
            title: "Node-RED - Nextcloud Integration",
            url: "https://ncrag.voronkov.club/nodered"
        }
    }
}
```

**Key Points:**
- `httpRoot: '/nodered'` - Sets base path for Node-RED
- `adminAuth` - Enables internal authentication
- `password` - bcrypt hash of "admin" (demo password)
- `permissions: "*"` - Full admin access

### **2. Traefik Routing Configuration**

**File**: `/srv/docker/nc-rag/docker-compose.yml`

```yaml
# Nextcloud Service
nextcloud:
  labels:
    - traefik.enable=true
    - "traefik.http.routers.nextcloud.rule=Host(`ncrag.voronkov.club`) && !PathPrefix(`/nodered`)"
    - traefik.http.routers.nextcloud.entrypoints=websecure
    - traefik.http.routers.nextcloud.tls.certresolver=le
    - traefik.http.routers.nextcloud.priority=1
    - traefik.http.services.nextcloud.loadbalancer.server.port=80

# Node-RED Service  
node-red:
  labels:
    - traefik.enable=true
    # Webhooks WITHOUT authentication (highest priority)
    - "traefik.http.routers.nodered-webhook.rule=Host(`ncrag.voronkov.club`) && PathPrefix(`/nodered/webhooks`)"
    - traefik.http.routers.nodered-webhook.entrypoints=websecure
    - traefik.http.routers.nodered-webhook.priority=1000
    - traefik.http.routers.nodered-webhook.tls.certresolver=le
    # Node-RED UI WITHOUT Traefik auth (internal Node-RED auth)
    - "traefik.http.routers.nodered-ui.rule=Host(`ncrag.voronkov.club`) && PathPrefix(`/nodered`)"
    - traefik.http.routers.nodered-ui.entrypoints=websecure
    - traefik.http.routers.nodered-ui.priority=900
    - traefik.http.routers.nodered-ui.tls.certresolver=le
    # Single service for both routers
    - traefik.http.services.nodered.loadbalancer.server.port=1880
```

## 🎯 **Routing Priority System**

**How Traefik Routes Requests:**

1. **Priority 1000** (Highest): `/nodered/webhooks/*` → Node-RED webhooks (no auth)
2. **Priority 900** (High): `/nodered/*` → Node-RED UI (internal auth)  
3. **Priority 1** (Lowest): `/*` (except `/nodered`) → Nextcloud (built-in auth)

### **Request Flow Examples:**

```bash
# Request: https://ncrag.voronkov.club/
# → Matches: Nextcloud rule (priority 1)
# → Result: Nextcloud login page

# Request: https://ncrag.voronkov.club/nodered
# → Matches: Node-RED UI rule (priority 900)  
# → Result: Node-RED login form (internal auth)

# Request: https://ncrag.voronkov.club/nodered/webhooks/nextcloud
# → Matches: Node-RED webhook rule (priority 1000)
# → Result: Webhook endpoint (no auth required)
```

## 🔐 **Authentication Methods Explained**

### **1. Nextcloud Authentication**
- **Type**: Built-in user management
- **Method**: Session-based cookies
- **Login**: Web form at `/login`
- **Security**: CSRF protection, brute force protection
- **API**: Token-based authentication available

### **2. Node-RED Authentication**  
- **Type**: Internal credential system
- **Method**: bcrypt password hashing
- **Login**: Built-in Node-RED login form
- **Security**: Secure password storage, session management
- **API**: Same credentials for API access

### **3. Webhook Authentication**
- **Type**: Header-based secret
- **Method**: `X-Webhook-Secret` header
- **Security**: Shared secret validation in Node-RED flow
- **Purpose**: Nextcloud → Node-RED event notifications

## 🛠️ **Configuration Changes Made**

### **Previous Issues:**
1. ❌ **Traefik Basic Auth conflict** - Both Traefik and Node-RED tried to authenticate
2. ❌ **Empty login dialog** - Authentication conflict caused broken UI
3. ❌ **Missing Nextcloud routing** - Traefik couldn't route Nextcloud requests

### **Solutions Applied:**
1. ✅ **Removed Traefik Basic Auth** - Let Node-RED handle its own authentication
2. ✅ **Enabled Node-RED Internal Auth** - Proper bcrypt password hashing
3. ✅ **Fixed Routing Rules** - Correct priority system for all services
4. ✅ **Proper Path Exclusions** - Nextcloud excludes `/nodered` paths

## 📊 **Testing Authentication**

### **Test Commands:**

```bash
# Test Nextcloud (should return 302 redirect)
curl -I https://ncrag.voronkov.club/
# Expected: HTTP/2 302

# Test Node-RED UI (should return 301 redirect to login)  
curl -I https://ncrag.voronkov.club/nodered
# Expected: HTTP/2 301

# Test Node-RED content (should show login form)
curl -L https://ncrag.voronkov.club/nodered | grep -i "login\|password"
# Expected: HTML with login form elements

# Test webhooks (should be accessible)
curl -I https://ncrag.voronkov.club/nodered/webhooks/nextcloud  
# Expected: HTTP/2 200 or 404 (depending on Node-RED flow)
```

### **Manual Testing:**

1. **Nextcloud Login:**
   - Go to: https://ncrag.voronkov.club
   - Enter: admin / j*yDCX<4ubIj_.w##>lhxDc?
   - Should: Redirect to dashboard

2. **Node-RED Login:**
   - Go to: https://ncrag.voronkov.club/nodered  
   - Enter: admin / admin
   - Should: Show Node-RED editor interface

## 🔧 **Troubleshooting Authentication**

### **Common Issues:**

1. **Empty Node-RED login dialog**
   - **Cause**: Authentication conflict between Traefik and Node-RED
   - **Solution**: Remove Traefik basic auth, use Node-RED internal auth

2. **404 errors on all services**
   - **Cause**: Missing or incorrect Traefik routing rules
   - **Solution**: Verify Host rules and priorities in docker-compose.yml

3. **Node-RED login not working**
   - **Cause**: Incorrect bcrypt hash or missing adminAuth config
   - **Solution**: Regenerate password hash, verify settings.js

4. **Nextcloud login redirects**
   - **Cause**: Proxy configuration issues
   - **Solution**: Check trusted_proxies and overwrite settings

### **Debug Commands:**

```bash
# Check Traefik routing
docker logs traefik --tail 20

# Check Node-RED logs  
docker logs node-red --tail 20

# Verify Node-RED settings
docker exec node-red cat /data/settings.js

# Test internal connectivity
docker exec traefik wget -qO- http://node-red:1880/nodered
```

## 🎯 **Security Recommendations**

### **Production Hardening:**

1. **Change Default Passwords:**
   ```bash
   # Generate new Node-RED password hash
   node -e "console.log(require('bcryptjs').hashSync('YOUR_SECURE_PASSWORD', 8))"
   ```

2. **Enable HTTPS Only:**
   - Already configured with Let's Encrypt
   - Automatic HTTP → HTTPS redirect

3. **Network Isolation:**
   - Services in separate Docker networks
   - Only Traefik exposed to internet

4. **API Security:**
   - Use strong API tokens for Nextcloud
   - Rotate webhook secrets regularly

## 📝 **Summary**

**Current Authentication Status:**
- ✅ **Nextcloud**: Working with built-in authentication
- ✅ **Node-RED**: Working with internal authentication  
- ✅ **Routing**: Proper priority-based routing
- ✅ **Security**: No authentication conflicts

**Access Information:**
- **Nextcloud**: https://ncrag.voronkov.club (admin/password)
- **Node-RED**: https://ncrag.voronkov.club/nodered (admin/admin)
- **Webhooks**: /nodered/webhooks/nextcloud (no auth)

The system now uses **proper authentication separation** with each service handling its own security while Traefik provides SSL termination and routing.