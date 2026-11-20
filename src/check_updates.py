"""Tell the workflow whether football-data has changed since the last full update.

The workflow checks every hour, because the site's update times vary (weekend
fixtures usually appear on Friday afternoon) and GitHub can start scheduled runs
hours late. To stay light on a free site, this asks only for the headers of the
three files that src.download fetches, never the files themselves. The server
gives each version of a file a tag (ETag) and a last-modified time; a new tag
means the file changed.

The result is one fingerprint of all three files. The workflow remembers the
fingerprint of the last successful update and runs the full pipeline only when
it differs.

Run (prints the fingerprint; on GitHub Actions also writes it as an output):
    python -m src.check_updates
"""
import hashlib
import os
import urllib.error
import urllib.request

from src.download import BASE_URL, LEAGUES, USER_AGENT, season_code


def file_urls(base_url=BASE_URL, season=None):
    """The same three files that src.download fetches."""
    season = season or season_code()
    return [f"{base_url}/mmz4281/{season}/{league}.csv" for league in LEAGUES] + \
           [f"{base_url}/fixtures.csv"]


def file_version(headers):
    """What identifies this version of a file: its ETag, else its last-modified time and size.

    Returns None when the server sends neither, so the caller can treat the file as changed.
    """
    etag = headers.get("ETag")
    if etag:
        return f"etag {etag}"
    modified = headers.get("Last-Modified")
    if modified:
        return f"modified {modified} size {headers.get('Content-Length')}"
    return None


def head(url):
    """The version of one file, 'missing' if it does not exist yet, or None if unknown."""
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return file_version(response.headers)
    except urllib.error.HTTPError as error:
        # In July the new season's file may not exist yet, as in src.download
        if error.code == 404:
            return "missing"
        raise


def fingerprint(versions):
    """One short key for all files' versions, or None if any version is unknown.

    None makes the workflow run the full update every time, which is safe:
    predictions are write-once and repeated simulations are skipped.
    """
    if any(version is None for version in versions.values()):
        return None
    text = "\n".join(f"{url} {versions[url]}" for url in sorted(versions))
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def main():
    versions = {url: head(url) for url in file_urls()}
    for url, version in versions.items():
        print(f"{url}: {version}")

    key = fingerprint(versions)
    print("Fingerprint:", key or "unknown, so the full update will run")

    # GitHub Actions reads step outputs from the file named in GITHUB_OUTPUT
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"fingerprint={key or ''}\n")


if __name__ == "__main__":
    main()
