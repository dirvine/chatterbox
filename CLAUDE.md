# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ChatterBox TTS Service - A local text-to-speech REST API service that provides a drop-in replacement for ElevenLabs API, designed for use with Claude Code hooks and local TTS synthesis.

## Architecture

The service is built with:
- **FastAPI** for the REST API framework
- **ChatterBox TTS** model for speech synthesis with MPS (Metal Performance Shaders) acceleration on macOS
- **Python 3.10+** with virtual environment management via `uv`
- **Process management** with systemd-style service controls

### Key Components

1. **tts_service.py** - Main FastAPI service providing TTS endpoints
   - `/speak` - Simple text-to-speech with immediate playback
   - `/synthesize` - Advanced synthesis with options for voice cloning
   - `/v1/text-to-speech/{voice_id}` - ElevenLabs-compatible endpoint
   - `/health` - Service health check

2. **chatterbox_manager.py** - Service lifecycle manager
   - Handles start/stop/restart/status operations
   - PID file management at `chatterbox.pid`
   - Logging to `logs/` directory

3. **notify_chatterbox.py** - Claude Code hook replacement
   - Drop-in replacement for ElevenLabs notifications
   - Fallback support when ChatterBox service isn't running

## Development Commands

### Install Dependencies
```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -r requirements.txt  # if exists, otherwise install from pyproject.toml
```

### Run Service
```bash
# Direct run
python tts_service.py

# With custom settings
python tts_service.py --host 0.0.0.0 --port 8080 --reload

# Using startup script
./start_service.sh

# Using service manager
python chatterbox_manager.py start
```

### Service Management
```bash
# Start service
python chatterbox_manager.py start

# Stop service
python chatterbox_manager.py stop

# Restart service
python chatterbox_manager.py restart

# Check status
python chatterbox_manager.py status

# Ensure running (start if not)
python chatterbox_manager.py ensure
```

### Testing
```bash
# Run test suite
python test_service.py

# Test specific endpoint with curl
curl -X POST http://127.0.0.1:8000/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message"}'

# Test ElevenLabs compatibility
curl -X POST http://127.0.0.1:8000/v1/text-to-speech/test-voice \
  -H "Content-Type: application/json" \
  -d '{"text": "Test ElevenLabs compatibility"}'
```

### macOS Service Installation
```bash
# Install as LaunchAgent
cp com.chatterbox.tts.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.chatterbox.tts.plist
launchctl start com.chatterbox.tts

# Uninstall
launchctl stop com.chatterbox.tts
launchctl unload ~/Library/LaunchAgents/com.chatterbox.tts.plist
```

## Environment Setup

The project uses Python 3.10+ with a virtual environment at `.venv/`. Dependencies are managed via `uv` package manager.

### Key Environment Variables
- `USE_CHATTERBOX=true` - Enable ChatterBox in Claude Code hooks
- `CHATTERBOX_URL=http://127.0.0.1:8000` - Service URL (default)

## File Structure

- `tts_service.py` - Main FastAPI service
- `chatterbox_manager.py` - Service lifecycle manager  
- `notify_chatterbox.py` - Claude Code hook replacement
- `notify_autostart.py` - Auto-start variant of notify hook
- `test_service.py` - Service test suite
- `start_service.sh` - Startup script with dependency installation
- `com.chatterbox.tts.plist` - macOS LaunchAgent configuration
- `logs/` - Service logs directory
- `.venv/` - Python virtual environment

## Audio Processing

- Uses `torchaudio` for WAV file generation
- `afplay` command for macOS audio playback
- Optional `ffmpeg` for MP3 conversion (ElevenLabs compatibility)
- Temporary files cleaned up automatically after playback

## API Response Formats

The service returns either:
- JSON responses with status messages
- Audio files (WAV/MP3) for download
- Background audio playback with cleanup

## Error Handling

- Service health checks via `/health` endpoint
- Automatic retry logic in manager
- Graceful shutdown with SIGTERM/SIGKILL handling
- Comprehensive logging to `logs/chatterbox.log` and `logs/chatterbox.error.log`

## Integration with Claude Code

To use as Claude Code notification hook:
1. Ensure service is running: `python chatterbox_manager.py ensure`
2. Copy hook: `cp notify_chatterbox.py ~/.claude/hooks/notify.py`
3. Or set environment: `export USE_CHATTERBOX=true`

The service provides zero-latency, offline TTS as a free alternative to ElevenLabs API.