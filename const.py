from datetime import datetime
from typing import Final, Optional

from pydantic import BaseModel


class PaperGist(BaseModel):
    about: str
    objective: str
    novelty: str
    key: str


class Paper(BaseModel):
    title: str
    author: str
    gist: PaperGist
    url: str
    first_figure_path: Optional[str]


class PaperList(BaseModel):
    date: datetime
    papers: list[Paper]


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
