#!/bin/bash

echo "=== Simple Nextcloud Test ==="
echo "Server: $SSH_SERVER"
echo "User: $SSH_USER"

# Test connection
echo "Testing SSH connection..."
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SSH_SERVER" "echo 'SSH OK'; date"

# Check containers
echo "Checking containers..."
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SSH_SERVER" "cd /srv/docker/nc-rag && docker ps | grep -E '(nextcloud|redis)'"

# Test Redis
echo "Testing Redis..."
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SSH_SERVER" "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli ping"

# Test login
echo "Testing login page..."
curl -s -o /dev/null -w "Status: %{http_code}\n" "https://ncrag.voronkov.club/login"

echo "=== Test Complete ==="