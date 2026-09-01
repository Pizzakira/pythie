"""Is the declared origin of a recording still where it says it is?

A manifest that declares a source URL makes a claim, and until 01/09/2026
nothing in this chain ever tested it: the URL recorded for the LaREF debate
led to a private video for a whole session before a reader noticed. The URL
had been right when it was written -- the broadcaster took the upload down
and republished the same recording under a new identifier -- but nothing
could have told the difference between "moved" and "wrong", because nothing
had ever looked.

This module looks. It asks YouTube's oEmbed endpoint, which answers for any
public video without an API key, a browser, or yt-dlp, and returns what was
seen: the title and the channel, or the fact that nothing answered. That is
deliberately little. It cannot prove the video is the one the transcript came
from; it proves the declared address resolves to a public recording with a
given title, so that a reader can compare the title with the manifest, and so
that "private" or "removed" is reported at launch rather than discovered at
the first click.

Reachability is checked; identity is not. Identity was established once, by
hand, on 01/09/2026 -- ten text probes across the debate aligned within half a
second between the two uploads -- and is recorded in the manifest, not here.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Optional

OEMBED = "https://www.youtube.com/oembed"
TIMEOUT_SECONDS = 6.0

_VIDEO_ID = re.compile(r"(?:v=|youtu\.be/|/embed/|/live/)([A-Za-z0-9_-]{11})")


@dataclass(frozen=True)
class Probe:
    url: str
    reachable: bool
    status: str                      # "public", "private_or_removed", "unreachable", "not_youtube"
    title: Optional[str] = None
    channel: Optional[str] = None
    checked_on: str = ""

    def describe(self) -> str:
        """One line for a log, in the language of the documentation."""
        if self.status == "public":
            return f"source atteignable : « {self.title} » ({self.channel})"
        if self.status == "private_or_removed":
            return "SOURCE PRIVÉE OU RETIRÉE : l'URL déclarée ne mène plus à une vidéo publique"
        if self.status == "not_youtube":
            return "source non vérifiable : ce n'est pas une URL YouTube"
        return "source injoignable : pas de réponse du réseau (l'URL n'est ni confirmée ni infirmée)"


def video_id(url: str) -> Optional[str]:
    match = _VIDEO_ID.search(url or "")
    return match.group(1) if match else None


def probe_youtube(url: str, timeout: float = TIMEOUT_SECONDS) -> Probe:
    """What the declared URL resolves to, right now.

    oEmbed answers 200 with a title for a public video, 401/403 for a private
    one and 404 for a removed one. The two failure codes are folded together:
    from the outside, "you may not see it" and "it is gone" are the same fact
    for a reader who wants to open the link.
    """
    today = date.today().isoformat()
    if not video_id(url):
        return Probe(url, False, "not_youtube", checked_on=today)

    query = urllib.parse.urlencode({"url": url, "format": "json"})
    request = urllib.request.Request(f"{OEMBED}?{query}",
                                     headers={"User-Agent": "pythie-provenance/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in (401, 403, 404):
            return Probe(url, False, "private_or_removed", checked_on=today)
        return Probe(url, False, "unreachable", checked_on=today)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return Probe(url, False, "unreachable", checked_on=today)

    return Probe(url, True, "public",
                 title=str(payload.get("title") or ""),
                 channel=str(payload.get("author_name") or ""),
                 checked_on=today)


def timestamped(url: str, seconds: float) -> str:
    """The same video, opened at a given second."""
    if not url:
        return ""
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}t={int(seconds)}s"
