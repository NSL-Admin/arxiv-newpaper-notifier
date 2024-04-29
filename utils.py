import io
import os
import tempfile
import textwrap
import urllib
import urllib.request
from datetime import datetime, timedelta
from logging import Logger
from typing import Optional, cast

import fitz
from arxiv import Client, Result, Search, SortCriterion
from llama_cpp import Llama
from PIL import Image

from const import Paper, PaperGist, PaperList


def fetch_papers(
    category: str, date: datetime, max_results: int, logger: Logger
) -> list[Result]:
    client = Client(delay_seconds=1)
    search = Search(
        query=f"cat:{category}",
        max_results=max_results,
        sort_by=SortCriterion.SubmittedDate,
    )
    all_results = list(client.results(search=search))
    selected = [
        r for r in all_results if date <= r.published < (date + timedelta(days=1))
    ]
    logger.info(
        f'found {len(selected)} papers published on {date.strftime("%Y-%m-%d")}'
    )
    return selected


def generate_gist(llm: Llama, title: str, abstract: str, logger: Logger) -> PaperGist:
    logger.info("starting gist generation with LLM")
    llm_resp = llm.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": textwrap.dedent("""
                        You are a renowned professor in Computer Science. Your students will ask you to extract key information from an abstract of an academic paper using your expertise, then you will give them your answer in the following JSON format:
                        {
                            "about":  # write what this research did in plain sentence (string),
                            "objective":  # write what this research tried to achieve (string),
                            "novelty":  # write how this research is superior to existing ones (string),
                            "key":  # write what is the most important findings of this research (string),
                        }
                    """),
            },
            {
                "role": "user",
                "content": textwrap.dedent(f"""
                        Please extract gist from the following abstract from a paper titled \"{title}\":
                        {abstract}
                    """),
            },
        ],
        response_format={
            "type": "json_object",
            "schema": {
                "type": "object",
                "properties": {
                    "about": {"type": "string"},
                    "objective": {"type": "string"},
                    "novelty": {"type": "string"},
                    "key": {"type": "string"},
                },
            },
        },
        temperature=0.7,
    )
    logger.info("finished gist generation with LLM")
    llm_resp_text = cast(str, llm_resp["choices"][0]["message"]["content"])  # type:ignore
    return PaperGist.model_validate_json(llm_resp_text)


def get_first_figure(pdf_url: str, data_dir: str, logger: Logger) -> Optional[str]:
    # TODO: filter picture with aspect ratio
    if not pdf_url:
        return None
    pdf_name = os.path.basename(pdf_url)
    with tempfile.TemporaryDirectory() as tmpdir:
        # download pdf to temporary directory
        with urllib.request.urlopen(pdf_url) as web_stream:
            pdf_path = os.path.join(tmpdir, pdf_name)
            with open(pdf_path, "wb") as pdf_file:
                pdf_file.write(web_stream.read())
        # open pdf and search for images
        pdf = fitz.open(pdf_path)
        for page in pdf:
            images = page.get_images()  # type:ignore
            if not images:
                continue
            # extract reference number to the first image in this PDF
            first_image = images[0]
            image_xref: int = first_image[0]
            # extract image itself and save it
            base_image = pdf.extract_image(xref=image_xref)
            image = Image.open(io.BytesIO(base_image["image"]))
            # check the aspect ratio of this image.
            # since the figure describing the overall workflow tends to
            # be long in horizontal direction, we only accept image whose
            # ratio is more than 4 : 3
            MIN_RATIO = 4 / 3
            w, h = image.size
            if (w / h) < MIN_RATIO:
                continue
            image_path = os.path.join(
                data_dir,
                "images",
                f'{pdf_name}.{base_image["ext"]}',
            )
            image.save(image_path)
            logger.info(f"extracted image from {pdf_name} and saved it at {image_path}")
            return image_path
        logger.info(f"found no image in {pdf_name}")
        return None  # no image was found in the pdf


def process_results(
    search_results: list[Result],
    date: datetime,
    llm: Llama,
    data_dir: str,
    logger: Logger,
) -> PaperList:
    papers = []
    for result in search_results:
        gist = generate_gist(
            llm=llm, title=result.title, abstract=result.summary, logger=logger
        )
        first_figure_path = get_first_figure(
            pdf_url=result.pdf_url, data_dir=data_dir, logger=logger
        )
        paper = Paper(
            title=result.title,
            author=", ".join(
                map(lambda author: author.name, result.authors)
            ),  # generate comma-separated list of authors
            gist=gist,
            url=result.entry_id,
            first_figure_path=first_figure_path,
        )
        papers.append(paper)
    return PaperList(papers=papers, date=date)