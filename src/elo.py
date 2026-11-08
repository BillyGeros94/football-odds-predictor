START_RATING = 1500
K = 20
HOME_ADVANTAGE = 60

def expected_home(home_rating, away_rating):
    return 1 / (1 + 10 ** ((away_rating - (home_rating + HOME_ADVANTAGE)) / 400))

def update(home_rating, away_rating, result):
    score = {"H": 1, "D": 0.5, "A": 0}[result]
    expected = expected_home(home_rating, away_rating)
    change = K * (score - expected)
    return home_rating + change, away_rating - change