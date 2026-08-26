"""Runtime robots.txt check. Fetched fresh each run rather than hardcoded, since site rules can
change between the pilot and any later scale run."""
from __future__ import annotations

from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser


def check_allowed(url: str, user_agent: str) -> bool:
    """True if robots.txt for url's host permits user_agent to fetch this exact path."""
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except OSError:
        # robots.txt unreachable: fail closed, do not assume permission.
        print(f"WARNING: could not fetch {robots_url}; treating as disallowed")
        return False
    return parser.can_fetch(user_agent, url)
