import argparse
import logging
import os
from datetime import datetime, timedelta, timezone

from llama_cpp import Llama

from const import ARXIV_CATEGORIES
from utils import fetch_papers, process_results

parser = argparse.ArgumentParser(
    description="Fetch information of the latest papers from arXiv, then update json"
)
parser.add_argument(
    "--category",
    help="Category ID to search for papers of",
    choices=ARXIV_CATEGORIES,
    required=True,
)
parser.add_argument(  # TODO: Explain that this will be interpreted as UTC in README
    "--date",
    help="Date to search for papers within (in the format like 2024-01-01)",
    type=lambda datestr: datetime.strptime(datestr, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    ),
    default=(datetime.today() - timedelta(days=1)).replace(
        tzinfo=timezone.utc
    ),  # defaults to yesterday
    required=False,
)
parser.add_argument(
    "--data-dir",
    help="Path to a directory to store data in",
    default=os.path.join(os.path.dirname(__file__), "data"),
    required=False,
)
parser.add_argument(
    "--max-papers",
    help="Max number of papers to search for",
    type=int,
    default=20,
    required=False,
)
parser.add_argument(
    "--gpu",
    help="Use GPU acceleration to create summary of paper with LLM",
    action="store_true",
    required=False,
)
parser.add_argument(
    "--verbose",
    help="Enable verbose logging from this script",
    action="store_true",
    required=False,
)

if __name__ == "__main__":
    args = parser.parse_args()

    # globally enable logging (to stdout)
    logging.basicConfig()

    # create logger for logs from this app
    logger = logging.getLogger("fetch_paper_info")
    if args.verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    # load quantized LLM
    # if `use_gpu` is True, offload all layers to GPU. Otherwise offload no layer.
    n_gpu_layers = -1 if args.gpu else 0
    llm = Llama.from_pretrained(
        repo_id="QuantFactory/Meta-Llama-3-8B-Instruct-GGUF",
        filename="Meta-Llama-3-8B-Instruct.Q5_K_M.gguf",
        n_gpu_layers=n_gpu_layers,
        n_ctx=3096,  # Llama's context length. 512 by default.
    )

    # fetch papers from arXiv
    search_results = fetch_papers(
        category=args.category,
        date=args.date,
        max_results=args.max_papers,
        logger=logger,
    )

    # extract necessary information from papers
    paperlist = process_results(
        search_results=search_results,
        date=args.date,
        llm=llm,
        data_dir=args.data_dir,
        logger=logger,
    )

    # write to json
    with open(os.path.join(args.data_dir, "papers.json"), "w") as jsonfile:
        jsonfile.write(paperlist.model_dump_json())
