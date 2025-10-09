#!/bin/bash
# Big Apple Rec Sports Backend Scripts
# Usage: source scripts.sh

export BACKEND_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

# npm-like commands
serve() {
    echo "🚀 Starting backend server..."
    cd "$BACKEND_DIR"
    python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
}

ngrok_tunnel() {
    echo "🌐 Starting ngrok tunnel..."
    pkill -f ngrok 2>/dev/null || true
    sleep 1
    ngrok http 8000
}

dev() {
    echo "🔧 Starting development environment..."
    cd "$BACKEND_DIR"
    pkill -f ngrok 2>/dev/null || true
    pkill -f uvicorn 2>/dev/null || true
    sleep 1
    
    echo "Starting backend server in background..."
    python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
    SERVER_PID=$!
    
    sleep 3
    echo "Starting ngrok tunnel..."
    ngrok http 8000 &
    TUNNEL_PID=$!
    
    echo "✅ Development environment started!"
    echo "📊 Server PID: $SERVER_PID"
    echo "📊 Tunnel PID: $TUNNEL_PID"
    echo "🔍 Check status with: status"
}

stop() {
    echo "🛑 Stopping all processes..."
    pkill -f ngrok 2>/dev/null || true
    pkill -f uvicorn 2>/dev/null || true
    echo "✅ All processes stopped"
}

status() {
    echo "📊 Process Status:"
    echo "=================="
    
    echo "Backend Server:"
    if pgrep -f uvicorn > /dev/null; then
        echo "✅ Running (PID: $(pgrep -f uvicorn))"
    else
        echo "❌ Not running"
    fi
    
    echo ""
    echo "Ngrok Tunnel:"
    if pgrep -f ngrok > /dev/null; then
        echo "✅ Running (PID: $(pgrep -f ngrok))"
    else
        echo "❌ Not running"
    fi
    
    echo ""
    echo "Ngrok URL:"
    URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['tunnels'][0]['public_url'] if data.get('tunnels') else '')" 2>/dev/null)
    if [ -n "$URL" ]; then
        echo "🌐 $URL"
    else
        echo "❌ No tunnel URL available"
    fi
}

url() {
    URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['tunnels'][0]['public_url'] if data.get('tunnels') else '')" 2>/dev/null)
    if [ -n "$URL" ]; then
        echo "🌐 Ngrok URL: $URL"
        echo "$URL" | pbcopy 2>/dev/null && echo "📋 URL copied to clipboard!"
    else
        echo "❌ No ngrok tunnel running"
    fi
}

test_api() {
    echo "🧪 Testing API endpoints..."
    echo "=========================="
    
    echo "Root endpoint:"
    curl -s http://127.0.0.1:8000/ | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "❌ Server not responding"
    
    echo ""
    echo "Leadership health:"
    curl -s http://127.0.0.1:8000/leadership/health | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "❌ Server not responding"
}

# Show available commands
help() {
    echo "🚀 Big Apple Rec Sports Backend Commands"
    echo "========================================="
    echo "serve      - Start the backend server"
    echo "ngrok_tunnel - Start ngrok tunnel"
    echo "dev        - Start both server and tunnel (background)"
    echo "stop       - Stop all running processes"
    echo "status     - Show process status"
    echo "url        - Get and copy ngrok URL"
    echo "test_api   - Test API endpoints"
    echo "help       - Show this help"
    echo ""
    echo "Quick Start:"
    echo "1. Run 'serve' in one terminal"
    echo "2. Run 'ngrok_tunnel' in another terminal"
    echo "3. Use 'url' to get the ngrok URL for Google Apps Script"
}

echo "✅ Backend scripts loaded! Type 'help' to see available commands." 