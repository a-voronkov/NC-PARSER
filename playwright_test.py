#!/usr/bin/env python3
"""
Playwright test for Nextcloud login functionality
"""
import asyncio
import os
import subprocess
from playwright.async_api import async_playwright

async def install_playwright():
    """Install Playwright and browsers"""
    print("Installing Playwright...")
    subprocess.run(["pip", "install", "playwright"], check=True)
    subprocess.run(["playwright", "install"], check=True)

async def test_nextcloud_login():
    """Test Nextcloud login process"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("1. Navigating to Nextcloud login page...")
            await page.goto("https://ncrag.voronkov.club/login", timeout=30000)
            
            # Take screenshot
            await page.screenshot(path="/workspace/login_page.png")
            print("Screenshot saved: login_page.png")
            
            print("2. Filling login form...")
            await page.fill('input[name="user"]', 'admin')
            await page.fill('input[name="password"]', 'G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY')
            
            print("3. Submitting login...")
            await page.click('input[type="submit"]')
            
            # Wait for navigation
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # Take screenshot after login attempt
            await page.screenshot(path="/workspace/after_login.png")
            print("Screenshot saved: after_login.png")
            
            # Check current URL
            current_url = page.url
            print(f"Current URL: {current_url}")
            
            # Check if login was successful
            if "/login" in current_url:
                print("❌ LOGIN FAILED: Still on login page")
                
                # Check for error messages
                error_elements = await page.query_selector_all('.warning, .error, [data-test="login-error"]')
                if error_elements:
                    for element in error_elements:
                        error_text = await element.text_content()
                        print(f"Error message: {error_text}")
                else:
                    print("No visible error messages found")
                
                return False
            else:
                print("✅ LOGIN SUCCESS: Redirected away from login page")
                
                # Check for dashboard elements
                dashboard_elements = await page.query_selector_all('[data-test="dashboard"], .app-files, #app-navigation')
                if dashboard_elements:
                    print("Dashboard elements found - login confirmed successful")
                else:
                    print("No dashboard elements found - unclear state")
                
                return True
                
        except Exception as e:
            print(f"Error during test: {e}")
            await page.screenshot(path="/workspace/error_screenshot.png")
            return False
        finally:
            await browser.close()

async def run_ssh_fix():
    """Run SSH commands to fix common issues"""
    ssh_commands = [
        "cd /srv/docker/nc-rag && docker ps",
        "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli ping",
        "cd /srv/docker/nc-rag && docker exec nextcloud php -m | grep -i redis",
        "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get redis",
        "cd /srv/docker/nc-rag && docker logs nextcloud --tail 10"
    ]
    
    for cmd in ssh_commands:
        print(f"Running: {cmd}")
        ssh_cmd = [
            'sshpass', '-p', os.environ['SSH_PASSWORD'],
            'ssh', '-o', 'StrictHostKeyChecking=no',
            f"{os.environ['SSH_USER']}@{os.environ['SSH_SERVER']}",
            cmd
        ]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        print("-" * 50)

async def main():
    print("=== Nextcloud Login Test with Playwright ===")
    
    # Install Playwright if needed
    try:
        await install_playwright()
    except Exception as e:
        print(f"Failed to install Playwright: {e}")
        return
    
    # Run SSH diagnostics first
    print("\n=== SSH Diagnostics ===")
    await run_ssh_fix()
    
    # Run Playwright test
    print("\n=== Playwright Login Test ===")
    success = await test_nextcloud_login()
    
    if success:
        print("\n🎉 Login test PASSED!")
    else:
        print("\n❌ Login test FAILED!")
        print("Check screenshots for more details")
    
    print("\nScreenshots saved in /workspace/:")
    print("- login_page.png")
    print("- after_login.png")
    print("- error_screenshot.png (if error occurred)")

if __name__ == "__main__":
    asyncio.run(main())