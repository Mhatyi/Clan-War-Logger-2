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
    except requests.exceptions.RequestException as e:
        print(f"❌ Error while fetching {url}: {e}")
        sys.exit(1)

# ----------------- FETCH CLAN & WAR INFO -----------------

# 1️⃣ Get current clan members
members_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/members"
members_data = fetch_json(members_url)
current_member_tags = {m['tag'] for m in members_data.get('items', [])}

# 2️⃣ Get current war participants
war_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/currentriverrace"
war_data = fetch_json(war_url)

# ----------------- BUILD TABLE -----------------

date_str = datetime.utcnow().strftime("%Y-%m-%d")

report_lines = [
    f"| Player | Decks Used | Fame |",
    f"|--------|------------|------|"
]

# SORT: most decks used → least
for p in sorted(
    war_data.get("clan", {}).get("participants", []),
    key=lambda x: x.get("decksUsed", 0),
    reverse=True
):
    if p['tag'] in current_member_tags:
        name = p['name']
        decks_used = p.get("decksUsed", 0)
        fame = p.get("fame", 0)
        report_lines.append(f"| {name} | {decks_used}/4 | {fame} |")

report_lines.append("\n")

# ----------------- CUSTOM DAY SYSTEM -----------------

# Count previous entries
if not os.path.exists(LOG_FILE):
    log_count = 0
else:
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        text = f.read()
    log_count = text.count("<summary>")

# Tomorrow starts at Training Day 2
starting_offset = 1

# Determine cycle day (1–7)
cycle_day = ((log_count + starting_offset) % 7) + 1

# Label days
if cycle_day == 1:
    day_title = f"Training Day 1 — {date_str}"
elif cycle_day == 2:
    day_title = f"Training Day 2 — {date_str}"
elif cycle_day == 3:
    day_title = f"Training Day 3 — {date_str}"
elif cycle_day == 4:
    day_title = f"Battle Day 1 — {date_str}"
elif cycle_day == 5:
    day_title = f"Battle Day 2 — {date_str}"
elif cycle_day == 6:
    day_title = f"Battle Day 3 — {date_str}"
elif cycle_day == 7:
    day_title = f"Battle Day 4 — {date_str}"

# Week calculation
week_number = ((log_count + starting_offset) // 7) + 1

# Week header only when week STARTS
week_header = f"## Week {week_number}\n\n" if cycle_day == 1 else ""

# ----------------- COLLAPSIBLE ENTRY -----------------

collapsible_entry = (
    f"{week_header}"
    f"<details>\n"
    f"<summary>{day_title}</summary>\n\n"
    + "\n".join(report_lines) +
    "\n</details>\n\n"
)

# ----------------- PREPEND TO war_log.md -----------------

if log_count == 0:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(collapsible_entry)
    print("✅ Created war_log.md")
else:
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        old = f.read()
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(collapsible_entry + old)
    print(f"✅ Added new entry ({day_title})")