import os
print("Current working directory:", os.getcwd())
import requests
from datetime import datetime
import os

# ----------------- CONFIG -----------------
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjQ5YjRkYmQ1LWRkMDUtNGQwNS05NzVhLTAxOTEyNDY3ZDY1OCIsImlhdCI6MTc2MTE2MTM4MCwic3ViIjoiZGV2ZWxvcGVyL2M2ZGUwMTQxLTQxNmQtOGJmMy02YzViLTNlNzQ1MWY4MWRkOCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxNDIuMTExLjQ4LjI1MyJdLCJ0eXBlIjoiY2xpZW50In1dfQ.nNASqJA5zlBTade8CcJPLwd6EkMbb9Cj6KCMhzgNdcpzgDcpsNQbAVqXYG9KxENbHlB7nll228WNh1DHIZsw8Q"      # Clash Royale API token
CLAN_TAG = "QJQLJG9R"        # Clan tag without the #
LOG_FILE = "war_log.md"                # File to store daily logs

# Webshare proxy settings
PROXY_USERNAME = "dwojxhku"
PROXY_PASSWORD = "i1eooh7kmncw"
PROXY_IP = "142.111.48.253"
PROXY_PORT = "7030"

proxies = {
    "http": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}",
    "https": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}"
}
# ------------------------------------------

headers = {"Authorization": f"Bearer {API_TOKEN}"}

# 1️⃣ Get current clan members (filter out kicked members)
members_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/members"
try:
    response = requests.get(members_url, headers=headers, proxies=proxies)
    response.raise_for_status()
    members_data = response.json()
except Exception as e:
    print(f"❌ Error fetching clan members: {e}")
    exit(1)

current_member_tags = {m['tag'] for m in members_data['items']}

# 2️⃣ Get current war participants
war_url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/currentriverrace"
try:
    response = requests.get(war_url, headers=headers, proxies=proxies)
    response.raise_for_status()
    war_data = response.json()
except Exception as e:
    print(f"❌ Error fetching war data: {e}")
    exit(1)

date_str = datetime.utcnow().strftime("%Y-%m-%d")
report_lines = []

# Header
report_lines.append(f"## 📅 {date_str} — Clan War Deck Usage (Current Members Only)")
report_lines.append("")
report_lines.append("| Player | Decks Used | Fame |")
report_lines.append("|--------|------------|------|")

# Log only participants who are still in the clan
for p in sorted(war_data["clan"]["participants"], key=lambda x: x["name"].lower()):
    if p['tag'] in current_member_tags:
        name = p['name']
        decks_used = p.get("decksUsed", 0)
        fame = p.get("fame", 0)
        report_lines.append(f"| {name} | {decks_used}/4 | {fame} |")

report_lines.append("\n")

# Append or write to file
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