#!/usr/bin/env python3
"""
Test script for ChatterBox TTS Service
"""

import time
import requests
import subprocess
import sys

def test_service():
    """Test the ChatterBox TTS service."""
    
    # Check if service is running
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=1)
        if response.status_code == 200:
            print("✅ Service is already running")
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Model loaded: {data.get('model_loaded')}")
        else:
            print("❌ Service returned unexpected status:", response.status_code)
            return False
    except requests.exceptions.RequestException:
        print("❌ Service is not running")
        print("   Start it with: python tts_service.py")
        return False
    
    # Test the speak endpoint
    print("\n🔊 Testing speech synthesis...")
    test_text = "Hello David, this is ChatterBox TTS working locally on your Mac!"
    
    try:
        response = requests.post(
            "http://127.0.0.1:8000/speak",
            json={"text": test_text},
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Speech synthesis successful!")
            data = response.json()
            print(f"   {data.get('message')}")
            return True
        else:
            print(f"❌ Speech synthesis failed: {response.status_code}")
            print(f"   {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_elevenlabs_compatibility():
    """Test ElevenLabs compatibility endpoint."""
    print("\n🔄 Testing ElevenLabs compatibility...")
    
    try:
        response = requests.post(
            "http://127.0.0.1:8000/v1/text-to-speech/test-voice",
            json={
                "text": "Testing ElevenLabs compatible endpoint",
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ ElevenLabs compatibility working!")
            print(f"   Received audio: {len(response.content)} bytes")
            
            # Save and play the audio
            with open("test_elevenlabs.wav", "wb") as f:
                f.write(response.content)
            
            subprocess.run(["afplay", "test_elevenlabs.wav"], check=False)
            return True
        else:
            print(f"❌ ElevenLabs compatibility failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 ChatterBox TTS Service Test\n")
    
    # Test basic functionality
    if test_service():
        # Test ElevenLabs compatibility
        time.sleep(2)  # Wait a bit between audio plays
        test_elevenlabs_compatibility()
        
        print("\n✨ All tests completed!")
        print("\nTo use with Claude Code:")
        print("1. Keep the service running: python tts_service.py")
        print("2. Copy notify hook: cp notify_chatterbox.py ~/.claude/hooks/notify.py")
        print("3. Or set environment: export USE_CHATTERBOX=true")
    else:
        print("\n⚠️  Please start the service first:")
        print("   python tts_service.py")
        sys.exit(1)