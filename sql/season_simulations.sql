-- season_simulations: each team's chances of every season outcome, from simulating the
-- rest of the season many times (src/simulate.py). Every run is kept, so the app can show
-- how a team's chances changed over the season. All rows of one run share run_at.

CREATE TABLE IF NOT EXISTS season_simulations (
    run_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    season          TEXT NOT NULL,
    league          TEXT NOT NULL,
    team_id         INTEGER NOT NULL REFERENCES teams(team_id),
    played          INTEGER NOT NULL,          -- matches played so far
    points          INTEGER NOT NULL,          -- points so far
    expected_points NUMERIC(5,1) NOT NULL,     -- average final points across simulations
    p_title         NUMERIC(5,4) NOT NULL,
    p_top4          NUMERIC(5,4),              -- Premier League only
    p_promotion     NUMERIC(5,4),              -- Championship only: top 2
    p_playoffs      NUMERIC(5,4),              -- Championship only: 3rd to 6th
    p_relegation    NUMERIC(5,4) NOT NULL,     -- bottom 3
    PRIMARY KEY (run_at, team_id)
);
