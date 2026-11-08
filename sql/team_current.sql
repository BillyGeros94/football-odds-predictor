CREATE OR REPLACE VIEW team_current AS
WITH team_matches AS (
-- Home team's view of each match
    SELECT match_id, match_date, home_team_id AS team_id, TRUE AS is_home,
           home_goals AS goals_for, away_goals AS goals_against,
           home_shots_on_target AS sot_for, away_shots_on_target AS sot_against,
           home_after AS elo_after
    FROM matches
    JOIN elo_ratings USING (match_id)
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
           ROW_NUMBER() OVER (PARTITION BY team_id
                              ORDER BY match_date DESC, match_id DESC) AS rn
    FROM team_matches
    WINDOW w AS (PARTITION BY team_id ORDER BY match_date, match_id
                 ROWS BETWEEN 4 PRECEDING AND CURRENT ROW)
)
SELECT * FROM ranked WHERE rn = 1;