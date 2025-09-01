# ChatterBox TTS Service

A local REST API service for text-to-speech synthesis using ChatterBox TTS, designed as a drop-in replacement for ElevenLabs API in Claude Code hooks.

## Features

- REST API for text-to-speech synthesis
- Direct audio playback through macOS sound system
- ElevenLabs API compatibility mode
- Can be used as a local alternative to cloud TTS services
- Zero-latency local processing

## Installation

```bash
# Install dependencies using uv
uv pip install -e .

# Or using pip
pip install fastapi uvicorn[standard] pydantic torchaudio chatterbox-tts
```

## Quick Start

### Run the service manually:
```bash
python tts_service.py
```

Or with custom settings:
```bash
python tts_service.py --host 0.0.0.0 --port 8080
```

### Run as a background service:
```bash
./start_service.sh
```

## API Endpoints

### 1. Simple Speech Synthesis
**POST** `/speak`
```json
{
  "text": "Hello, world!"
}
```
This endpoint immediately plays the audio through your Mac's speakers.

### 2. Advanced Synthesis
**POST** `/synthesize`
```json
{
  "text": "Hello, world!",
  "play": true,
  "return_audio": false,
  "audio_prompt_path": "/path/to/voice/sample.wav"
}
```

### 3. ElevenLabs Compatible
**POST** `/v1/text-to-speech/{voice_id}`
```json
{
  "text": "Hello, world!",
  "model_id": "eleven_turbo_v2_5",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.5
  }
}
```

### 4. Health Check
**GET** `/health`

Returns service status and model loading state.

## Using with Claude Code

### Option 1: Replace notify.py directly

Copy `notify_chatterbox.py` to `~/.claude/hooks/notify.py`:
```bash
cp notify_chatterbox.py ~/.claude/hooks/notify.py
```

### Option 2: Set environment variables

In your `.env` or shell configuration:
```bash
export USE_CHATTERBOX=true
export CHATTERBOX_URL=http://127.0.0.1:8000
```

The notify hook will automatically use ChatterBox when available and fall back to ElevenLabs if the service is not running.

## Running as a macOS Service

1. Copy the plist file to LaunchAgents:
```bash
cp com.chatterbox.tts.plist ~/Library/LaunchAgents/
```

2. Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.chatterbox.tts.plist
```

3. Start the service:
```bash
launchctl start com.chatterbox.tts
```

To stop:
```bash
launchctl stop com.chatterbox.tts
launchctl unload ~/Library/LaunchAgents/com.chatterbox.tts.plist
```

## Testing

Test the service with curl:
```bash
# Simple speak
curl -X POST http://127.0.0.1:8000/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from ChatterBox!"}'

# ElevenLabs compatible
curl -X POST http://127.0.0.1:8000/v1/text-to-speech/test-voice \
  -H "Content-Type: application/json" \
  -d '{"text": "Testing ElevenLabs compatibility"}'
```

## Configuration

The service uses ChatterBox TTS with MPS (Metal Performance Shaders) acceleration on macOS for fast synthesis.

To use a custom voice, provide an audio sample:
```python
# In your request
{
  "text": "Your text here",
  "audio_prompt_path": "/path/to/voice/sample.wav"
}
```

## Advantages over ElevenLabs

1. **No API costs** - Completely free to use
2. **No internet required** - Works offline
3. **Zero latency** - No network round-trip
4. **Privacy** - Your text never leaves your machine
5. **Unlimited usage** - No rate limits or quotas

## Troubleshooting

If the service doesn't start:
1. Check that Python 3.10+ is installed
2. Ensure all dependencies are installed: `uv pip install -e .`
3. Check logs in `logs/` directory
4. Verify port 8000 is not in use: `lsof -i :8000`

If audio doesn't play:
1. Ensure you're on macOS (uses `afplay`)
2. Check system audio settings
3. Test with: `afplay test-1.wav`

## License

See LICENSE file for details.