CREATE OR REPLACE VIEW match_features AS
WITH team_matches AS (
    -- Home team's view of each match
    SELECT match_id, match_date, home_team_id AS team_id, TRUE AS is_home,
           home_goals AS goals_for, away_goals AS goals_against,
           home_shots_on_target AS sot_for, away_shots_on_target AS sot_against
    FROM matches
    UNION ALL
    -- Away team's view of each match
    SELECT match_id, match_date, away_team_id AS team_id, FALSE AS is_home,
           away_goals AS goals_for, home_goals AS goals_against,
           away_shots_on_target AS sot_for, home_shots_on_target AS sot_against
    FROM matches
),
rolling AS (
SELECT match_id, team_id, is_home,
       AVG(goals_for) OVER w AS goals_for_avg5, AVG(goals_against) OVER w AS goals_against_avg5,
       AVG(sot_for) OVER w AS sot_for_avg5, AVG(sot_against) OVER w AS sot_against_avg5
FROM team_matches
WINDOW w AS (
    PARTITION BY team_id
    ORDER BY match_date, match_id
    ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
)
)
SELECT m.match_id, m.match_date, m.league, m.season, m.result,
       e.home_before AS home_elo,
       e.away_before AS away_elo,
       h.goals_for_avg5 AS home_gf5,
       h.goals_against_avg5 AS home_ga5,
       h.sot_for_avg5 AS home_sot5,
       h.sot_against_avg5 AS home_sota5,
       a.goals_for_avg5 AS away_gf5,
       a.goals_against_avg5 AS away_ga5,
       a.sot_for_avg5 AS away_sot5,
       a.sot_against_avg5 AS away_sota5
FROM matches m
JOIN elo_ratings e ON e.match_id = m.match_id
JOIN rolling h ON h.match_id = m.match_id AND h.is_home
JOIN rolling a ON a.match_id = m.match_id AND NOT a.is_home;
