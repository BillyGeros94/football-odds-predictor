"""Football Odds Predictor app: the entry point that sets up the pages.

Run locally from the project folder:
    streamlit run app/streamlit_app.py
"""
import random
from datetime import date

import streamlit as st

st.set_page_config(page_title="Football Odds Predictor · Premier League and Championship probabilities",
                   page_icon=":material/sports_soccer:", layout="wide")

# -------------------------
# Christmas theme: blinking lights along the top and gentle snowfall, on its own from
# 1 December to 6 January. Clicks pass through; reduced-motion settings are respected.
# -------------------------

LIGHT_COLOURS = ["#e53935", "#fdd835", "#43a047", "#1e88e5", "#fb8c00"]


def is_festive(today=None):
    """True from 1 December to 6 January."""
    today = today or date.today()
    return today.month == 12 or (today.month == 1 and today.day <= 6)


def _lights_html(n_bulbs=40):
    bulbs = "".join(
        f'<span class="xmas-bulb" style="background:{c};color:{c};animation-delay:{(i % 5) * 0.3:.1f}s"></span>'
        for i, c in enumerate(LIGHT_COLOURS[i % len(LIGHT_COLOURS)] for i in range(n_bulbs))
    )
    return f'<div class="xmas-lights">{bulbs}</div>'


def _snow_html(n_flakes=25):
    rng = random.Random(7)  # fixed seed: flakes keep their places when Streamlit reruns
    flakes = []
    for _ in range(n_flakes):
        left = rng.uniform(0, 100)
        size = rng.uniform(0.6, 1.3)
        duration = rng.uniform(9, 18)
        delay = -rng.uniform(0, 18)  # negative delay: snow is already falling on page load
        opacity = rng.uniform(0.4, 0.9)
        flakes.append(
            f'<span class="xmas-flake" style="left:{left:.1f}vw;font-size:{size:.2f}rem;'
            f'opacity:{opacity:.2f};animation-duration:{duration:.1f}s,{duration / 3:.1f}s;'
            f'animation-delay:{delay:.1f}s,{delay:.1f}s">❄</span>'
        )
    return f'<div class="xmas-snow">{"".join(flakes)}</div>'


_CSS = """
<style>
/* lights along the top edge, above Streamlit's header; clicks pass through */
.xmas-lights {
    position: fixed; top: 0; left: 0; width: 100%; height: 22px;
    display: flex; justify-content: space-around; align-items: flex-start;
    border-top: 2px solid #2e3b2e;
    pointer-events: none; z-index: 1000001;
}
.xmas-bulb {
    width: 9px; height: 13px; margin-top: 3px;
    border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
    box-shadow: 0 2px 10px 2px currentColor;
    animation: xmas-blink 1.5s ease-in-out infinite alternate;
}
@keyframes xmas-blink {
    from { opacity: 1; }
    to   { opacity: 0.25; box-shadow: none; }
}

/* falling snow over the whole page; clicks pass through */
.xmas-snow {
    position: fixed; inset: 0; overflow: hidden;
    pointer-events: none; z-index: 1000000;
}
.xmas-flake {
    position: absolute; top: -2rem;
    color: #b3d4f5; text-shadow: 0 0 3px rgba(255, 255, 255, 0.8);
    animation-name: xmas-fall, xmas-sway;
    animation-timing-function: linear, ease-in-out;
    animation-iteration-count: infinite, infinite;
    animation-direction: normal, alternate;
}
@keyframes xmas-fall {
    to { top: 105vh; }
}
@keyframes xmas-sway {
    from { transform: translateX(-15px); }
    to   { transform: translateX(15px); }
}

/* people who turned off animations in their system settings get none */
@media (prefers-reduced-motion: reduce) {
    .xmas-snow { display: none; }
    .xmas-bulb { animation: none; }
}
</style>
"""


def add_christmas_theme(force=False, snow=True, lights=True):
    """Add the theme if it is the festive season (or force=True)."""
    if not (force or is_festive()):
        return
    html = _CSS
    if lights:
        html += _lights_html()
    if snow:
        html += _snow_html()
    st.markdown(html, unsafe_allow_html=True)


add_christmas_theme()

pages = [
    st.Page("views/upcoming.py", title="Upcoming matches", icon=":material/event:", default=True),
    st.Page("views/live_record.py", title="Live record", icon=":material/insights:"),
    st.Page("views/season.py", title="Season predictions", icon=":material/emoji_events:"),
    st.Page("views/teams.py", title="Teams", icon=":material/groups:"),
    st.Page("views/performance.py", title="Model performance", icon=":material/analytics:"),
]

import data   # noqa: E402  (after set_page_config)
import style  # noqa: E402
import ui     # noqa: E402

BRAND = "Football Odds Predictor"
GLYPH = ('<rect class="s" x="5" y="7.5" width="16" height="11" rx="1.5" stroke-width="1.6"/>'
         '<path class="s" d="M13 7.5v11" stroke-width="1.6"/><circle class="s" cx="13" cy="13" r="2.4" stroke-width="1.6"/>')
EXTRA_CSS = """
.hero.page { margin: 3.5vh 0 1.8rem; } .hero.page .title { font-size: 2.45rem; }
.stApp h3 { font-size: 1.12rem; font-weight: 600; letter-spacing: -.02em; }
[data-testid="stMetric"] { border-top: 1px solid var(--line); padding-top: .75rem; }
[data-testid="stMetricLabel"] p { font-family: var(--mono); font-size: .7rem; letter-spacing: .06em;
  text-transform: uppercase; color: var(--muted); }
[data-testid="stMetricValue"] { font-size: 2rem; font-weight: 600; letter-spacing: -.035em; }
.st-key-nav { justify-content: flex-end; gap: .15rem; flex-wrap: nowrap; overflow-x: auto; }
.st-key-nav [data-testid="stPageLink"] a { padding: .3rem .7rem; border-radius: 999px; background: transparent; }
.st-key-nav [data-testid="stPageLink"] a p { font-size: .84rem; color: var(--muted); white-space: nowrap; }
.st-key-nav [data-testid="stPageLink"] a:hover p { color: var(--ink); }
.st-key-nav [data-testid="stPageLink"] a[aria-current="page"], .st-key-nav [data-testid="stPageLink"] a.active
  { background: var(--soft); }
.st-key-nav [data-testid="stPageLink"] a[aria-current="page"] p { color: var(--ink); }
[data-testid="stSegmentedControl"] button { border-radius: 999px !important; }
.foot a { color: inherit; }
@media (max-width: 640px) { .hero.page .title { font-size: 1.9rem; }
  .st-key-topbar [data-testid="stHorizontalBlock"] { flex-wrap: wrap; } }
"""

nav = st.navigation(pages, position="hidden")
style.set_theme(ui.mode())
ui.apply(width="1180px", extra=EXTRA_CSS)
right = ui.top_bar(BRAND, GLYPH, widths=(2.2, 5))
with right.container(key="nav", horizontal=True):
    for page in pages:
        st.page_link(page, label=page.title)

nav.run()

last_simulation, latest_result = data.freshness()
# Simulations only run when new results arrive, so their date is not the last workflow run
ui.foot(f"Results to {latest_result:%a %d %b %Y}"
        + (f" · Season simulation {last_simulation:%a %d %b %Y}" if last_simulation is not None else "")
        + " · Data: football-data.co.uk · "
        '<a href="https://github.com/BillyGeros94/football-odds-predictor">Method and code ↗</a>')
