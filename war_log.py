import os
import sys
import requests
from datetime import datetime

# ----------------- CONFIG -----------------
API_TOKEN = os.getenv("API_TOKEN")
CLAN_TAG = os.getenv("CLAN_TAG")
LOG_FILE = "war_log.md"

# Force first run to start on a battle day (day 4)
FIRST_RUN_START_AT_BATTLE = True

# Days 1–3 are training (single shared table)
TRAINING_DAYS = [1, 2, 3]

# ----------------- VALIDATION -----------------
if not API_TOKEN:
    print("❌ API_TOKEN is missing!")
    sys.exit(1)

if not CLAN_TAG:
    print("❌ CLAN_TAG is missing!")
    sys.exit(1)

# ----------------- REQUEST HEADERS -----------------
headers = {"Authorization": f"Bearer {API_TOKEN}"}

# ----------------- PROXY SETUP -----------------
PROXY_USERNAME = os.getenv("PROXY_USERNAME", "")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "")
PROXY_IP = os.getenv("PROXY_IP", "")
PROXY_PORT = os.getenv("PROXY_PORT", "")

proxy_string = ""

if PROXY_IP and PROXY_PORT:
    if PROXY_USERNAME and PROXY_PASSWORD:
        proxy_string = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}"
    else:
        proxy_string = f"http://{PROXY_IP}:{PROXY_PORT}"

proxies = {
    "http": proxy_string,
    "https": proxy_string
} if proxy_string else None


# ----------------- REQUEST FUNCTION (with proxy) -----------------
def fetch_json(url):
    try:
        response = requests.get(url, headers=headers, timeout=10, proxies=proxies)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        print(f"❌ HTTP Status: {response.status_code} for {url}")
        print(f"❌ Response body: {response.json()}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error fetching {url}")
        sys.exit(1)


# ----------------- DATA FETCH -----------------
members_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/members"
war_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/currentriverrace"

members_data = fetch_json(members_url)
war_data = fetch_json(war_url)

current_member_tags = {m['tag'] for m in members_data.get('items', [])}


# ----------------- SORTING FUNCTION -----------------
def sort_players(participants):
    return sorted(
        participants,
        key=lambda p: (
            -p.get("decksUsed", 0),
            -p.get("fame", 0),
            p.get("name", "").lower()
        )
    )


# ----------------- DAY INDEXING -----------------
def get_day_index(log, season, week):
    existing = []

    for line in log.splitlines():
        if "Day " in line:
            try:
                part = line.split("Day ")[1]
                d_str = part.split()[0]
                existing.append(int(d_str))
            except:
                pass

    if not existing:
        return 4 if FIRST_RUN_START_AT_BATTLE else 1

    return max(existing) + 1


# ----------------- DETECT COLOSSEUM -----------------
def is_colosseum_week():
    try:
        period = war_data.get("periodIndex", 0)
        return period >= 3
    except:
        return False


# ----------------- BUILD LOG ENTRY -----------------
date_str = datetime.utcnow().strftime("%Y-%m-%d")

if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log = f.read()
else:
    log = ""

season = 127
week = 1

day = get_day_index(log, season, week)
col = is_colosseum_week()

output = []


# ----------------- HEADER GENERATION -----------------
if f"Season {season}" not in log:
    output.append(f"# Season {season}\n")

if col:
    header = f"## 🏛️ Colosseum Week"
else:
    header = f"## Week {week}"

if header not in log:
    output.append(header + "\n")


# ----------------- TRAINING / BATTLE TABLE LOGIC -----------------
participants = [
    p for p in war_data.get("clan", {}).get("participants", [])
    if p["tag"] in current_member_tags
]

sorted_players = sort_players(participants)


# TRAINING DAYS (single table for days 1–3)
if not col and day in TRAINING_DAYS:
    if "### 🎯 Training Days 1–3" not in log:
        output.append("### 🎯 Training Days 1–3\n")
        output.append("<details>\n<summary>Open Training Table</summary>\n")
        output.append("| Player | Decks Used | Fame |")
        output.append("|-------|------------|------|")
        for p in sorted_players:
            output.append(f"| {p['name']} | {p.get('decksUsed', 0)}/4 | {p.get('fame', 0)} |")
        output.append("</details>\n")

    entry = ""

else:
    emoji = "🏛️" if col else "⚔️"
    output.append(f"### {emoji} Day {day} — {date_str}")
    output.append("| Player | Decks Used | Fame |")
    output.append("|-------|------------|------|")
    for p in sorted_players:
        output.append(f"| {p['name']} | {p.get('decksUsed', 0)}/4 | {p.get('fame', 0)} |")
    output.append("")


# ----------------- WRITE TO FILE -----------------
with open(LOG_FILE, "a", encoding="utf-8") as f:
    f.write("\n".join(output))

print(f"✅ Logged Day {day} ({date_str})")
