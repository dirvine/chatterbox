#!/usr/bin/env python3
"""
macOS Notification Reader using PyObjC
Reads notifications in real-time and sends them to ChatterBox TTS.
"""

import time
import json
import requests
import logging
import sys
from pathlib import Path
from typing import Set
from datetime import datetime

try:
    from Foundation import NSObject, NSDistributedNotificationCenter
    from AppKit import NSWorkspace
    import objc
except ImportError:
    print("PyObjC not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyobjc-framework-Cocoa"])
    from Foundation import NSObject, NSDistributedNotificationCenter
    from AppKit import NSWorkspace
    import objc

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "notification_reader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CHATTERBOX_URL = "http://127.0.0.1:8000"
SPOKEN_CACHE_FILE = Path(__file__).parent / ".spoken_notifications.json"
MAX_CACHE_SIZE = 1000

# Apps to announce notifications from (customize this list)
SPEAK_APPS = {
    "Messages", "Mail", "Slack", "Discord", "Teams", "Telegram", 
    "WhatsApp", "Signal", "Calendar", "Reminders", "Notes",
    "Terminal", "iTerm", "Code", "Safari", "Chrome", "Firefox",
    "Finder", "System Preferences", "Activity Monitor"
}

# Notification types to speak
SPEAK_NOTIFICATION_TYPES = {
    "com.apple.message.notification",
    "com.apple.mail.notification",
    "com.apple.calendar.notification",
    "com.apple.reminders.notification",
}

class NotificationObserver(NSObject):
    def init(self):
        self = objc.super(NotificationObserver, self).init()
        if self is None:
            return None
        
        self.spoken_ids = self.load_spoken_cache()
        self.service_available = self.check_service()
        self.last_service_check = time.time()
        
        return self
    
    def load_spoken_cache(self) -> Set[str]:
        """Load previously spoken notification IDs."""
        if SPOKEN_CACHE_FILE.exists():
            try:
                with open(SPOKEN_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    return set(data.get("spoken_ids", [])[-MAX_CACHE_SIZE:])
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
        return set()
    
    def save_spoken_cache(self):
        """Save spoken notification IDs."""
        try:
            with open(SPOKEN_CACHE_FILE, 'w') as f:
                json.dump({"spoken_ids": list(self.spoken_ids)[-MAX_CACHE_SIZE:]}, f)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def check_service(self) -> bool:
        """Check if ChatterBox service is available."""
        try:
            response = requests.get(f"{CHATTERBOX_URL}/health", timeout=1)
            return response.status_code == 200 and response.json().get("model_loaded", False)
        except:
            return False
    
    def speak_text(self, text: str, app_name: str = "System") -> bool:
        """Send text to ChatterBox TTS service."""
        # Periodic service health check
        if time.time() - self.last_service_check > 30:
            self.service_available = self.check_service()
            self.last_service_check = time.time()
        
        if not self.service_available:
            return False
        
        try:
            # Format the text for speaking
            speak_text = self.format_for_speech(text, app_name)
            
            response = requests.post(
                f"{CHATTERBOX_URL}/speak",
                json={"text": speak_text},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Spoke: {app_name}: {text[:50]}...")
                return True
            else:
                logger.error(f"Failed to speak: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
            self.service_available = False
            return False
    
    def format_for_speech(self, text: str, app_name: str) -> str:
        """Format notification text for natural speech."""
        # Clean up common notification patterns
        text = text.replace("...", " ")
        text = text.replace("\n", ". ")
        
        # Add context based on app
        if app_name == "Messages":
            return f"New message: {text}"
        elif app_name == "Mail":
            return f"New email: {text}"
        elif app_name == "Calendar":
            return f"Calendar reminder: {text}"
        elif app_name == "Reminders":
            return f"Reminder: {text}"
        elif app_name == "Slack":
            return f"Slack message: {text}"
        else:
            return f"{app_name} says: {text}"
    
    def handleNotification_(self, notification):
        """Handle incoming notifications."""
        try:
            info = notification.userInfo()
            if not info:
                return
            
            # Extract notification details
            app_name = info.get("NSApplicationName", "Unknown")
            bundle_id = info.get("NSApplicationBundleIdentifier", "")
            title = info.get("Title", "")
            subtitle = info.get("Subtitle", "")
            message = info.get("Message", "")
            informative_text = info.get("InformativeText", "")
            
            # Create unique ID for this notification
            timestamp = str(time.time())
            notif_id = f"{bundle_id}_{timestamp}_{hash(title + message)}"
            
            # Check if we should speak this notification
            if notif_id in self.spoken_ids:
                return
            
            # Determine if we should speak this app's notifications
            should_speak = (
                app_name in SPEAK_APPS or
                bundle_id in SPEAK_NOTIFICATION_TYPES or
                any(t in notification.name() for t in ["Notification", "Alert", "Message"])
            )
            
            if not should_speak:
                logger.debug(f"Skipping notification from {app_name}")
                return
            
            # Combine notification text
            text_parts = []
            if title:
                text_parts.append(title)
            if subtitle:
                text_parts.append(subtitle)
            if message:
                text_parts.append(message)
            if informative_text and informative_text not in text_parts:
                text_parts.append(informative_text)
            
            full_text = ". ".join(text_parts)
            
            if full_text:
                logger.info(f"Notification from {app_name}: {full_text[:100]}...")
                
                if self.speak_text(full_text, app_name):
                    self.spoken_ids.add(notif_id)
                    
                    # Periodically save cache
                    if len(self.spoken_ids) % 10 == 0:
                        self.save_spoken_cache()
        
        except Exception as e:
            logger.error(f"Error handling notification: {e}")

def main():
    """Main entry point."""
    logger.info("Starting macOS Notification Reader...")
    
    # Create observer
    observer = NotificationObserver.alloc().init()
    
    if not observer.service_available:
        logger.error("ChatterBox service not available. Please start it first.")
        logger.info("Run: python chatterbox_manager.py start")
        sys.exit(1)
    
    # Announce startup
    observer.speak_text("Notification reader is now active", "System")
    
    # Get the distributed notification center
    center = NSDistributedNotificationCenter.defaultCenter()
    
    # Register for all notifications (we'll filter in the handler)
    center.addObserver_selector_name_object_(
        observer,
        objc.selector(observer.handleNotification_, signature=b'v@:@'),
        None,  # Listen to all notification names
        None   # From all objects
    )
    
    logger.info("Listening for notifications...")
    
    try:
        # Run the main loop
        from AppKit import NSRunLoop
        NSRunLoop.currentRunLoop().run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        center.removeObserver_(observer)
        observer.save_spoken_cache()
        sys.exit(0)

if __name__ == "__main__":
    main()