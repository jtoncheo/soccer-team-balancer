import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from statistics import mean
import random

# --- Google Sheets Setup ---
@st.cache_resource

def get_gsheet_client():
    creds_dict = st.secrets["google"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        creds_dict,
        scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

SPREADSHEET_NAME = "SoccerRatings"
WORKSHEET_NAME = "Ratings"
POSITIONS = ["GK", "DEF", "MID", "FWD"]

# --- Load and Save ---
def load_data():
    gc = get_gsheet_client()
    sh = gc.open(SPREADSHEET_NAME)
    worksheet = sh.worksheet(WORKSHEET_NAME)

    rows = worksheet.get_all_values()[1:]  # Skip header
    data = {}
    for player, position, user, rating in rows:
        rating = int(rating)
        data.setdefault(player, {}).setdefault(position, {})[user] = rating
    return data

def save_rating(player, position, user, rating):
    gc = get_gsheet_client()
    sh = gc.open(SPREADSHEET_NAME)
    worksheet = sh.worksheet(WORKSHEET_NAME)

    rows = worksheet.get_all_values()
    updated = False

    for i, row in enumerate(rows[1:], start=2):  # start=2 to account for 1-based indexing and header
        if row[0] == player and row[1] == position and row[2] == user:
            worksheet.update_cell(i, 4, rating)
            updated = True
            break

    if not updated:
        worksheet.append_row([player, position, user, rating])

# --- Streamlit App UI ---
st.set_page_config(page_title="Soccer Player Ratings", layout="centered")
st.title("⚽ Soccer Player Rating App")

st.sidebar.header("Rate a Player")
user = st.sidebar.text_input("Your Name")
name_input = st.sidebar.text_input("Player Name")
ratings_input = {pos: st.sidebar.slider(pos, 1, 10, 5) for pos in POSITIONS}
submit = st.sidebar.button("Submit/Update Player")

if submit:
    if user.strip() == "" or name_input.strip() == "":
        st.sidebar.warning("⚠️ User and player name are required.")
    else:
        for pos in POSITIONS:
            save_rating(name_input, pos, user, ratings_input[pos])
        st.sidebar.success(f"✅ Player '{name_input}' saved by {user}.")
        st.rerun()

# --- Display Data ---
data = load_data()

st.header("📋 Player Ratings (Averages)")
if not data:
    st.info("No player data available.")
else:
    for player, positions in data.items():
        st.subheader(player)
        cols = st.columns(len(POSITIONS))
        for i, pos in enumerate(POSITIONS):
            ratings = positions.get(pos, {})
            if ratings:
                avg = round(mean(ratings.values()), 2)
                tooltip = ", ".join(f"{u}: {r}" for u, r in ratings.items())
                cols[i].metric(pos, avg, help=tooltip)
            else:
                cols[i].metric(pos, "N/A")

# --- Team Balancing ---
st.header("⚖️ Balanced Teams")

def compute_avg_rating(player_data):
    return mean(
        [mean(pos.values()) for pos in player_data.values() if pos]
    ) if player_data else 0

players = list(data.items())
players_with_avg = [(name, compute_avg_rating(positions)) for name, positions in players]
players_with_avg.sort(key=lambda x: x[1], reverse=True)

if len(players_with_avg) < 2:
    st.info("Need at least 2 players to form teams.")
else:
    random.shuffle(players_with_avg)
    team1, team2 = [], []
    team1_total, team2_total = 0, 0

    for player, rating in players_with_avg:
        if team1_total <= team2_total:
            team1.append((player, rating))
            team1_total += rating
        else:
            team2.append((player, rating))
            team2_total += rating

    st.subheader("Team 1")
    for p, r in team1:
        st.write(f"{p} - Avg Rating: {r:.2f}")

    st.subheader("Team 2")
    for p, r in team2:
        st.write(f"{p} - Avg Rating: {r:.2f}")

    st.markdown(f"**Total Rating - Team 1:** {team1_total:.2f}")
    st.markdown(f"**Total Rating - Team 2:** {team2_total:.2f}")
