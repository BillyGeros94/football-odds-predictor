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
)
SELECT match_id, team_id, is_home,
       AVG(goals_for) OVER w AS goals_for_avg5, AVG(goals_against) OVER w AS goals_against_avg5,
       AVG(sot_for) OVER w AS sot_for_avg5, AVG(sot_against) OVER w AS sot_against_avg5
FROM team_matches
WINDOW w AS (
    PARTITION BY team_id
    ORDER BY match_date, match_id
    ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
)
