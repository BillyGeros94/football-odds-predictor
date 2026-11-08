-- team_current: each team's form right now, for predicting upcoming fixtures.
-- One row per team: its Elo after its latest match and its averages over its
-- last 5 matches. Unlike features.sql, the latest match IS included, because
-- it has already been played. Read by src/predict.py.

CREATE OR REPLACE VIEW team_current AS
WITH team_matches AS (
    -- Each match becomes two rows, one per team, with that team's rating after the match
    -- Home team's view of each match
    SELECT match_id, match_date, home_team_id AS team_id, TRUE AS is_home,
           home_goals AS goals_for, away_goals AS goals_against,
           home_shots_on_target AS sot_for, away_shots_on_target AS sot_against,
           home_after AS elo_after
    FROM matches
    JOIN elo_ratings USING (match_id)   -- USING keeps a single match_id column
    UNION ALL
    -- Away team's view of each match
    SELECT match_id, match_date, away_team_id AS team_id, FALSE AS is_home,
           away_goals AS goals_for, home_goals AS goals_against,
           away_shots_on_target AS sot_for, home_shots_on_target AS sot_against,
           away_after AS elo_after
    FROM matches
    JOIN elo_ratings USING (match_id)
),
ranked AS (
    SELECT team_id, match_date, elo_after,
           AVG(goals_for) OVER w AS gf5,
           AVG(goals_against) OVER w AS ga5,
           AVG(sot_for) OVER w AS sot5,
           AVG(sot_against) OVER w AS sota5,
           -- Number each team's matches from newest (1) to oldest
           ROW_NUMBER() OVER (PARTITION BY team_id
                              ORDER BY match_date DESC, match_id DESC) AS rn
    FROM team_matches
    WINDOW w AS (PARTITION BY team_id ORDER BY match_date, match_id
                 ROWS BETWEEN 4 PRECEDING AND CURRENT ROW)   -- last 5, including this one
)
-- Keep only each team's latest match
SELECT * FROM ranked WHERE rn = 1;
