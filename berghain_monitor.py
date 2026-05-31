#!/usr/bin/env python3
"""
🎵 Berghain Berlin Monitor
Tracks DJ lineups and sends email alerts when program changes
"""

import requests
import json
import os
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def fetch_berghain_program():
    """Fetch Berghain program using Selenium"""
    print("🌐 Fetching Berghain program (Selenium)...")
    
    try:
        # Setup Chrome options
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Start driver
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        # Load page
        driver.get("https://berghain.berlin/en/program/")
        
        # Wait for content to load
        wait = WebDriverWait(driver, 10)
        
        # Get page content
        page_content = driver.page_source
        
        # Extract events (adapt selectors based on actual HTML)
        events = {}
        
        # Look for event containers
        event_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='event'], [class*='program'], article")
        
        print(f"   ✅ Found {len(event_elements)} event elements")
        
        # Parse events
        for elem in event_elements:
            try:
                text = elem.text.strip()
                if text and len(text) > 10:
                    events[text[:50]] = text
            except:
                pass
        
        driver.quit()
        
        return events if events else {"status": "Page loaded - content may be dynamic"}
        
    except Exception as e:
        print(f"   ❌ Selenium error: {e}")
        return {"error": str(e)}

def load_snapshot(filename="berghain_snapshot.json"):
    """Load previous snapshot"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_snapshot(data, filename="berghain_snapshot.json"):
    """Save current snapshot"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def detect_changes(current, previous):
    """Detect changes between snapshots"""
    changes = []
    
    current_set = set(current.keys()) if isinstance(current, dict) else set()
    previous_set = set(previous.keys()) if isinstance(previous, dict) else set()
    
    # New events
    added = current_set - previous_set
    if added:
        changes.extend([f"New: {item}" for item in list(added)[:5]])
    
    # Removed events
    removed = previous_set - current_set
    if removed:
        changes.extend([f"Removed: {item}" for item in list(removed)[:5]])
    
    return changes

def send_email(current_events, changes):
    """Send email with program update"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    EMAIL = os.getenv("GMAIL_ADDRESS")
    PASSWORD = os.getenv("GMAIL_PASSWORD")
    RECIPIENT = os.getenv("NOTIFY_EMAIL")
    
    if not all([EMAIL, PASSWORD, RECIPIENT]):
        print("⚠️  Missing email credentials")
        return
    
    # Build HTML
    current_html = "<h3>📅 CURRENT PROGRAM</h3>"
    for i, (key, value) in enumerate(list(current_events.items())[:10]):
        current_html += f"<p style='margin: 5px 0; color: #555; font-size: 13px;'>• {value[:100]}</p>"
    
    changes_html = "<h3>🔄 WHAT CHANGED</h3>"
    if changes:
        for change in changes[:10]:
            changes_html += f"<p style='margin: 5px 0; color: #666;'>✓ {change}</p>"
    else:
        changes_html += "<p style='color: #666;'>No changes detected</p>"
    
    html = f"""<html><body style="font-family: Arial; color: #333; background: #f5f5f5; padding: 20px;">
<div style="max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px;">

<h1 style="color: #ff6b9d; text-align: center;">🎵 Berghain Berlin</h1>
<h2 style="text-align: center; color: #666; font-size: 16px;">Program Monitor</h2>

<div style="background: #f0f9ff; padding: 25px; border-radius: 10px; margin: 20px 0;">
{current_html}
</div>

<div style="background: #fef3c7; padding: 25px; border-radius: 10px;">
{changes_html}
</div>

<div style="text-align: center; padding-top: 20px; border-top: 1px solid #eee; margin-top: 30px; font-size: 12px; color: #999;">
<p>Email sent: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
<p>Monitor checks every 48 hours</p>
</div>

</div>
</body></html>"""
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🎵 Berghain - Program Update"
    msg["From"] = EMAIL
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(html, "html"))
    
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, RECIPIENT, msg.as_string())
        server.quit()
        print("✅ Email sent!")
    except Exception as e:
        print(f"Email error: {e}")

def main():
    """Main monitoring function"""
    print("=" * 70)
    print("🎵 BERGHAIN BERLIN MONITOR")
    print("=" * 70)
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70 + "\n")
    
    # Fetch current program
    current_program = fetch_berghain_program()
    
    # Load previous snapshot
    previous_program = load_snapshot()
    
    # Detect changes
    changes = detect_changes(current_program, previous_program)
    
    print(f"\n{'='*70}")
    if changes:
        print(f"🔄 CHANGES DETECTED ({len(changes)} changes)")
        for change in changes[:5]:
            print(f"  {change}")
    else:
        print("✅ No changes detected")
    print(f"{'='*70}\n")
    
    # Save snapshot
    save_snapshot(current_program)
    
    # Send email if first run or changes detected
    if not previous_program or changes:
        send_email(current_program, changes)
    else:
        print("✅ Silent check - no email (no changes)")

if __name__ == "__main__":
    main()
