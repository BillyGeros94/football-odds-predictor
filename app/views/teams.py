"""Teams: current ratings for every team, and one team's rating history and recent results."""
import altair as alt
import streamlit as st

import data
from style import COLOURS, LEAGUES, league_filter

st.title("Teams")
st.caption("Elo is one strength number per team, updated after every match. Both leagues share "
           "one scale, so teams keep their rating when promoted or relegated.")

ratings = data.team_ratings()
upcoming = data.upcoming()

# ---- Ratings table ----
leagues = league_filter("teams_league")
shown = ratings[ratings["league"].isin(leagues)].reset_index(drop=True)
shown.insert(0, "rank", range(1, len(shown) + 1))
shown["league"] = shown["league"].map(LEAGUES)
st.dataframe(
    shown[["rank", "team", "league", "elo", "gf5", "ga5", "sot5", "sota5"]],
    hide_index=True, width="stretch",
    column_config={
        "rank": "Rank", "team": "Team", "league": "League",
        "elo": st.column_config.ProgressColumn("Elo", format="%.0f", min_value=1100,
                                               max_value=float(ratings["elo"].max()) + 20),
        "gf5": st.column_config.NumberColumn("Goals for", format="%.1f", help="Per game, last 5 matches"),
        "ga5": st.column_config.NumberColumn("Goals against", format="%.1f", help="Per game, last 5 matches"),
        "sot5": st.column_config.NumberColumn("Shots on target", format="%.1f", help="Per game, last 5 matches"),
        "sota5": st.column_config.NumberColumn("Shots on target against", format="%.1f",
                                               help="Per game, last 5 matches"),
    },
)

# ---- One team ----
st.divider()
team = st.selectbox("Team", ratings["team"].sort_values())
row = ratings[ratings["team"] == team].iloc[0]
history = data.team_matches(row["team_id"])
league_table = ratings[ratings["league"] == row["league"]].reset_index(drop=True)

cols = st.columns(3)
change = row["elo"] - history["elo_before"].iloc[-5] if len(history) >= 5 else None
cols[0].metric("Elo", f"{row['elo']:.0f}",
               delta=f"{change:+.0f} over 5 matches" if change is not None else None)
cols[1].metric(f"Rank in the {LEAGUES[row['league']]}",
               int(league_table.index[league_table["team"] == team][0]) + 1)
cols[2].metric("Rank across both leagues", int(ratings.index[ratings["team"] == team][0]) + 1)

# Rating after every match, with a line at the start of each season
st.subheader(f"{team}'s rating since 2015/16")
season_starts = history.groupby("season", as_index=False)["match_date"].min()
line = (
    alt.Chart(history)
    .mark_line(color=COLOURS["Model"])
    .encode(
        x=alt.X("match_date:T", title=None),
        y=alt.Y("elo_after:Q", title="Elo", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("match_date:T", title="Date"), "opponent:N", "venue:N",
                 "scored:Q", "conceded:Q", alt.Tooltip("elo_after:Q", title="Elo", format=".0f")],
    )
)
starts = alt.Chart(season_starts).mark_rule(color="#cbd5e1", strokeDash=[4, 4]).encode(x="match_date:T")
st.altair_chart((starts + line).properties(height=320), width="stretch")
st.caption("Dashed lines mark the start of each season, when ratings are pulled 40% of the way "
           "back to the league average.")

# Last 10 matches
st.subheader("Last 10 matches")
last = history.sort_values("match_date", ascending=False).head(10).copy()
last["score"] = last["scored"].astype(str) + "–" + last["conceded"].astype(str)
last["change"] = last["elo_after"] - last["elo_before"]
st.dataframe(
    last[["match_date", "venue", "opponent", "score", "result", "elo_after", "change"]],
    hide_index=True, width="stretch",
    column_config={
        "match_date": st.column_config.DateColumn("Date", format="D MMM YYYY"),
        "venue": "H/A", "opponent": "Opponent", "score": "Score", "result": "W/D/L",
        "elo_after": st.column_config.NumberColumn("Elo after", format="%.0f"),
        "change": st.column_config.NumberColumn("Change", format="%+.1f"),
    },
)

# Next match, if predicted
upcoming_team = upcoming[(upcoming["home"] == team) | (upcoming["away"] == team)]
if not upcoming_team.empty:
    nxt = upcoming_team.iloc[0]
    st.subheader("Next match")
    st.markdown(f"**{nxt['home']} v {nxt['away']}**, {nxt['match_date']:%a %d %b}: "
                f"home {nxt['prob_home']:.0%} · draw {nxt['prob_draw']:.0%} · away {nxt['prob_away']:.0%}")
