#!/usr/bin/env python3
"""
Test script for notification reader.
Creates test notifications to verify the TTS integration.
"""

import subprocess
import time
import sys

def send_notification(title, message, subtitle=""):
    """Send a test notification using osascript."""
    script = f'''
    display notification "{message}" with title "{title}" subtitle "{subtitle}" sound name "Glass"
    '''
    
    try:
        subprocess.run(['osascript', '-e', script], check=True)
        print(f"✅ Sent notification: {title}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to send notification: {e}")
        return False

def main():
    """Run notification tests."""
    print("🧪 Testing ChatterBox Notification Reader\n")
    
    # Check if ChatterBox service is running
    try:
        import requests
        response = requests.get("http://127.0.0.1:8000/health", timeout=1)
        if response.status_code != 200 or not response.json().get("model_loaded"):
            print("❌ ChatterBox service not ready")
            print("   Run: python chatterbox_manager.py start")
            sys.exit(1)
    except:
        print("❌ ChatterBox service not running")
        print("   Run: python chatterbox_manager.py start")
        sys.exit(1)
    
    print("✅ ChatterBox service is running\n")
    
    # Send test notifications
    tests = [
        ("Test 1", "Hello", "This is a test notification from ChatterBox"),
        ("Test 2", "Email Alert", "You have 3 new emails"),
        ("Test 3", "Calendar", "Meeting in 15 minutes"),
        ("Test 4", "Reminder", "Don't forget to test the notification reader"),
        ("Test 5", "Message", "David says: The notification reader is working great!")
    ]
    
    print("Sending test notifications...\n")
    print("NOTE: Make sure notification_reader.py is running to hear them spoken!")
    print("      Run in another terminal: python notification_reader.py\n")
    
    for i, (subtitle, title, message) in enumerate(tests, 1):
        print(f"Test {i}/{len(tests)}:")
        if send_notification(title, message, subtitle):
            time.sleep(3)  # Wait between notifications
    
    print("\n✨ Test complete!")
    print("\nTo use continuously:")
    print("1. Keep ChatterBox service running: python chatterbox_manager.py start")
    print("2. Run notification reader: python notification_reader.py")
    print("\nTo install as system service:")
    print("1. cp com.chatterbox.notification-reader.plist ~/Library/LaunchAgents/")
    print("2. launchctl load ~/Library/LaunchAgents/com.chatterbox.notification-reader.plist")
    print("3. launchctl start com.chatterbox.notification-reader")

if __name__ == "__main__":
    main()