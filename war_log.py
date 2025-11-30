import os
import sys
import re
import requests
from datetime import datetime

# ---------------- CONFIG ----------------
API_TOKEN = os.getenv("API_TOKEN")
CLAN_TAG = os.getenv("CLAN_TAG")
LOG_FILE = "war_log.md"
STARTING_SEASON = 126  # initial season if none exists

# Optional proxy
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
PROXY_IP = os.getenv("PROXY_IP")
PROXY_PORT = os.getenv("PROXY_PORT")

# ---------------- VALIDATION ----------------
if not API_TOKEN:
    print("❌ API_TOKEN is missing! Please check your GitHub secret.")
    sys.exit(1)
if not CLAN_TAG:
    print("❌ CLAN_TAG is missing! Please check your GitHub secret.")
    sys.exit(1)

# ---------------- PROXIES ----------------
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

def replace_details_block(text, summary_title, new_block):
    pattern = r"<details>.*?<summary>\s*" + re.escape(summary_title) + r"\s*</summary>.*?</details>\s*"
    new_text, n = re.subn(pattern, new_block, text, flags=re.DOTALL | re.IGNORECASE)
    return new_text, n > 0

def first_summary_title(text):
    m = re.search(r"<summary>\s*(.*?)\s*</summary>", text, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None

def top_season_number(text):
    m = re.search(r"^#\s*Season\s+(\d+)", text, flags=re.MULTILINE | re.IGNORECASE)
    return int(m.group(1)) if m else None

def count_summaries_after(text, idx):
    sub = text[idx:]
    return len(re.findall(r"<summary>", sub, flags=re.IGNORECASE))

def index_of_top_season(text):
    m = re.search(r"^#\s*Season\s+\d+\s*$", text, flags=re.MULTILINE | re.IGNORECASE)
    return m.start() if m else None

# ---------------- FETCH DATA ----------------
members_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/members"
war_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/currentriverrace"

members_data = fetch_json(members_url)
war_data = fetch_json(war_url)

current_member_tags = {m['tag'] for m in members_data.get('items', [])}
date_str = datetime.utcnow().strftime("%Y-%m-%d")
period_type = war_data.get("periodType", "").lower()
is_colosseum = (period_type == "colosseum")

# ---------------- READ PREVIOUS LOG ----------------
previous_text = ""
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as fh:
        previous_text = fh.read()

existing_season = top_season_number(previous_text)
season_number = existing_season if existing_season is not None else STARTING_SEASON

prev_summary = first_summary_title(previous_text) if previous_text else None
prev_was_colosseum = prev_summary and ("colosseum" in prev_summary.lower() or "🏟" in prev_summary)
starting_new_season = prev_was_colosseum and not is_colosseum
if starting_new_season:
    season_number += 1

log_count_for_season = 0
if previous_text:
    season_idx = index_of_top_season(previous_text)
    if season_idx is None:
        log_count_for_season = previous_text.count("<summary>")
    else:
        m = re.search(r"^#\s*Season\s+\d+\s*$", previous_text, flags=re.MULTILINE | re.IGNORECASE)
        end_idx = m.end() if m else 0
        log_count_for_season = count_summaries_after(previous_text, end_idx)

if starting_new_season:
    log_count_for_season = 0

# ---------------- CYCLE DAY ----------------
starting_offset = 5  # Start at 6th battle day on first run
cycle_day = ((log_count_for_season + starting_offset) % 7) + 1  # 1..7
week_number = ((log_count_for_season + starting_offset) // 7) + 1

# ---------------- PARTICIPANTS ----------------
participants_raw = []
for p in war_data.get("clan", {}).get("participants", []):
    tag = p.get("tag")
    if tag not in current_member_tags:
        continue
    name = p.get("name", "Unknown")
    api_decks = int(p.get("decksUsed", 0) or 0)
    fame = int(p.get("fame", 0) or 0)
    participants_raw.append({"name": name, "api_decks": api_decks, "fame": fame})

# ---------------- BUILD TABLES ----------------
def build_colosseum_battle_table_text(participants):
    sorted_p = sorted(participants, key=lambda x: (x["api_decks"], x["fame"], x["name"].lower()), reverse=True)
    lines = [
        "| Player | Total Decks Used | Total Fame |",
        "|--------|------------------|------------|"
    ]
    for pp in sorted_p:
        lines.append(f"| {pp['name']} | {pp['api_decks']} | {pp['fame']} |")
    lines.append("\n")
    return "<details>\n<summary>🏟️ Colosseum Battle Table (Days 4–7) — " + date_str + "</summary>\n\n" + "\n".join(lines) + "\n</details>\n\n"

def build_daily_battle_table_text(participants, day_number):
    sorted_p = sorted(participants, key=lambda x: (x["api_decks"], x["fame"], x["name"].lower()), reverse=True)
    lines = [
        "| Player | Decks Used | Fame |",
        "|--------|------------|------|"
    ]
    for pp in sorted_p:
        lines.append(f"| {pp['name']} | {pp['api_decks']}/4 | {pp['fame']} |")
    lines.append("\n")
    title = f"⚔️ Battle Day {day_number} — {date_str}"
    return "<details>\n<summary>" + title + "</summary>\n\n" + "\n".join(lines) + "\n</details>\n\n", title

# ---------------- BUILD LOG ----------------
to_prepend = ""

# Season header
if starting_new_season or existing_season is None:
    to_prepend += f"# Season {season_number}\n\n"

# Week header
if is_colosseum:
    week_header_text = "## Colosseum Week\n\n"
else:
    week_header_text = f"## Week {week_number}\n\n"

week_header_present = False
if previous_text and not starting_new_season:
    season_idx = index_of_top_season(previous_text)
    search_area = previous_text[season_idx:] if season_idx is not None else previous_text
    if re.search(r"^##\s*(Week\s+\d+|Colosseum Week)\s*$", search_area, flags=re.MULTILINE | re.IGNORECASE):
        week_header_present = True
if not week_header_present:
    to_prepend += week_header_text

new_text = previous_text

# Only build the appropriate table for the current cycle day
if is_colosseum:
    colosseum_block = build_colosseum_battle_table_text(participants_raw)
    new_text, col_replaced = replace_details_block(new_text, "🏟️ Colosseum Battle Table (Days 4–7) — " + date_str, colosseum_block)
    if not col_replaced:
        new_text, col_replaced = replace_details_block(new_text, "🏟️ Colosseum Battle Table (Days 4–7)", colosseum_block)
    if not col_replaced:
        to_prepend += colosseum_block
else:
    if cycle_day >= 3:
        # Start logging from 3rd battle day
        day_number = cycle_day
        daily_block, daily_title = build_daily_battle_table_text(participants_raw, day_number)
        new_text, daily_replaced = replace_details_block(new_text, daily_title, daily_block)
        if not daily_replaced:
            to_prepend += daily_block

# ---------------- WRITE FILE ----------------
final_text = to_prepend + new_text
final_text = re.sub(r"(#\s*Season\s+\d+\s*\n\s*){2,}", r"\1", final_text, flags=re.IGNORECASE)

with open(LOG_FILE, "w", encoding="utf-8") as fh:
    fh.write(final_text)

if starting_new_season:
    print(f"✅ Started new Season {season_number} and updated logs (cycle_day={cycle_day}, week={week_number})")
else:
    print(f"✅ Updated war_log.md (cycle_day={cycle_day}, week={week_number}, periodType={period_type})")