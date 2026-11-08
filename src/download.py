"""Download the current season's results and the upcoming fixtures.

Fetches three small CSV files from football-data.co.uk: the Premier League and
Championship files for the current season, and fixtures.csv. It is meant to run
twice a week (see .github/workflows/update.yml), not more: the site is free and
run by one person.
"""
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

BASE_URL = "https://www.football-data.co.uk"
USER_AGENT = ("football-odds-predictor/1.0 "
              "(personal non-commercial project; https://github.com/BillyGeros94)")
LEAGUES = ["E0", "E1"]


def season_code(today=None):
    # 2026/27 → "2627". A new season starts in July.
    today = today or date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def looks_like_csv(content):
    # Every football-data file starts with the Div column, sometimes after a BOM
    start = content[:100].decode("utf-8-sig", errors="replace")
    return start.startswith("Div,")


def save(content, path):
    # Write to a temporary file first, so a failed download never leaves half a file
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_bytes(content)
    temp.replace(path)


def download(url, path):
    content = fetch(url)
    if not looks_like_csv(content):
        raise ValueError(f"{url} did not return a football-data CSV")
    save(content, path)
    print(f"Saved {path} ({len(content):,} bytes)")


def main(base_url=BASE_URL):
    season = season_code()

    for league in LEAGUES:
        url = f"{base_url}/mmz4281/{season}/{league}.csv"
        try:
            download(url, Path(f"data/raw/{league}_{season}.csv"))
        except urllib.error.HTTPError as error:
            # In July the new season's file may not exist yet
            if error.code != 404:
                raise
            print(f"{url} is not published yet, skipping")

    download(f"{base_url}/fixtures.csv", Path("data/fixtures/fixtures.csv"))


if __name__ == "__main__":
    main()
