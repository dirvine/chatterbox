#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
# ]
# ///
"""
Claude Code Notification Hook with ChatterBox TTS Support
Uses local ChatterBox TTS service if available, falls back to ElevenLabs
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# Configuration
CHATTERBOX_URL = os.environ.get('CHATTERBOX_URL', 'http://127.0.0.1:8000')
USE_CHATTERBOX = os.environ.get('USE_CHATTERBOX', 'true').lower() == 'true'

# ElevenLabs configuration (fallback)
def get_api_key():
    """Get API key from multiple possible sources."""
    key = os.environ.get('ELEVENLABS_API_KEY')
    if key:
        return key
    
    env_file = Path.home() / '.env'
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('ELEVENLABS_API_KEY='):
                        key = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if key:
                            return key
        except:
            pass
    
    claude_env = Path.home() / '.claude' / '.env'
    if claude_env.exists():
        try:
            with open(claude_env, 'r') as f:
                for line in f:
                    if line.startswith('ELEVENLABS_API_KEY='):
                        key = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if key:
                            return key
        except:
            pass
    
    return None

ELEVENLABS_API_KEY = get_api_key()
VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', 'EXAVITQu4vr4xnSDxMaL')

# Debug log
DEBUG_LOG = Path.home() / '.claude' / 'logs' / 'tts-hooks.log'
DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)

def log_debug(message):
    """Log debug messages."""
    with open(DEBUG_LOG, 'a') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] {message}\n")

def speak_with_chatterbox(text: str) -> bool:
    """Use local ChatterBox TTS service to speak the notification."""
    try:
        import requests
        
        # Check if service is running
        try:
            health_response = requests.get(f"{CHATTERBOX_URL}/health", timeout=1)
            if health_response.status_code != 200:
                log_debug(f"ChatterBox service not healthy: {health_response.status_code}")
                return False
        except:
            log_debug("ChatterBox service not available")
            return False
        
        # Send text to ChatterBox service
        url = f"{CHATTERBOX_URL}/speak"
        data = {
            "text": text,
            "play": True
        }
        
        log_debug(f"Sending to ChatterBox: {text}")
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            log_debug("ChatterBox synthesis successful")
            return True
        else:
            log_debug(f"ChatterBox error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        log_debug(f"ChatterBox error: {e}")
        return False

def speak_with_elevenlabs(text: str) -> bool:
    """Use ElevenLabs API to speak the notification (fallback)."""
    if not ELEVENLABS_API_KEY:
        log_debug("No ElevenLabs API key found")
        return False
    
    try:
        import requests
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        data = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        log_debug(f"Falling back to ElevenLabs")
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            try:
                result = subprocess.run(['afplay', temp_path], capture_output=True, timeout=30)
                if result.returncode == 0:
                    log_debug("Audio played successfully via ElevenLabs")
                else:
                    log_debug(f"afplay failed with code {result.returncode}")
            except Exception as e:
                log_debug(f"Error playing ElevenLabs audio: {e}")
            finally:
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            return True
        else:
            log_debug(f"ElevenLabs API error: {response.status_code}")
            return False
            
    except Exception as e:
        log_debug(f"ElevenLabs error: {e}")
        return False

def speak_notification(text: str) -> bool:
    """Speak notification using ChatterBox or ElevenLabs."""
    if USE_CHATTERBOX:
        # Try ChatterBox first
        if speak_with_chatterbox(text):
            return True
        # Fall back to ElevenLabs if ChatterBox fails
        log_debug("ChatterBox failed, trying ElevenLabs")
    
    return speak_with_elevenlabs(text)

def get_project_name():
    """Get the project directory name."""
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
    return Path(project_dir).name

def main():
    """Process notification event based on hook type."""
    try:
        event_data = {}
        hook_type = os.environ.get('CLAUDE_HOOK_TYPE', 'unknown')
        
        if not sys.stdin.isatty():
            try:
                input_data = sys.stdin.read()
                if input_data:
                    event_data = json.loads(input_data)
                    log_debug(f"Received event data: {event_data}")
            except:
                pass
        
        project = get_project_name()
        
        # Check for compact event
        is_compact = False
        if hook_type == 'SessionStart' or 'SessionStart' in str(event_data.get('hook_event_name', '')):
            source = event_data.get('source', '').lower()
            if 'compact' in source or 'compaction' in source or ':compact' in hook_type.lower():
                is_compact = True
                log_debug(f"Detected compaction event")
        
        # Determine message based on hook type
        if 'message' in event_data:
            message = event_data['message']
            if "waiting for your input" in message.lower():
                message = f"David, I need your help in {project}"
        elif is_compact:
            message = f"David, we have compacted the context window in {project}"
        elif hook_type == 'SessionStart' or 'SessionStart' in str(event_data.get('hook_event_name', '')):
            source = event_data.get('source', 'unknown')
            if source == 'startup':
                message = f"David, I am ready to work on {project}"
            elif source == 'resume':
                message = f"David, I am resuming work on {project}"
            elif source == 'clear':
                message = f"David, I have cleared the context and am ready for {project}"
            else:
                message = f"David, I am ready to work on {project}"
        elif hook_type == 'SubagentStop' or 'SubagentStop' in str(event_data.get('hook_event_name', '')):
            message = f"David, the subagent has completed its work in {project}, moving on now"
        elif hook_type == 'Notification' or 'Notification' in str(event_data.get('hook_event_name', '')):
            message = f"David, I need your help in {project}"
        elif hook_type == 'Stop' or 'Stop' in str(event_data.get('hook_event_name', '')):
            message = f"David, I have completed my work in {project}"
        elif hook_type == 'PreCompact' or 'PreCompact' in str(event_data.get('hook_event_name', '')):
            message = f"David, preparing to compact the context window in {project}"
        else:
            message = f"David, Claude needs your input in {project}"
        
        log_debug(f"Message to speak: {message}")
        
        # Speak the notification
        if speak_notification(message):
            log_debug(f"Hook executed successfully - Type: {hook_type}, Project: {project}")
        else:
            log_debug(f"Hook executed but audio failed - Type: {hook_type}, Project: {project}")
        
        sys.exit(0)
        
    except Exception as e:
        log_debug(f"Error in main: {e}")
        import traceback
        log_debug(f"Traceback: {traceback.format_exc()}")
        sys.exit(0)

if __name__ == "__main__":
    main()