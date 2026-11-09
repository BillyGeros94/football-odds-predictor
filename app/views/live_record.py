"""Live record: predictions made before kick-off, scored against the results and the market."""
import altair as alt
import pandas as pd
import streamlit as st

import data
from style import COLOURS

st.title("Live record")
st.caption("Every prediction is saved before kick-off and published to the repository. Once the "
           "match is played it is scored against two benchmarks on the same games: the market's "
           "pre-match odds and its closing odds at kick-off. Lower log loss is better.")

live = data.live()
if live == "missing":
    st.warning("live_scores() was not found in src/live_score.py.")
    st.stop()
if live is None:
    st.info("Tracking started in November 2026. Results appear here once the first predicted "
            "matches have been played.")
    st.stop()

matches = live["matches"]
scores = live["scores"].set_index("model")

# ---- Headline numbers ----
cols = st.columns(5)
cols[0].metric("Model", f"{scores.loc['average', 'log_loss']:.4f}")
cols[1].metric("Market pre-match", f"{scores.loc['market pre-match', 'log_loss']:.4f}")
cols[2].metric("Market closing", f"{scores.loc['market closing', 'log_loss']:.4f}")
cols[3].metric("Matches scored", len(matches))
cols[4].metric("Not scored yet", live["unscored"],
               help="Past predictions with no result yet: usually the result has not been loaded, "
                    "otherwise a postponed match")

# ---- Log loss over time ----
st.subheader("Running log loss")
running = pd.DataFrame({"match_date": matches["match_date"]})
for label, column in [("Model", "model_loss"), ("Market pre-match", "pre_loss"),
                      ("Market closing", "close_loss")]:
    running[label] = matches[column].expanding().mean().to_numpy()
running = running.groupby("match_date").last().reset_index()   # one point per match day
long = running.melt("match_date", var_name="source", value_name="log_loss")

chart = (
    alt.Chart(long)
    .mark_line(point=True)
    .encode(
        x=alt.X("match_date:T", title=None),
        y=alt.Y("log_loss:Q", title="Average log loss so far", scale=alt.Scale(zero=False)),
        color=alt.Color("source:N", title=None,
                        scale=alt.Scale(domain=list(COLOURS)[:3], range=list(COLOURS.values())[:3])),
        tooltip=["match_date:T", "source:N", alt.Tooltip("log_loss:Q", format=".4f")],
    )
    .properties(height=320)
)
st.altair_chart(chart, width="stretch")
st.caption("Early values move a lot: log loss needs a few hundred matches to settle.")

# ---- Where the model and the market disagreed ----
st.subheader("Where the model and the market disagreed")
outcomes = ["home", "draw", "away"]
diff = pd.concat([(matches[f"model_{o}"] - matches[f"pre_{o}"]).abs() for o in outcomes], axis=1)
matches = matches.assign(disagreement=diff.max(axis=1) * 100)
actual = matches["result"].map({"H": "home", "D": "draw", "A": "away"})
model_on_actual = [matches.loc[i, f"model_{o}"] for i, o in actual.items()]
market_on_actual = [matches.loc[i, f"pre_{o}"] for i, o in actual.items()]
matches["closer"] = ["Model" if m > k else "Market" for m, k in zip(model_on_actual, market_on_actual)]

top = matches.nlargest(10, "disagreement").copy()
top["match"] = top["home"] + " v " + top["away"]
for source in ["model", "pre"]:
    top[source] = (top[[f"{source}_home", f"{source}_draw", f"{source}_away"]] * 100).round().astype(int) \
        .astype(str).agg(" / ".join, axis=1)
st.dataframe(
    top[["match_date", "match", "model", "pre", "result", "disagreement", "closer"]],
    hide_index=True, width="stretch",
    column_config={
        "match_date": st.column_config.DateColumn("Date", format="D MMM"),
        "match": "Match",
        "model": "Model H / D / A %",
        "pre": "Market H / D / A %",
        "result": "Result",
        "disagreement": st.column_config.NumberColumn("Biggest gap", format="%.0f pts"),
        "closer": "Closer to the result",
    },
)
won = (matches["closer"] == "Model").mean() * 100
st.caption(f"Across all {len(matches)} scored matches, the model gave the actual result a higher "
           f"probability than the market in {won:.0f}% of them.")

# ---- Recent matches ----
st.subheader("Recent scored matches")
recent = matches.sort_values("match_date", ascending=False).head(20).copy()
recent["match"] = recent["home"] + " v " + recent["away"]
favourite = recent[["model_home", "model_draw", "model_away"]].to_numpy().argmax(axis=1)
recent["favourite"] = [["Home", "Draw", "Away"][i] for i in favourite]
recent["hit"] = recent["favourite"].str[0] == recent["result"]
for o in outcomes:
    recent[f"model_{o}"] = recent[f"model_{o}"] * 100
st.dataframe(
    recent[["match_date", "match", "model_home", "model_draw", "model_away", "result", "hit"]],
    hide_index=True, width="stretch",
    column_config={
        "match_date": st.column_config.DateColumn("Date", format="D MMM"),
        "match": "Match",
        "model_home": st.column_config.NumberColumn("Home %", format="%.0f"),
        "model_draw": st.column_config.NumberColumn("Draw %", format="%.0f"),
        "model_away": st.column_config.NumberColumn("Away %", format="%.0f"),
        "result": "Result",
        "hit": st.column_config.CheckboxColumn("Favourite won"),
    },
)
if live["superseded"]:
    st.caption(f"{live['superseded']} earlier prediction(s) were replaced by one made for a "
               "rescheduled date; only the latest prediction for each match is scored.")
