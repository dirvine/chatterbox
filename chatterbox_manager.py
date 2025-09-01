#!/usr/bin/env python3
"""
ChatterBox Service Manager
Manages the ChatterBox TTS service lifecycle
"""

import os
import sys
import time
import signal
import subprocess
import psutil
import requests
from pathlib import Path
from datetime import datetime

SERVICE_DIR = Path(__file__).parent
PID_FILE = SERVICE_DIR / "chatterbox.pid"
LOG_FILE = SERVICE_DIR / "logs" / "chatterbox.log"
ERROR_LOG = SERVICE_DIR / "logs" / "chatterbox.error.log"
SERVICE_URL = "http://127.0.0.1:8000"
SERVICE_SCRIPT = SERVICE_DIR / "tts_service.py"

def log(message):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")
    
    # Also write to log file
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")

def is_service_running():
    """Check if the service is running and responsive."""
    # First check if process exists
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if psutil.pid_exists(pid):
                # Process exists, check if it's our service
                try:
                    proc = psutil.Process(pid)
                    cmdline = ' '.join(proc.cmdline())
                    if 'tts_service.py' in cmdline:
                        # It's our service, check if responsive
                        try:
                            response = requests.get(f"{SERVICE_URL}/health", timeout=2)
                            if response.status_code == 200:
                                return True
                        except:
                            # Process exists but not responsive yet
                            return False
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            # PID exists but process doesn't or isn't ours
            PID_FILE.unlink()
        except (ValueError, IOError):
            PID_FILE.unlink()
    
    # Check if service is running without PID file (started manually)
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=1)
        if response.status_code == 200:
            log("Service is running (started externally)")
            return True
    except:
        pass
    
    return False

def wait_for_service(timeout=30):
    """Wait for service to become responsive."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{SERVICE_URL}/health", timeout=1)
            if response.status_code == 200:
                data = response.json()
                if data.get('model_loaded'):
                    return True
        except:
            pass
        time.sleep(0.5)
    return False

def start_service():
    """Start the ChatterBox service."""
    if is_service_running():
        log("Service is already running")
        return True
    
    log("Starting ChatterBox TTS service...")
    
    # Create logs directory
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Start the service in background
    with open(LOG_FILE, 'a') as stdout, open(ERROR_LOG, 'a') as stderr:
        process = subprocess.Popen(
            [sys.executable, str(SERVICE_SCRIPT), "--host", "127.0.0.1", "--port", "8000"],
            stdout=stdout,
            stderr=stderr,
            cwd=SERVICE_DIR,
            start_new_session=True
        )
    
    # Save PID
    PID_FILE.write_text(str(process.pid))
    log(f"Service started with PID {process.pid}")
    
    # Wait for service to be ready
    log("Waiting for service to be ready...")
    if wait_for_service():
        log("✅ ChatterBox TTS service is ready!")
        return True
    else:
        log("⚠️ Service started but not responsive yet")
        return False

def stop_service():
    """Stop the ChatterBox service."""
    if not PID_FILE.exists():
        log("No PID file found")
        return False
    
    try:
        pid = int(PID_FILE.read_text().strip())
        log(f"Stopping service with PID {pid}...")
        
        # Try graceful shutdown first
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
        except ProcessLookupError:
            log("Process already stopped")
            PID_FILE.unlink()
            return True
        
        # Check if still running
        if psutil.pid_exists(pid):
            # Force kill
            try:
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
            except ProcessLookupError:
                pass
        
        PID_FILE.unlink()
        log("Service stopped")
        return True
        
    except (ValueError, IOError) as e:
        log(f"Error stopping service: {e}")
        return False

def restart_service():
    """Restart the ChatterBox service."""
    log("Restarting service...")
    stop_service()
    time.sleep(2)
    return start_service()

def status():
    """Get service status."""
    if is_service_running():
        if PID_FILE.exists():
            pid = PID_FILE.read_text().strip()
            print(f"✅ ChatterBox TTS service is running (PID: {pid})")
        else:
            print("✅ ChatterBox TTS service is running (external)")
        
        try:
            response = requests.get(f"{SERVICE_URL}/health", timeout=2)
            data = response.json()
            print(f"   Model loaded: {data.get('model_loaded')}")
            print(f"   Status: {data.get('status')}")
        except:
            pass
    else:
        print("❌ ChatterBox TTS service is not running")

def ensure_running():
    """Ensure the service is running, start if not."""
    if not is_service_running():
        return start_service()
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ChatterBox Service Manager")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "ensure"],
                       help="Command to execute")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_service()
    elif args.command == "stop":
        stop_service()
    elif args.command == "restart":
        restart_service()
    elif args.command == "status":
        status()
    elif args.command == "ensure":
        ensure_running()