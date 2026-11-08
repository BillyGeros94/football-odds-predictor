CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    league   TEXT NOT NULL,
    season   TEXT NOT NULL,
    match_date DATE NOT NULL,
    home_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    away_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    home_goals  INTEGER NOT NULL,
    away_goals INTEGER NOT NULL,
    home_shots INTEGER,
    away_shots INTEGER,
    home_shots_on_target INTEGER,
    away_shots_on_target INTEGER, 
    result TEXT NOT NULL CHECK (result IN ('H', 'D', 'A')),
    UNIQUE (match_date, home_team_id, away_team_id)
);

CREATE TABLE IF NOT EXISTS odds (
    match_id INTEGER PRIMARY KEY REFERENCES matches(match_id),
    avg_home   NUMERIC(6,2),
    avg_draw  NUMERIC(6,2),
    avg_away   NUMERIC(6,2),
    close_home   NUMERIC(6,2),
    close_draw  NUMERIC(6,2),
    close_away  NUMERIC(6,2) 
);

CREATE TABLE IF NOT EXISTS elo_ratings (
    match_id    INTEGER PRIMARY KEY REFERENCES matches(match_id),
    home_before NUMERIC(7,2) NOT NULL,
    away_before NUMERIC(7,2) NOT NULL,
    home_after  NUMERIC(7,2) NOT NULL,
    away_after  NUMERIC(7,2) NOT NULL
);
