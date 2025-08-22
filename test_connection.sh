#!/bin/bash
echo "Testing SSH connection..."
echo "SSH_SERVER: $SSH_SERVER"
echo "SSH_USER: $SSH_USER"
echo "Attempting connection..."
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SSH_SERVER" "echo 'Connection successful'; date"