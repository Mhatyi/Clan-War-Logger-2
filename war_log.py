import os
import sys
import requests
from datetime import datetime

# ----------------- CONFIG -----------------
API_TOKEN = os.getenv("API_TOKEN")
CLAN_TAG = os.getenv("CLAN_TAG")
LOG_FILE = "war_log.md"

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
            -p.get("decksUsedToday", 0),
            -p.get("decksUsed", 0),
            -p.get("fame", 0),
            p.get("name", "").lower()
        )
    )

# ----------------- COLOSSEUM DETECTION -----------------
def is_colosseum_week(season, week):
    if season % 2 == 1:
        return week == 5
    else:
        return week == 4

# ----------------- SEASON/WEEK/DAY LOGIC -----------------
def parse_current_state(log):
    """Parse the current season, week, and day from the log."""
    if not log.strip():
        return 127, 1, 5, False  # FIRST RUN: Start at Day 5 → increments to 6 (Battle Day 3)
    
    lines = log.splitlines()
    
    # Find latest season (first one in file = newest)
    season = 127
    for line in lines:
        if line.startswith("# Season "):
            try:
                season = int(line.split("Season ")[1])
                break
            except:
                pass
    
    # Find latest week in that season
    week = 1
    is_colosseum = False
    in_season = False
    for line in lines:
        if f"# Season {season}" in line:
            in_season = True
        elif line.startswith("# Season "):
            in_season = False
        
        if in_season:
            if "## 🏟️ Colosseum Week" in line:
                week = 5
                is_colosseum = True
                break
            elif line.startswith("## Week "):
                try:
                    week = int(line.split("Week ")[1].split()[0])
                    break
                except:
                    pass
    
    # Find latest day in current week
    day = 0
    in_week = False
    for line in lines:
        if (is_colosseum and "## 🏟️ Colosseum Week" in line) or \
           (not is_colosseum and f"## Week {week}" in line):
            in_week = True
        elif line.startswith("## "):
            if in_week:
                break
        
        if in_week:
            if "Battle Days" in line and "🏟️" in line:
                day = 6
            elif "Battle Day " in line:
                try:
                    parts = line.split("Battle Day ")[1].split()
                    battle_day = int(parts[0])
                    day = max(day, battle_day + 3)
                except:
                    pass
            elif "Training Days" in line:
                day = max(day, 3)
    
    return season, week, day, is_colosseum

# ----------------- LOG HANDLING -----------------
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log = f.read()
else:
    log = ""

season, week, day, was_colosseum = parse_current_state(log)

# Increment day
day += 1

# Check week transitions
new_week = False
first_week = (season == 127 and week == 1)

if was_colosseum and day > 7:
    season += 1
    week = 1
    day = 1
    new_week = True
elif not was_colosseum and week == 1 and day > 7:
    week = 2
    day = 1
    new_week = True
elif not was_colosseum and week > 1 and day > 7:
    week += 1
    day = 1
    new_week = True

colosseum = is_colosseum_week(season, week)

date_str = datetime.utcnow().strftime("%Y-%m-%d")
participants = [
    p for p in war_data.get("clan", {}).get("participants", [])
    if p["tag"] in current_member_tags
]
sorted_players = sort_players(participants)

# ----------------- BUILD CURRENT WEEK CONTENT -----------------
current_week_content = {}

# Training Days (SKIP for first week only)
if day in TRAINING_DAYS and not first_week:
    training_content = []
    training_content.append("<details>\n")
    training_content.append("<summary>🎯 Training Days 1–3</summary>\n")
    training_content.append("\n| Player | Decks Used Today | Fame |\n")
    training_content.append("|-------|------------------|------|\n")
    for p in sorted_players:
        training_content.append(f"| {p['name']} | {p.get('decksUsedToday', 0)}/4 | {p.get('fame', 0)} |\n")
    training_content.append("</details>\n")
    current_week_content['training'] = training_content

# Battle Days
if day in [4, 5, 6, 7]:
    battle_day = day - 3
    
    if colosseum:
        # COLOSSEUM: Cumulative max decks (4, 8, 12, 16)
        max_decks = battle_day * 4
        battle_content = []
        battle_content.append("<details>\n")
        battle_content.append(f"<summary>🏟️ Battle Days 1–4 — {date_str}</summary>\n")
        battle_content.append("\n| Player | Decks Used Today | Fame |\n")
        battle_content.append("|-------|------------------|------|\n")
        for p in sorted_players:
            decks_today = p.get('decksUsedToday', 0)
            battle_content.append(f"| {p['name']} | {decks_today}/{max_decks} | {p.get('fame', 0)} |\n")
        battle_content.append("</details>\n")
        current_week_content['colosseum_battle'] = battle_content
    else:
        max_decks = 4
        battle_content = []
        battle_content.append("<details>\n")
        battle_content.append(f"<summary>⚔️ Battle Day {battle_day} — {date_str}</summary>\n")
        battle_content.append("\n| Player | Decks Used Today | Fame |\n")
        battle_content.append("|-------|------------------|------|\n")
        for p in sorted_players:
            decks_today = p.get('decksUsedToday', 0)
            battle_content.append(f"| {p['name']} | {decks_used_today}/{max_decks} | {p.get('fame', 0)} |\n")
        battle_content.append("</details>\n")
        
        if 'battles' not in current_week_content:
            current_week_content['battles'] = []
        current_week_content['battles'].append((battle_day, battle_content))

# ----------------- REBUILD ENTIRE LOG (REVERSED ORDER) -----------------
log_structure = {}
current_season = None
current_week = None
current_section = []

if log:
    lines = log.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if line.startswith("# Season "):
            if current_season and current_week:
                if current_season not in log_structure:
                    log_structure[current_season] = {}
                log_structure[current_season][current_week] = current_section
            
            try:
                current_season = int(line.split("Season ")[1])
                current_week = None
                current_section = []
            except:
                pass
        
        elif line.startswith("## "):
            if current_season and current_week:
                if current_season not in log_structure:
                    log_structure[current_season] = {}
                log_structure[current_season][current_week] = current_section
            
            if "🏟️ Colosseum Week" in line:
                current_week = "colosseum"
            elif "Week " in line:
                try:
                    current_week = int(line.split("Week ")[1].split()[0])
                except:
                    pass
            
            current_section = []
        
        else:
            if current_season is not None:
                current_section.append(line)
        
        i += 1
    
    if current_season and current_week:
        if current_season not in log_structure:
            log_structure[current_season] = {}
        log_structure[current_season][current_week] = current_section

if season not in log_structure:
    log_structure[season] = {}

current_week_key = "colosseum" if colosseum else week

week_lines = []

# Add battle days in REVERSE order
if 'battles' in current_week_content:
    sorted_battles = sorted(current_week_content['battles'], key=lambda x: x[0], reverse=True)
    for _, content in sorted_battles:
        week_lines.extend(content)
elif 'colosseum_battle' in current_week_content:
    week_lines.extend(current_week_content['colosseum_battle'])

# Add training days at the bottom
if 'training' in current_week_content:
    week_lines.extend(current_week_content['training'])

if current_week_key in log_structure[season]:
    existing_lines = log_structure[season][current_week_key]
    
    existing_battles = []
    existing_training = []
    i = 0
    
    while i < len(existing_lines):
        line = existing_lines[i]
        
        if line.startswith("<details>"):
            detail_block = [line]
            i += 1
            
            is_battle = False
            is_training = False
            battle_day_num = None
            
            while i < len(existing_lines):
                detail_block.append(existing_lines[i])
                
                if "Battle Day " in existing_lines[i] and "⚔️" in existing_lines[i]:
                    is_battle = True
                    try:
                        battle_day_num = int(existing_lines[i].split("Battle Day ")[1].split()[0])
                    except:
                        pass
                elif "Training Days" in existing_lines[i]:
                    is_training = True
                
                if existing_lines[i].strip() == "</details>":
                    i += 1
                    break
                i += 1
            
            if is_battle and battle_day_num and battle_day_num != (day - 3):
                existing_battles.append((battle_day_num, detail_block))
            elif is_training:
                existing_training = detail_block
        else:
            i += 1
    
    if 'battles' not in current_week_content:
        current_week_content['battles'] = []
    
    for battle_day_num, battle_lines in existing_battles:
        current_week_content['battles'].append((battle_day_num, battle_lines))
    
    week_lines = []
    if current_week_content.get('battles'):
        sorted_battles = sorted(current_week_content['battles'], key=lambda x: x[0], reverse=True)
        for _, content in sorted_battles:
            week_lines.extend(content)
    elif 'colosseum_battle' in current_week_content:
        week_lines.extend(current_week_content['colosseum_battle'])
    
    if 'training' in current_week_content:
        week_lines.extend(current_week_content['training'])
    elif existing_training:
        week_lines.extend(existing_training)

log_structure[season][current_week_key] = week_lines

# ----------------- WRITE FILE IN REVERSE ORDER -----------------
output_lines = []

sorted_seasons = sorted(log_structure.keys(), reverse=True)

for s in sorted_seasons:
    output_lines.append(f"# Season {s}\n")
    output_lines.append("")
    
    weeks = log_structure[s]
    
    week_keys = []
    for w in weeks.keys():
        if w == "colosseum":
            week_keys.append((99, w))
        else:
            week_keys.append((w, w))
    
    week_keys.sort(reverse=True)
    
    for _, week_key in week_keys:
        if week_key == "colosseum":
            output_lines.append("## 🏟️ Colosseum Week\n")
        else:
            output_lines.append(f"## Week {week_key}\n")
        
        output_lines.append("")
        output_lines.extend(weeks[week_key])
        output_lines.append("")

while output_lines and not output_lines[-1].strip():
    output_lines.pop()

# ----------------- WRITE FILE -----------------
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"✅ Logged Season {season}, Week {week}, Day {day} ({date_str})")
