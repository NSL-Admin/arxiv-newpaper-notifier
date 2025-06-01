import logging
from datetime import datetime
from typing import Final, Optional

import requests
from fake_useragent import UserAgent
from pydantic import BaseModel, Field, field_validator
from requests.exceptions import Timeout

ARXIV_CATEGORIES: Final[set[str]] = {
    # includes Computer Science and Electrical Engineering and Systems Science group
    "cs.AR",
    "cs.AI",
    "cs.CC",
    "cs.CE",
    "cs.CG",
    "cs.CL",
    "cs.CR",
    "cs.CV",
    "cs.CY",
    "cs.DB",
    "cs.DC",
    "cs.DL",
    "cs.DM",
    "cs.DS",
    "cs.ET",
    "cs.FL",
    "cs.GL",
    "cs.GR",
    "cs.GT",
    "cs.HC",
    "cs.IR",
    "cs.IT",
    "cs.LG",
    "cs.LO",
    "cs.MA",
    "cs.MM",
    "cs.MS",
    "cs.NA",
    "cs.NE",
    "cs.NI",
    "cs.OH",
    "cs.OS",
    "cs.PF",
    "cs.PL",
    "cs.RO",
    "cs.SC",
    "cs.SD",
    "cs.SE",
    "cs.SI",
    "cs.SY",
    "eess.AS",
    "eess.IV",
    "eess.SP",
    "eess.SY",
}

REQUEST_HEADERS: Final[dict[str, str]] = {
    "user-agent": UserAgent().chrome  # set random chrome UA
}


class UrlWithText(BaseModel):
    url: str = Field(description="the url mentioned in the reference section.")
    text: str = Field(
        description="the text to associate the url with. This text should be a short noun phrase explaining the content at the url. This text MUST NOT include any asterisks or any URLs."
    )


class PaperGist(BaseModel):
    # descriptions are given for the sake of the formatter LLM
    about: str = Field(
        description="write what this research did in plain sentence (single line without any URLs, around 50 words)"
    )
    objective: str = Field(
        description="write what this research tried to achieve (single line without any URLs, around 50 words)"
    )
    novelty: str = Field(
        description="write how this research is superior to existing ones (single line without any URLs, around 50 words)"
    )
    key: str = Field(
        description="write what are the most important findings of this research (single line without any URLs, around 50 words)"
    )
    reference_urls: list[UrlWithText] = Field(
        description="write especially important URLs mentioned in the referece section if it exists, that provide important contexts to understand this research."
    )

    @field_validator("reference_urls")
    @classmethod
    def validate_reference_urls(cls, v: list[UrlWithText]) -> list[UrlWithText]:
        """Ensure that reference_urls only include valid URLs."""
        sanitized_urls = []
        for url in v:
            if "example.com" in url.url:
                logging.warning(
                    f"the url {url.url} is a placeholder url, being removed from reference urls"
                )
                continue
            if any(u in url.url for u in ["arxiv.org", "www.mdpi.com"]):
                logging.warning(
                    f"the url {url.url} is a URL to another paper which may not be very reliable, being removed from reference urls"
                )
                continue
            try:
                r = requests.get(
                    url=url.url,
                    timeout=5,
                    allow_redirects=True,
                    headers=REQUEST_HEADERS,
                )
            except Timeout:
                logging.warning(
                    f"{url.url} is an inaccessible url, being removed from reference urls"
                )
                continue
            else:
                if (
                    r.status_code not in [200, 403]
                ):  # 403 is usually a result from website's bot protection, so it's not likely to be a problem for the users
                    logging.warning(
                        f"{url.url} returned unusual status code {r.status_code}, being removed from reference urls"
                    )
                    continue
            sanitized_urls.append(url)
        return sanitized_urls


class Paper(BaseModel):
    title: str
    author: str
    gist: PaperGist
    url: str
    first_figure_path: Optional[str]


class PaperList(BaseModel):
    date: datetime
    papers: list[Paper]
