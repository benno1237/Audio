# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
import re

# Dependency Imports
from bs4 import BeautifulSoup
from requests_futures.sessions import FuturesSession

# Music Imports
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass


class LyricUtilities(MixinMeta, ABC, metaclass=CompositeMetaClass):
    """Base class to hold all Lyric utility methods"""


BOT_SONG_RE = re.compile(
    (r"((\[)|(\()).*(of?ficial|feat\.?|" r"ft\.?|audio|video|lyrics?|remix|HD).*(?(2)]|\))"),
    flags=re.I,
)


async def getlyrics(artistsong):
    percents = {
        " ": "+",
        "!": "%21",
        '"': "%22",
        "#": "%23",
        "$": "%24",
        "%": "%25",
        "&": "%26",
        "'": "%27",
        "(": "%28",
        ")": "%29",
        "*": "%2A",
        "+": "%2B",
        "`": "%60",
        ",": "%2C",
        "-": "%2D",
        ".": "%2E",
        "/": "%2F",
    }
    searchquery = ""
    for char in artistsong:
        if char in percents:
            char = percents[char]
        searchquery += char
    session = FuturesSession()
    future = session.get("https://google.com/search?q=" + searchquery + "+lyrics")
    response_one = future.result()
    soup = BeautifulSoup(response_one.text, "html.parser")
    bouncer = "Our systems have detected unusual traffic from your computer network"
    if bouncer in soup.get_text():
        title_ = ""
        artist_ = ""
        lyrics_ = "Google has detected us being suspicious, try again later."
        source_ = ""
    else:
        try:
            title_ = soup.find("span", class_="BNeawe tAd8D AP7Wnd").get_text()
            artist_ = soup.find_all("span", class_="BNeawe s3v9rd AP7Wnd")[-1].get_text()
            lyrics_ = soup.find_all("div", class_="BNeawe tAd8D AP7Wnd")[-1].get_text()
            source_ = soup.find_all("span", class_="uEec3 AP7Wnd")[-1].get_text()
        except AttributeError:
            title_, artist_, lyrics_, source_ = (
                "",
                "",
                "Not able to find the lyrics for {}.".format(searchquery),
                "",
            )
    session.close()
    return title_, artist_, lyrics_, source_
