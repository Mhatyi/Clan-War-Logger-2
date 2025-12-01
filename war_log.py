# war_log.py
import os
import sys
import re
import requests
from datetime import datetime

# ---------------- CONFIG ----------------
API_TOKEN = os.getenv("API_TOKEN")
CLAN_TAG = os.getenv("CLAN_TAG")
LOG_FILE = "war_log.md"
STARTING_SEASON = 127

# Optional proxy
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
PROXY_IP = os.getenv("PROXY_IP")
PROXY_PORT = os.getenv("PROXY_PORT")

# Validations
if not API_TOKEN:
    print("❌ API_TOKEN is missing! Please check your GitHub secret.")
    sys.exit(1)
if not CLAN_TAG:
    print("❌ CLAN_TAG is missing! Please check your GitHub secret.")
    sys.exit(1)

# Proxies
if PROXY_IP and PROXY_PORT:
    proxies = {
        "http": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}",
        "https": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}"
    }
else:
    proxies = None

headers = {"Authorization": f"Bearer {API_TOKEN}"}

# ---------------- HELPERS ----------------

def fetch_json(url):
    try:
        r = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching {url}: {e}")
        sys.exit(1)

# replace first <details> block whose summary content equals summary_title
def replace_details_block(text, summary_title, new_block):
    pattern = r"<details>.*?<summary>\s*" + re.escape(summary_title) + r"\s*</summary>.*?</details>\s*"
    new_text, n = re.subn(pattern, new_block, text, flags=re.DOTALL | re.IGNORECASE)
    return new_text, n > 0

# find first match object for a week header (either "## Week X" or "## Colosseum Week")
def find_week_header_match(text, week_number, is_colosseum):
    if is_colosseum:
        pat = r"^##\s*Colosseum\s+Week\s*$"
    else:
        pat = rf"^##\s*Week\s+{week_number}\s*$"
    return re.search(pat, text, flags=re.MULTILINE | re.IGNORECASE)

# find training block match after an index
def find_training_block_match_after(text, start_idx):
    pattern = r"<details>.*?<summary>\s*🎯\s*Training\s*Days\s*\(1–3\).*?</details>\s*"
    return re.search(pattern, text[start_idx:], flags=re.DOTALL | re.IGNORECASE)

# find generic training block anywhere
def find_training_block_match(text):
    pattern = r"<details>.*?<summary>\s*🎯\s*Training\s*Days\s*\(1–3\).*?</details>\s*"
    return re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)

# find the first summary title (newest)
def first_summary_title(text):
    m = re.search(r"<summary>\s*(.*?)\s*</summary>", text, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None

# extract topmost season number
def top_season_number(text):
    m = re.search(r"^#\s*Season\s+(\d+)", text, flags=re.MULTILINE | re.IGNORECASE)
    return int(m.group(1)) if m else None

# find index of topmost season header
def index_of_top_season(text):
    m = re.search(r"^#\s*Season\s+\d+\s*$", text, flags=re.MULTILINE | re.IGNORECASE)
    return m.start() if m else None

# count summaries after index
def count_summaries_after(text, idx):
    sub = text[idx:]
    return len(re.findall(r"<summary>", sub, flags=re.IGNORECASE))

# parse a table row like "| Name | 3/4 | 120 |" and return decks (int) if found
def parse_decks_from_row(row_text):
    m = re.search(r"^\|\s*[^|]+\|\s*(\d+)\s*/\s*4\s*\|", row_text)
    if m:
        return int(m.group(1))
    return None

# get most recent logged decksUsed number for a player from previous_text
def get_most_recent_logged_decks(name, prev_text):
    # search top-down; file is newest-first so first match is most recent
    pattern = rf"^\|\s*{re.escape(name)}\s*\|\s*(\d+)\s*/\s*4\s*\|"
    match = re.search(pattern, prev_text, flags=re.MULTILINE)
    if match:
        try:
            return int(match.group(1))
        except:
            return None
    return None

# ---------------- FETCH DATA ----------------
members_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/members"
war_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/currentriverrace"

members_data = fetch_json(members_url)
war_data = fetch_json(war_url)

current_member_tags = {m['tag'] for m in members_data.get('items', [])}
date_str = datetime.utcnow().strftime("%Y-%m-%d")
period_type = war_data.get("periodType", "").lower()
is_colosseum = (period_type == "colosseum")

# ---------------- READ EXISTING LOG ----------------
previous_text = ""
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        previous_text = f.read()

existing_season = top_season_number(previous_text)
season_number = existing_season if existing_season is not None else STARTING_SEASON

prev_summary = first_summary_title(previous_text) if previous_text else None
prev_was_colosseum = prev_summary and ("colosseum" in prev_summary.lower() or "🏟" in prev_summary)
starting_new_season = prev_was_colosseum and not is_colosseum
if starting_new_season:
    season_number += 1

# compute how many day entries in the current season (summaries after top season header)
if previous_text:
    season_idx = index_of_top_season(previous_text)
    if season_idx is None:
        log_count_for_season = previous_text.count("<summary>")
    else:
        m = re.search(r"^#\s*Season\s+\d+\s*$", previous_text, flags=re.MULTILINE | re.IGNORECASE)
        end_idx = m.end() if m else 0
        log_count_for_season = count_summaries_after(previous_text, end_idx)
else:
    log_count_for_season = 0

if starting_new_season:
    log_count_for_season = 0

# ---------------- CYCLE DAY ----------------
# start at Training Day 1 on first run
starting_offset = 0
cycle_day = ((log_count_for_season + starting_offset) % 7) + 1  # 1..7
week_number = ((log_count_for_season + starting_offset) // 7) + 1

# ---------------- PARTICIPANTS ----------------
participants = []
for p in war_data.get("clan", {}).get("participants", []):
    tag = p.get("tag")
    if tag not in current_member_tags:
        continue
    name = p.get("name", "Unknown")
    api_decks = int(p.get("decksUsed", 0) or 0)
    fame = int(p.get("fame", 0) or 0)
    participants.append({"name": name, "api_decks": api_decks, "fame": fame})

# ---------------- BUILD TABLES ----------------

def build_training_block(participants):
    # Training block uses API totals directly, sorted decks->fame->name
    sorted_p = sorted(participants, key=lambda x: (x["api_decks"], x["fame"], x["name"].lower()), reverse=True)
    lines = ["| Player | Decks Used | Fame |", "|--------|------------|------|"]
    for p in sorted_p:
        lines.append(f"| {p['name']} | {p['api_decks']}/4 | {p['fame']} |")
    lines.append("\n")
    return "<details>\n<summary>🎯 Training Days (1–3) — " + date_str + "</summary>\n\n" + "\n".join(lines) + "\n</details>\n\n"

def build_battle_block_normal(participants, day_number):
    sorted_p = sorted(participants, key=lambda x: (x["api_decks"], x["fame"], x["name"].lower()), reverse=True)
    lines = ["| Player | Decks Used | Fame |", "|--------|------------|------|"]
    for p in sorted_p:
        lines.append(f"| {p['name']} | {p['api_decks']}/4 | {p['fame']} |")
    lines.append("\n")
    title = f"⚔️ Battle Day {day_number} — {date_str}"
    return "<details>\n<summary>" + title + "</summary>\n\n" + "\n".join(lines) + "\n</details>\n\n", title

def build_battle_block_colosseum(participants, day_number, prev_text):
    # For colosseum days we use subtraction method to estimate day's decks
    processed = []
    for p in participants:
        name = p["name"]
        api_decks = p["api_decks"]
        fame = p["fame"]
        prev_logged = get_most_recent_logged_decks(name, prev_text) if prev_text else None
        if prev_logged is not None:
            delta = api_decks - prev_logged
            if 0 <= delta <= 4:
                daily = delta
            else:
                # fallback: cap to 4 or use api_decks if small
                daily = max(0, min(api_decks, 4))
        else:
            # no previous record: cap at api_decks or 4
            daily = max(0, min(api_decks, 4))
        processed.append({"name": name, "daily": daily, "fame": fame})
    sorted_p = sorted(processed, key=lambda x: (x["daily"], x["fame"], x["name"].lower()), reverse=True)
    lines = ["| Player | Decks Used | Fame |", "|--------|------------|------|"]
    for p in sorted_p:
        lines.append(f"| {p['name']} | {p['daily']}/4 | {p['fame']} |")
    lines.append("\n")
    title = f"🏟️ Battle Day {day_number} — {date_str}"
    return "<details>\n<summary>" + title + "</summary>\n\n" + "\n".join(lines) + "\n</details>\n\n", title

# ---------------- INSERT / REPLACE LOGIC ----------------

# new content to prepend if needed
to_prepend = ""

# season header
if starting_new_season or existing_season is None:
    to_prepend += f"# Season {season_number}\n\n"

# week header (colosseum label if applicable)
if is_colosseum:
    week_header_text = "## Colosseum Week\n\n"
else:
    week_header_text = f"## Week {week_number}\n\n"

# check if week header already present in current season area
week_present = False
if previous_text and not starting_new_season:
    # find top season index and search after it
    season_idx = index_of_top_season(previous_text)
    search_area = previous_text[season_idx:] if season_idx is not None else previous_text
    if re.search(r"^##\s*(Week\s+\d+|Colosseum Week)\s*$", search_area, flags=re.MULTILINE | re.IGNORECASE):
        # ensure the specific header for this week isn't already present
        # If colosseum, ensure Colosseum Week exists; if not colosseum, check Week N
        if is_colosseum and re.search(r"^##\s*Colosseum\s+Week\s*$", search_area, flags=re.MULTILINE | re.IGNORECASE):
            week_present = True
        elif (not is_colosseum) and re.search(rf"^##\s*Week\s+{week_number}\s*$", search_area, flags=re.MULTILINE | re.IGNORECASE):
            week_present = True

if not week_present:
    to_prepend += week_header_text

# Prepare training block (we always ensure one training block exists for the week)
training_block = build_training_block(participants)

# Replace today's dated training block if present, else replace generic training block
new_text = previous_text
new_text, replaced = replace_details_block(new_text, "🎯 Training Days (1–3) — " + date_str, training_block)
if not replaced:
    new_text, replaced = replace_details_block(new_text, "🎯 Training Days (1–3)", training_block)
if not replaced:
    # attempt to insert training block under week header (if present) or prepend later
    # We'll insert after week header if it exists
    header_match = find_week_header_match(new_text, week_number, is_colosseum)
    if header_match:
        # find if training block exists after the header - if so we would have replaced it above, so otherwise insert after header
        insert_pos = header_match.end()
        new_text = new_text[:insert_pos] + training_block + new_text[insert_pos:]
    else:
        # will prepend with to_prepend
        to_prepend += training_block

# Handle battle days
# If colosseum -> create separate colosseum-day tables (4 of them across the week) using subtraction
# If normal week -> create per-day battle table using API totals
if is_colosseum:
    if cycle_day >= 4:
        # day_number in 4..7 maps to battle day index: day_number - 3 => Battle Day 1..4 but we keep day_number for labeling consistency
        day_number = cycle_day
        block, title = build_battle_block_colosseum(participants, day_number, previous_text)
        # try to replace existing today's block
        new_text, replaced = replace_details_block(new_text, title, block)
        if not replaced:
            # insert into week: place above training block if training exists under the same week
            header_match = find_week_header_match(new_text, week_number, is_colosseum)
            if header_match:
                # search for training block after header
                tr_match = find_training_block_match_after(new_text, header_match.end())
                if tr_match:
                    # tr_match is relative to header_match.end(); compute absolute span
                    abs_start = header_match.end() + tr_match.start()
                    abs_end = header_match.end() + tr_match.end()
                    # replace training block with (battle block + training block)
                    new_text = new_text[:abs_start] + block + new_text[abs_start:abs_end] + new_text[abs_end:]
                else:
                    # no training block found in this week area — insert after header
                    insert_pos = header_match.end()
                    new_text = new_text[:insert_pos] + block + new_text[insert_pos:]
            else:
                # no header found (new season likely) -> will prepend
                to_prepend += block
else:
    # normal week
    if cycle_day >= 4:
        day_number = cycle_day
        block, title = build_battle_block_normal(participants, day_number)
        new_text, replaced = replace_details_block(new_text, title, block)
        if not replaced:
            header_match = find_week_header_match(new_text, week_number, is_colosseum=False)
            if header_match:
                tr_match = find_training_block_match_after(new_text, header_match.end())
                if tr_match:
                    abs_start = header_match.end() + tr_match.start()
                    abs_end = header_match.end() + tr_match.end()
                    new_text = new_text[:abs_start] + block + new_text[abs_start:abs_end] + new_text[abs_end:]
                else:
                    insert_pos = header_match.end()
                    new_text = new_text[:insert_pos] + block + new_text[insert_pos:]
            else:
                to_prepend += block

# Compose final text
final_text = to_prepend + new_text
final_text = re.sub(r"(#\s*Season\s+\d+\s*\n\s*){2,}", r"\1", final_text, flags=re.IGNORECASE)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(final_text)

if starting_new_season:
    print(f"✅ Started new Season {season_number} and updated logs (cycle_day={cycle_day}, week={week_number})")
else:
    print(f"✅ Updated war_log.md (cycle_day={cycle_day}, week={week_number}, periodType={period_type})")