#!/bin/bash

echo "🎯 ChatterBox TTS Service Setup Summary"
echo "========================================"
echo ""

# Check service status
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ ChatterBox Service: RUNNING"
    if [ -f chatterbox.pid ]; then
        echo "   PID: $(cat chatterbox.pid)"
    fi
else
    echo "❌ ChatterBox Service: NOT RUNNING"
    echo "   To start: python chatterbox_manager.py start"
fi
echo ""

# Check hook installation
if [ -f ~/.claude/hooks/notify.py ]; then
    if grep -q "ChatterBox" ~/.claude/hooks/notify.py; then
        echo "✅ Claude Hook: INSTALLED (with auto-start)"
    else
        echo "⚠️  Claude Hook: OLD VERSION (no auto-start)"
        echo "   To update: cp notify_autostart.py ~/.claude/hooks/notify.py"
    fi
else
    echo "❌ Claude Hook: NOT INSTALLED"
    echo "   To install: cp notify_autostart.py ~/.claude/hooks/notify.py"
fi
echo ""

# Check logs
echo "📊 Recent Activity:"
if [ -f ~/.claude/logs/tts-hooks.log ]; then
    echo "Last 3 notifications:"
    tail -n 3 ~/.claude/logs/tts-hooks.log | sed 's/^/   /'
else
    echo "   No logs found"
fi
echo ""

echo "🚀 Quick Commands:"
echo "   Start service:  python chatterbox_manager.py start"
echo "   Stop service:   python chatterbox_manager.py stop"
echo "   Check status:   python chatterbox_manager.py status"
echo "   Test speech:    python test_service.py"
echo ""
echo "The service will auto-start when Claude Code starts a new session!"