import os
import sys
import requests
from datetime import datetime

# ----------------- CONFIG -----------------
API_TOKEN = os.getenv("API_TOKEN")
CLAN_TAG = os.getenv("CLAN_TAG")
LOG_FILE = "war_log.md"

TRAINING_DAYS = [1, 2, 3]  # single shared table

# ----------------- VALIDATION -----------------
if not API_TOKEN:
    print("❌ API_TOKEN is missing!")
    sys.exit(1)

if not CLAN_TAG:
    print("❌ CLAN_TAG is missing!")
    sys.exit(1)

# ----------------- REQUEST HEADERS -----------------
headers = {"Authorization": f"Bearer {API_TOKEN}"}

# Optional proxy
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

proxies = {"http": proxy_string, "https": proxy_string} if proxy_string else None

# ----------------- FETCH FUNCTIONS -----------------
def fetch_json(url):
    try:
        response = requests.get(url, headers=headers, timeout=10, proxies=proxies)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed to {url}: {e}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error: {e}")
        sys.exit(1)

# ----------------- DATA FETCH -----------------
members_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/members"
war_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/currentriverrace"

members_data = fetch_json(members_url)
war_data = fetch_json(war_url)

current_member_tags = {m["tag"] for m in members_data.get("items", [])}

# ----------------- SORTING -----------------
def sort_players(participants):
    return sorted(
        participants,
        key=lambda p: (
            -p.get("decksUsed", 0),
            -p.get("fame", 0),
            p.get("name", "").lower()
        )
    )

# ----------------- DAY INDEX -----------------
def get_day_index(log):
    existing = []
    for line in log.splitlines():
        if "Day " in line:
            try:
                part = line.split("Day ")[1]
                d_str = part.split()[0]
                existing.append(int(d_str))
            except:
                pass
    # FIRST RUN SPECIAL CASE
    if not existing:
        return 2  # start first run at Battle Day 2
    return max(existing) + 1

# ----------------- COLOSSEUM DETECTION -----------------
def is_colosseum_week(season, week):
    # Pattern: odd season → week 5, even season → week 4
    if season % 2 == 1:
        return week == 5
    else:
        return week == 4

# ----------------- LOG HANDLING -----------------
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log = f.read()
else:
    log = ""

season = 127  # start season
week = 1
day = get_day_index(log)
colosseum = is_colosseum_week(season, week)

date_str = datetime.utcnow().strftime("%Y-%m-%d")
participants = [
    p for p in war_data.get("clan", {}).get("participants", [])
    if p["tag"] in current_member_tags
]
sorted_players = sort_players(participants)

output = []

# ----------------- SEASON / WEEK HEADERS -----------------
if f"Season {season}" not in log:
    output.append(f"# Season {season}\n")

week_header = f"## 🏟️ Colosseum Week" if colosseum else f"## Week {week}"
if week_header not in log:
    output.append(week_header + "\n")

# ----------------- TRAINING DAYS -----------------
if not colosseum and day in TRAINING_DAYS:
    if "### 🎯 Training Days 1–3" not in log:
        output.append("### 🎯 Training Days 1–3\n")
        output.append("<details>\n<summary>Open Training Table</summary>\n")
        output.append("| Player | Decks Used | Fame |")
        output.append("|-------|------------|------|")
        for p in sorted_players:
            output.append(f"| {p['name']} | {p.get('decksUsed', 0)}/4 | {p.get('fame', 0)} |")
        output.append("</details>\n")
    # DO NOT CREATE TABLES FOR DAY 2 OR 3
    entry = ""
else:
    # ----------------- BATTLE / COLOSSEUM DAYS -----------------
    if colosseum:
        # Subtraction method for table numbering
        first_battle_day_of_colosseum = day - (day % 4) + 1
        col_day_num = day - first_battle_day_of_colosseum + 1
        emoji = "🏟️"
        output.append(f"### {emoji} Day {col_day_num} — {date_str}")
    else:
        emoji = "⚔️"
        output.append(f"### {emoji} Day {day} — {date_str}")

    output.append("| Player | Decks Used | Fame |")
    output.append("|-------|------------|------|")
    for p in sorted_players:
        output.append(f"| {p['name']} | {p.get('decksUsed',0)}/4 | {p.get('fame',0)} |")
    output.append("")

# ----------------- WRITE FILE -----------------
with open(LOG_FILE, "a", encoding="utf-8") as f:
    f.write("\n".join(output))

print(f"✅ Logged Day {day} ({date_str})")
