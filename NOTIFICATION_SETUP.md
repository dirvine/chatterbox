# macOS Notification Speaker Setup

Your Mac can now speak notifications aloud using ChatterBox TTS! 🎉

## Quick Start

### 1. Ensure ChatterBox TTS is running
```bash
python chatterbox_manager.py status
# If not running:
python chatterbox_manager.py start
```

### 2. Test the notification reader
```bash
# Run the notification reader
python notification_reader.py

# In another terminal, send a test notification
./send_test_notification.sh
```

### 3. Install as a system service (recommended)
```bash
# Easy one-command installation
./manage_notification_reader.sh install

# This will:
# - Install the LaunchAgent
# - Start the notification reader
# - Keep it running in the background
```

## Management Commands

Use the management script for easy control:

```bash
# Check status
./manage_notification_reader.sh status

# Start/stop/restart
./manage_notification_reader.sh start
./manage_notification_reader.sh stop
./manage_notification_reader.sh restart

# View logs
./manage_notification_reader.sh logs

# Run tests
./manage_notification_reader.sh test

# Uninstall
./manage_notification_reader.sh uninstall
```

## How It Works

1. **notification_reader.py** - Monitors macOS notifications using PyObjC
2. **ChatterBox TTS** - Converts notification text to speech
3. **LaunchAgent** - Keeps the service running automatically

## Customization

Edit `notification_reader.py` to customize:

- **SPEAK_APPS** - Which apps' notifications to speak
- **IGNORED_APPS** - Apps to never speak
- **format_for_speech()** - How notifications are announced

## Features

- ✅ Real-time notification monitoring
- ✅ Automatic text-to-speech conversion
- ✅ App-specific announcement formatting
- ✅ Duplicate notification prevention
- ✅ Background service with auto-restart
- ✅ Low resource usage
- ✅ Works offline - no internet required

## Supported Notifications

Currently speaks notifications from:
- Messages
- Mail  
- Slack
- Discord
- Calendar
- Reminders
- Terminal/iTerm
- VS Code
- Safari/Chrome/Firefox
- And more (customizable)

## Troubleshooting

If notifications aren't being spoken:

1. Check ChatterBox is running:
   ```bash
   curl http://127.0.0.1:8000/health
   ```

2. Check notification reader status:
   ```bash
   ./manage_notification_reader.sh status
   ```

3. Check logs:
   ```bash
   tail -f logs/notification_reader.log
   ```

4. Test manually:
   ```bash
   python test_notification.py
   ```

## Privacy Note

All processing happens locally on your Mac. No notification data leaves your machine.

## Uninstall

To completely remove the notification speaker:

```bash
./manage_notification_reader.sh uninstall
```

This only removes the notification reader. ChatterBox TTS service remains for other uses.