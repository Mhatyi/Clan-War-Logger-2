import os
import sys
import requests
from datetime import datetime

print("Current working directory:", os.getcwd())

# ----------------- CONFIG -----------------
API_TOKEN = os.getenv("API_TOKEN")
CLAN_TAG = os.getenv("CLAN_TAG")
LOG_FILE = "war_log.md"  # File to store daily logs

# Optional proxy
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
PROXY_IP = os.getenv("PROXY_IP")
PROXY_PORT = os.getenv("PROXY_PORT")

# ----------------- VALIDATION -----------------
if not API_TOKEN:
    print("❌ API_TOKEN is missing! Please check your GitHub secret.")
    sys.exit(1)

if not CLAN_TAG:
    print("❌ CLAN_TAG is missing! Please check your GitHub secret.")
    sys.exit(1)

# Setup proxies if provided
if PROXY_IP and PROXY_PORT:
    proxies = {
        "http": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}",
        "https": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}"
    }
else:
    proxies = None

# ----------------- REQUEST HEADERS -----------------
headers = {"Authorization": f"Bearer {API_TOKEN}"}

def fetch_json(url):
    """Fetch JSON data from Clash Royale API with error handling."""
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error while fetching {url}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error while fetching {url}: {e}")
    sys.exit(1)

# 1️⃣ Get current clan members
members_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/members"
members_data = fetch_json(members_url)
current_member_tags = {m['tag'] for m in members_data.get('items', [])}

# 2️⃣ Get current war participants
war_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/currentriverrace"
war_data = fetch_json(war_url)

# 3️⃣ Build log entry
date_str = datetime.utcnow().strftime("%Y-%m-%d")
report_lines = [
    f"## 📅 {date_str} — Clan War Deck Usage (Current Members Only)\n",
    "| Player | Decks Used | Fame |",
    "|--------|------------|------|"
]

for p in sorted(war_data.get("clan", {}).get("participants", []), key=lambda x: x["name"].lower()):
    if p['tag'] in current_member_tags:
        name = p['name']
        decks_used = p.get("decksUsed", 0)
        fame = p.get("fame", 0)
        report_lines.append(f"| {name} | {decks_used}/4 | {fame} |")

report_lines.append("\n")

# 4️⃣ Write or append to the markdown log file
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"✅ Created {LOG_FILE} and added entry for {date_str}")
else:
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        existing = f.read()
    if date_str not in existing:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        print(f"✅ Added new entry for {date_str}")
    else:
        print(f"ℹ️ Entry for {date_str} already exists — no update made.")
