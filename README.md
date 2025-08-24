# Nextcloud + Node-RED Integration

A Docker Compose setup for running Nextcloud with Node-RED integration behind Traefik reverse proxy.

## 🎯 **Current Status: FULLY OPERATIONAL** ✅

- **Nextcloud**: Accessible at https://ncrag.voronkov.club (built-in auth)
- **Node-RED UI**: Accessible at https://ncrag.voronkov.club/nodered (internal auth: admin/admin)
- **Webhooks**: Functional at /nodered/webhooks/nextcloud (no auth required)
- **API**: Operational with token authentication

## 🚀 **Quick Start**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nc-rag
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Deploy services**
   ```bash
   docker compose up -d
   ```

4. **Access services**
   - Nextcloud: https://your-domain.com
   - Node-RED: https://your-domain.com/nodered

## 📋 **Components**

- **Nextcloud 30**: File hosting and collaboration platform
- **Node-RED 4.1**: Flow-based programming for IoT
- **Traefik v3.5**: Reverse proxy with automatic SSL
- **PostgreSQL 17**: Database backend
- **Redis 7**: Session and cache storage

## 🔧 **Key Features**

- **Automatic SSL**: Let's Encrypt certificates via Traefik
- **Basic Authentication**: Secure Node-RED UI access
- **Webhook Integration**: Nextcloud events → Node-RED flows
- **API Access**: Full Nextcloud API with token authentication
- **Health Monitoring**: Container health checks

## 📚 **Documentation**

- **[Authentication Guide](AUTHENTICATION_GUIDE.md)**: Complete authentication and routing setup
- **[Solution Guide](SOLUTION_GUIDE.md)**: Troubleshooting and configuration guide
- **[Troubleshooting](TROUBLESHOOTING.md)**: Common issues and fixes
- **[Working Solution](FINAL_WORKING_SOLUTION.md)**: Final configuration details

## 🛠️ **Configuration**

### **Environment Variables**
```bash
# Domain settings
NEXTCLOUD_DOMAIN=your-domain.com
LETSENCRYPT_EMAIL=admin@your-domain.com

# Nextcloud credentials
NEXTCLOUD_ADMIN_USER=admin
NEXTCLOUD_ADMIN_PASSWORD=your-secure-password

# API access
NEXTCLOUD_APP_PASSWORD=your-api-token
```

### **Network Architecture**
- **Backend Network**: Internal service communication
- **Web Network**: External Traefik access
- **SSL Termination**: Automatic certificate management

## 🔐 **Security**

- **HTTPS Only**: Automatic HTTP → HTTPS redirect
- **Multi-layer Auth**: Nextcloud built-in + Node-RED internal authentication
- **API Tokens**: Secure Nextcloud API access
- **Network Isolation**: Services in separate networks
- **Webhook Security**: Secret-based validation for Nextcloud events

## 📊 **Monitoring**

Check service status:
```bash
docker compose ps
docker compose logs -f [service-name]
```

Test endpoints:
```bash
curl -I https://your-domain.com
curl -u admin:password https://your-domain.com/nodered
```

## 🆘 **Support**

If you encounter issues:

1. Check the [Solution Guide](SOLUTION_GUIDE.md)
2. Review [Troubleshooting](TROUBLESHOOTING.md)
3. Examine container logs: `docker compose logs`
4. Verify network connectivity and DNS resolution

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 **Contributing**

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Status**: Production Ready ✅ | **Last Updated**: August 2025