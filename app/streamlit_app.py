"""Football Odds Predictor app: the entry point that sets up the pages.

Run locally from the project folder:
    streamlit run app/streamlit_app.py
"""
import streamlit as st

st.set_page_config(page_title="Football Odds Predictor", page_icon="⚽", layout="wide")

pages = [
    st.Page("views/upcoming.py", title="Upcoming matches", icon=":material/event:", default=True),
    st.Page("views/live_record.py", title="Live record", icon=":material/insights:"),
    st.Page("views/season.py", title="Season predictions", icon=":material/emoji_events:"),
    st.Page("views/teams.py", title="Teams", icon=":material/groups:"),
    st.Page("views/performance.py", title="Model performance", icon=":material/analytics:"),
]

with st.sidebar:
    st.caption("Premier League and Championship win, draw and loss probabilities, "
               "updated every Monday and Thursday.")
    st.caption("[Code and method on GitHub](https://github.com/BillyGeros94/football-odds-predictor)")

st.navigation(pages).run()
