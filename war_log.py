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

# 3️⃣ Build report lines
date_str = datetime.utcnow().strftime("%Y-%m-%d")
report_lines = [
    f"| Player | Decks Used | Fame |",
    f"|--------|------------|------|"
]

for p in sorted(war_data.get("clan", {}).get("participants", []), key=lambda x: x["name"].lower()):
    if p['tag'] in current_member_tags:
        name = p['name']
        decks_used = p.get("decksUsed", 0)
        fame = p.get("fame", 0)
        report_lines.append(f"| {name} | {decks_used}/4 | {fame} |")

report_lines.append("\n")

# ----------------- WEEK + COLLAPSIBLE DAY LOGIC -----------------

# Determine war day number
if not os.path.exists(LOG_FILE):
    day_number = 1
else:
    # Count collapsible "summary>" lines already present
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        text = f.read()
    day_number = text.count("<summary>") + 1

# Determine week number
week_number = (day_number - 1) // 7 + 1
day_in_week = (day_number - 1) % 7 + 1  # 1–7 inside week

# Day label rules
if day_in_week in (5, 6, 7):
    summary_title = f"Training Day — {date_str}"
else:
    summary_title = f"Day {day_number} — {date_str}"

# Build collapsible markdown entry
week_header = f"## Week {week_number}\n\n" if day_in_week == 1 else ""

collapsible_entry = (
    f"{week_header}"
    f"<details>\n"
    f"<summary>{summary_title}</summary>\n\n"
    + "\n".join(report_lines) +
    "\n</details>\n\n"
)

# Prepend to top of file
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(collapsible_entry)
    print(f"✅ Created {LOG_FILE} with Day {day_number}")
else:
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        old = f.read()

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(collapsible_entry + old)

    print(f"✅ Prepended Day {day_number} to top of {LOG_FILE}")
