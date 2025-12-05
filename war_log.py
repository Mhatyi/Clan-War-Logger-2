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


# =======================================================
# DIAGNOSTIC FETCH FUNCTION (NEW!)
# =======================================================
def fetch_json(url):
    """Fetch JSON with detailed error diagnostics."""
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed to {url}")
        print(f"   {type(e).__name__}: {e}")
        sys.exit(1)

    # If not 200 OK, print detailed server info
    if response.status_code != 200:
        print(f"❌ HTTP Status: {response.status_code} for {url}")
        try:
            data = response.json()
            print(f"❌ Response body: {data}")
        except:
            print(f"❌ Raw text: {response.text}")
        sys.exit(1)

    return response.json()
# =======================================================


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
            -p.get("decksUsed", 0),     # highest decks first
            -p.get("fame", 0),          # highest fame next
            p.get("name", "").lower()   # A→Z (final tie-break)
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

    # FIRST RUN SPECIAL CASE
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

# Get existing log
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log = f.read()
else:
    log = ""

season = 127  # start from season 127
week = 1      # start from week 1
day = get_day_index(log, season, week)
col = is_colosseum_week()

# ----------------- HEADER GENERATION -----------------
output = []

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
    # create training table once
    if "### 🎯 Training Days 1–3" not in log:
        output.append("### 🎯 Training Days 1–3\n")
        output.append("<details>\n<summary>Open Training Table</summary>\n")
        output.append("| Player | Decks Used | Fame |")
        output.append("|-------|------------|------|")
        for p in sorted_players:
            output.append(f"| {p['name']} | {p.get('decksUsed', 0)}/4 | {p.get('fame', 0)} |")
        output.append("</details>\n")

    # do NOT write new training tables
    entry = ""

else:
    # BATTLE DAYS
    emoji = "🏛️" if col else "⚔️"
    output.append(f"### {emoji} Day {day} — {date_str}")
    output.append("| Player | Decks Used | Fame |")
    output.append("|-------|------------|------|")
    for p in sorted_players:
        output.append(f"| {p['name']} | {p.get('decksUsed', 0)}/4 | {p.get('fame', 0)} |")
    output.append("")  # newline


# ----------------- WRITE TO FILE -----------------
with open(LOG_FILE, "a", encoding="utf-8") as f:
    f.write("\n".join(output))

print(f"✅ Logged Day {day} ({date_str})")
