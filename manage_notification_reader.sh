#!/bin/bash

# ChatterBox Notification Reader Manager
# Manages the notification reader service

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_NAME="com.chatterbox.notification-reader"
PLIST_FILE="$SCRIPT_DIR/$PLIST_NAME.plist"
LAUNCHAGENT_DIR="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCHAGENT_DIR/$PLIST_NAME.plist"

function check_chatterbox() {
    # Check if ChatterBox TTS service is running
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "✅ ChatterBox TTS service is running"
        return 0
    else
        echo "❌ ChatterBox TTS service is not running"
        echo "   Start it first: python chatterbox_manager.py start"
        return 1
    fi
}

function install() {
    echo "Installing ChatterBox Notification Reader..."
    
    # Check if ChatterBox is running
    if ! check_chatterbox; then
        exit 1
    fi
    
    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$LAUNCHAGENT_DIR"
    
    # Copy plist file
    cp "$PLIST_FILE" "$INSTALLED_PLIST"
    echo "✅ Installed plist to $INSTALLED_PLIST"
    
    # Load the service
    launchctl load "$INSTALLED_PLIST"
    echo "✅ Loaded service"
    
    # Start the service
    launchctl start "$PLIST_NAME"
    echo "✅ Started notification reader"
    
    echo ""
    echo "🎉 ChatterBox Notification Reader is now active!"
    echo "   Your Mac notifications will now be spoken aloud."
}

function uninstall() {
    echo "Uninstalling ChatterBox Notification Reader..."
    
    # Stop the service
    launchctl stop "$PLIST_NAME" 2>/dev/null
    
    # Unload the service
    launchctl unload "$INSTALLED_PLIST" 2>/dev/null
    
    # Remove plist file
    rm -f "$INSTALLED_PLIST"
    
    echo "✅ ChatterBox Notification Reader has been uninstalled"
}

function start() {
    if ! check_chatterbox; then
        exit 1
    fi
    
    launchctl start "$PLIST_NAME"
    echo "✅ Started notification reader"
}

function stop() {
    launchctl stop "$PLIST_NAME"
    echo "✅ Stopped notification reader"
}

function restart() {
    stop
    sleep 1
    start
}

function status() {
    echo "ChatterBox Notification Reader Status:"
    echo ""
    
    # Check ChatterBox service
    check_chatterbox
    echo ""
    
    # Check if plist is installed
    if [ -f "$INSTALLED_PLIST" ]; then
        echo "✅ Service is installed"
        
        # Check if loaded
        if launchctl list | grep -q "$PLIST_NAME"; then
            echo "✅ Service is loaded"
            
            # Get PID if running
            PID=$(launchctl list | grep "$PLIST_NAME" | awk '{print $1}')
            if [ "$PID" != "-" ]; then
                echo "✅ Service is running (PID: $PID)"
            else
                echo "❌ Service is not running"
            fi
        else
            echo "❌ Service is not loaded"
        fi
    else
        echo "❌ Service is not installed"
    fi
}

function test() {
    echo "Testing notification reader..."
    
    if ! check_chatterbox; then
        exit 1
    fi
    
    # Run test script
    python3 "$SCRIPT_DIR/test_notification.py"
}

function logs() {
    echo "Showing notification reader logs..."
    echo ""
    
    LOG_FILE="$SCRIPT_DIR/logs/notification_reader.log"
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "No log file found at $LOG_FILE"
    fi
}

# Main menu
case "$1" in
    install)
        install
        ;;
    uninstall)
        uninstall
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    test)
        test
        ;;
    logs)
        logs
        ;;
    *)
        echo "ChatterBox Notification Reader Manager"
        echo ""
        echo "Usage: $0 {install|uninstall|start|stop|restart|status|test|logs}"
        echo ""
        echo "Commands:"
        echo "  install   - Install and start the notification reader"
        echo "  uninstall - Stop and remove the notification reader"
        echo "  start     - Start the notification reader"
        echo "  stop      - Stop the notification reader"
        echo "  restart   - Restart the notification reader"
        echo "  status    - Show current status"
        echo "  test      - Run test notifications"
        echo "  logs      - Show live logs"
        echo ""
        echo "Quick start:"
        echo "  1. Make sure ChatterBox is running: python chatterbox_manager.py start"
        echo "  2. Install notification reader: $0 install"
        echo "  3. Test it: $0 test"
        exit 1
        ;;
esac