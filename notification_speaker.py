#!/usr/bin/env python3
"""
macOS Notification Speaker
Monitors macOS notifications and speaks them using ChatterBox TTS service.
"""

import time
import json
import requests
import subprocess
import sys
import os
import signal
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "notification_speaker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CHATTERBOX_URL = "http://127.0.0.1:8000"
CHECK_INTERVAL = 0.5  # seconds
SPOKEN_CACHE_FILE = Path(__file__).parent / ".spoken_notifications.json"
MAX_CACHE_SIZE = 1000
IGNORED_APPS = {"Finder", "System Preferences", "System Settings"}  # Apps to ignore

class NotificationSpeaker:
    def __init__(self):
        self.running = True
        self.spoken_ids: Set[str] = self.load_spoken_cache()
        self.last_notification = None
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
    
    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        logger.info("Shutting down notification speaker...")
        self.running = False
        self.save_spoken_cache()
        sys.exit(0)
    
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
        try:
            # Prepend app name for context
            full_text = f"{app_name}: {text}" if app_name != "System" else text
            
            response = requests.post(
                f"{CHATTERBOX_URL}/speak",
                json={"text": full_text},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Spoke notification from {app_name}")
                return True
            else:
                logger.error(f"Failed to speak: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
            return False
    
    def get_notifications_applescript(self) -> Optional[dict]:
        """Get notifications using AppleScript (fallback method)."""
        script = '''
        tell application "System Events"
            try
                set notificationList to {}
                set allNotifications to displayed notifications of notification center
                repeat with n in allNotifications
                    set notifRecord to {title:(title of n as string), subtitle:(subtitle of n as string), informativeText:(informative text of n as string)}
                    set end of notificationList to notifRecord
                end repeat
                return notificationList
            on error
                return {}
            end try
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                # Parse the AppleScript output
                # This is a simplified parser - actual implementation would need more robust parsing
                return {"notifications": []}
        except Exception as e:
            logger.debug(f"AppleScript notification check failed: {e}")
        
        return None
    
    def monitor_notification_db(self) -> Optional[dict]:
        """Monitor macOS notification database using terminal-notifier or similar."""
        # Check for terminal-notifier installation
        try:
            # Use log stream to monitor notifications
            process = subprocess.Popen(
                ['log', 'stream', '--predicate', 'eventMessage contains "notification"', '--style', 'json'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Read one line with timeout
            import select
            ready, _, _ = select.select([process.stdout], [], [], 0.1)
            if ready:
                line = process.stdout.readline()
                if line:
                    try:
                        log_entry = json.loads(line)
                        # Extract notification details from log
                        if "eventMessage" in log_entry:
                            return self.parse_log_notification(log_entry)
                    except json.JSONDecodeError:
                        pass
            
            process.terminate()
            
        except Exception as e:
            logger.debug(f"Log stream monitoring failed: {e}")
        
        return None
    
    def parse_log_notification(self, log_entry: dict) -> Optional[dict]:
        """Parse notification from log stream entry."""
        try:
            message = log_entry.get("eventMessage", "")
            # Extract app name and notification text from log message
            # This is a simplified parser - actual format may vary
            if "notification" in message.lower():
                return {
                    "app": log_entry.get("processImagePath", "").split("/")[-1].replace(".app", ""),
                    "text": message,
                    "timestamp": log_entry.get("timestamp", ""),
                    "id": f"{log_entry.get('timestamp', '')}_{hash(message)}"
                }
        except Exception as e:
            logger.debug(f"Failed to parse log notification: {e}")
        
        return None
    
    def run(self):
        """Main run loop."""
        logger.info("Starting macOS Notification Speaker...")
        
        if not self.check_service():
            logger.error("ChatterBox service not available. Please start it first.")
            return
        
        logger.info("ChatterBox service connected. Monitoring notifications...")
        
        # Speak startup message
        self.speak_text("Notification speaker is now active", "System")
        
        last_check = time.time()
        
        while self.running:
            try:
                # Check for new notifications
                notification = self.monitor_notification_db()
                
                if notification:
                    notif_id = notification.get("id")
                    app_name = notification.get("app", "System")
                    text = notification.get("text", "")
                    
                    # Check if we should speak this notification
                    if (notif_id and 
                        notif_id not in self.spoken_ids and 
                        app_name not in IGNORED_APPS and
                        text and len(text) > 0):
                        
                        # Speak the notification
                        if self.speak_text(text, app_name):
                            self.spoken_ids.add(notif_id)
                            
                            # Periodically save cache
                            if len(self.spoken_ids) % 10 == 0:
                                self.save_spoken_cache()
                
                # Periodic service health check
                if time.time() - last_check > 30:
                    if not self.check_service():
                        logger.warning("ChatterBox service not responding")
                    last_check = time.time()
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(1)
        
        self.save_spoken_cache()
        logger.info("Notification speaker stopped.")

def main():
    """Main entry point."""
    speaker = NotificationSpeaker()
    
    # Check if running as daemon
    if "--daemon" in sys.argv:
        # Detach from terminal
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork failed: {e}")
            sys.exit(1)
        
        # Create new session
        os.setsid()
        
        # Fork again for safety
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            logger.error(f"Second fork failed: {e}")
            sys.exit(1)
    
    speaker.run()

if __name__ == "__main__":
    main()