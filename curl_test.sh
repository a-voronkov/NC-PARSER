#!/bin/bash

echo "=== Nextcloud Login Test with cURL ==="

# Test basic connectivity
echo "1. Testing site accessibility..."
SITE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://ncrag.voronkov.club/login")
echo "Site status: $SITE_STATUS"

if [ "$SITE_STATUS" != "200" ]; then
    echo "❌ Site not accessible"
    exit 1
fi

# Test login flow
echo "2. Testing login flow..."
COOKIE_JAR="/tmp/test_cookies_$(date +%s).txt"
rm -f "$COOKIE_JAR"

# Get login page and CSRF token
echo "Getting login page..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ Failed to get CSRF token"
    exit 1
fi

echo "CSRF token obtained: ${CSRF_TOKEN:0:20}..."

# Submit login
echo "Submitting login credentials..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "HTTPSTATUS:%{http_code}\nFINAL_URL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

# Extract results
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTPSTATUS" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "FINAL_URL" | cut -d: -f2-)

echo "HTTP Status: $HTTP_STATUS"
echo "Final URL: $FINAL_URL"

# Check if login was successful
if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ LOGIN FAILED: Still on login page"
    
    # Check for specific error indicators in response
    if echo "$RESPONSE" | grep -q "Wrong username or password"; then
        echo "Error: Wrong credentials"
    elif echo "$RESPONSE" | grep -q "Too many failed login attempts"; then
        echo "Error: Too many failed attempts"
    elif echo "$RESPONSE" | grep -q "session"; then
        echo "Error: Session related issue"
    else
        echo "Error: Unknown login failure"
    fi
    
    # Save response for debugging
    echo "$RESPONSE" > "/workspace/login_response.html"
    echo "Response saved to login_response.html"
    
    exit 1
elif echo "$RESPONSE" | grep -q "files\|dashboard\|apps\|<title>Files"; then
    echo "✅ LOGIN SUCCESS: Found dashboard/files content"
    exit 0
else
    echo "⚠️ LOGIN UNCLEAR: Not on login page but no dashboard found"
    echo "Response length: $(echo "$RESPONSE" | wc -c) characters"
    
    # Save response for analysis
    echo "$RESPONSE" > "/workspace/login_response.html"
    echo "Response saved to login_response.html"
    
    exit 2
fi