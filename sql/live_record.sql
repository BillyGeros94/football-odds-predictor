-- live_record: each saved prediction next to the actual result and the market's odds.
-- Matched on season + both teams (each pairing plays once per league season), so a
-- rescheduled match still finds its result. If a match was predicted more than once,
-- prediction_rank = 1 is the latest prediction (made for the official date), the one that counts.

DROP VIEW IF EXISTS live_record;

CREATE OR REPLACE VIEW live_record AS
WITH p AS (
    SELECT *,
           to_char(match_date - INTERVAL '6 months', 'YY') ||
           to_char(match_date + INTERVAL '6 months', 'YY') AS season
    FROM predictions
)
SELECT p.prediction_id, p.created_at, p.match_date AS predicted_date, p.model,
       p.home_team_id, p.away_team_id,
       p.prob_home, p.prob_draw, p.prob_away,
       m.match_id, m.match_date, m.result,
       o.avg_home, o.avg_draw, o.avg_away,
       o.close_home, o.close_draw, o.close_away,
       ROW_NUMBER() OVER (
              PARTITION BY p.season, p.home_team_id, p.away_team_id, p.model
              ORDER BY p.created_at DESC
       ) AS prediction_rank
FROM p
JOIN matches m
    ON p.season = m.season
    AND p.home_team_id = m.home_team_id
    AND p.away_team_id = m.away_team_id
LEFT JOIN odds o
    ON o.match_id = m.match_id;