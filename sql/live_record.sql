-- live_record: each saved prediction next to the actual result and the closing odds.
-- Only predictions whose match has been played and loaded appear here.

CREATE OR REPLACE VIEW live_record AS
SELECT p.prediction_id, p.created_at, p.match_date, p.model,
       p.home_team_id, p.away_team_id,
       p.prob_home, p.prob_draw, p.prob_away,
       m.match_id, m.result,
       o.close_home, o.close_draw, o.close_away
FROM predictions p
JOIN matches m
    ON p.match_date = m.match_date
    AND p.home_team_id = m.home_team_id
    AND p.away_team_id = m.away_team_id
LEFT JOIN odds o
    ON m.match_id = o.match_id;
