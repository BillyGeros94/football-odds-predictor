-- The database tables. Safe to rerun: IF NOT EXISTS skips tables that already exist.
-- Run with: python -m src.db

-- One row per club. Names are exactly as football-data spells them.
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

-- One row per finished match. Shots can be missing in the source files, so they allow NULL.
CREATE TABLE IF NOT EXISTS matches (
    match_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    league       TEXT NOT NULL,       -- 'E0' Premier League, 'E1' Championship
    season       TEXT NOT NULL,       -- '2526' means 2025/26
    match_date   DATE NOT NULL,
    home_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    away_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    home_goals   INTEGER NOT NULL,
    away_goals   INTEGER NOT NULL,
    home_shots   INTEGER,
    away_shots   INTEGER,
    home_shots_on_target INTEGER,
    away_shots_on_target INTEGER,
    result       TEXT NOT NULL CHECK (result IN ('H', 'D', 'A')),
    -- A team plays once per day, so this identifies a match and stops duplicates on reload
    UNIQUE (match_date, home_team_id, away_team_id)
);

-- Market average odds per match: pre-match (avg_) and closing (close_).
-- Only 2019/20 onwards; closing odds are the benchmark, never a model input.
CREATE TABLE IF NOT EXISTS odds (
    match_id   INTEGER PRIMARY KEY REFERENCES matches(match_id),
    avg_home   NUMERIC(6,2),
    avg_draw   NUMERIC(6,2),
    avg_away   NUMERIC(6,2),
    close_home NUMERIC(6,2),
    close_draw NUMERIC(6,2),
    close_away NUMERIC(6,2)
);

-- Both teams' Elo ratings around each match. Models only use the "before" values,
-- which are known at kick-off. Rebuilt by python -m src.elo.
CREATE TABLE IF NOT EXISTS elo_ratings (
    match_id    INTEGER PRIMARY KEY REFERENCES matches(match_id),
    home_before NUMERIC(7,2) NOT NULL,
    away_before NUMERIC(7,2) NOT NULL,
    home_after  NUMERIC(7,2) NOT NULL,
    away_after  NUMERIC(7,2) NOT NULL
);

-- Live predictions for upcoming matches. Upcoming matches are not in `matches` yet,
-- so they are identified by date and teams. Rows are never overwritten, and
-- created_at proves each prediction was made before kick-off.
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    match_date    DATE NOT NULL,
    home_team_id  INTEGER NOT NULL REFERENCES teams(team_id),
    away_team_id  INTEGER NOT NULL REFERENCES teams(team_id),
    model         TEXT NOT NULL,
    prob_home     NUMERIC(5,4) NOT NULL,
    prob_draw     NUMERIC(5,4) NOT NULL,
    prob_away     NUMERIC(5,4) NOT NULL,
    UNIQUE (match_date, home_team_id, away_team_id, model)
);
