# LiveReleaseFetcher: Fetches latest experimental driver releases dynamically from GitHub
import os
import re
import json
import urllib.request
import urllib.error
from typing import Optional, Tuple, Dict, Any
from ..models.driver import DriverRelease

class LiveReleaseFetcher:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "OpCore-Simplify-ExperimentalDrivers/1.0 (Hackintosh Assistant)",
            "Accept": "application/vnd.github.v3+json, text/html, application/xhtml+xml, */*",
        }

    @staticmethod
    def parse_repo_owner_and_name(repo_url: str) -> Tuple[Optional[str], Optional[str]]:
        if not repo_url:
            return None, None
        clean = repo_url.strip().rstrip("/")
        parts = clean.split("/")
        if len(parts) >= 2:
            return parts[-2], parts[-1]
        return None, None

    def fetch_latest_release(self, repo_url: str) -> Optional[DriverRelease]:
        owner, repo = self.parse_repo_owner_and_name(repo_url)
        if not owner or not repo:
            return None

        # 1. Try GitHub REST API
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        try:
            req = urllib.request.Request(api_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8", errors="replace"))
                    return self._build_release_from_api(data, owner, repo)
        except Exception:
            # Fallback to HTML/Web page check if API is rate limited or unavailable
            pass

        # 2. Try HTML scraping fallback
        return self._fetch_from_html(owner, repo)

    def _build_release_from_api(self, data: Dict[str, Any], owner: str, repo: str) -> DriverRelease:
        tag = data.get("tag_name", "")
        name = data.get("name") or tag
        published = data.get("published_at", "")
        body = data.get("body", "")

        download_url = None
        assets = data.get("assets", [])
        for asset in assets:
            aname = asset.get("name", "").lower()
            if aname.endswith((".tar.gz", ".zip", ".pkg")):
                download_url = asset.get("browser_download_url")
                break

        if not download_url:
            download_url = data.get("tarball_url") or f"https://github.com/{owner}/{repo}/releases/download/{tag}/{repo}-{tag}.tar.gz"

        commit = data.get("target_commitish", "main")

        return DriverRelease(
            tag=tag,
            commit=commit[:8] if len(commit) >= 8 else commit,
            release_name=name,
            published_at=published,
            download_url=download_url,
            changelog=body.strip(),
        )

    def _fetch_from_html(self, owner: str, repo: str) -> Optional[DriverRelease]:
        url = f"https://github.com/{owner}/{repo}/releases"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8", errors="replace")

            # Look for /releases/tag/
            match = re.search(r'/releases/tag/([^"\'\s>]+)', content)
            if not match:
                return None
            tag = match.group(1)

            download_url = f"https://github.com/{owner}/{repo}/releases/download/{tag}/{repo}-{tag}.tar.gz"

            return DriverRelease(
                tag=tag,
                commit="latest",
                release_name=f"{repo} {tag}",
                published_at="latest",
                download_url=download_url,
                changelog=f"Automatically fetched latest release {tag} from upstream repository.",
            )
        except Exception:
            return None
