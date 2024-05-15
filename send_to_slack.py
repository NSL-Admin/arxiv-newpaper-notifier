import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient

from block import get_paper_block
from const import ARXIV_CATEGORIES, PaperList

parser = argparse.ArgumentParser(
    description="Send information of the latest papers to Slack"
)
parser.add_argument(
    "--category",
    help="Category ID to search for papers of",
    choices=ARXIV_CATEGORIES,
    required=True,
)
parser.add_argument(
    "--channel-id",
    help="ID of the Slack channel to send to",
    required=True,
)
parser.add_argument(
    "--data-dir",
    help="Path to a directory to store data in",
    default=os.path.join(os.path.dirname(__file__), "data"),
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
    load_dotenv()

    # globally enable logging (to stdout)
    logging.basicConfig()

    # create logger for logs from this app
    logger = logging.getLogger("send_to_slack")
    if args.verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    # create Slack client
    client = WebClient(token=os.environ["SLACK_API_TOKEN"])

    # load paperlist from json
    with open(os.path.join(args.data_dir, f"papers-{args.category}.json")) as jsonfile:
        paper_list = PaperList.model_validate_json(jsonfile.read())

    if not paper_list.papers:
        # No paper appeared on that day
        sys.exit()

    # build parent message and send it
    paper_titles = list(map(lambda x: x.title, paper_list.papers))
    parent_msg = f'*The last {len(paper_titles)} papers of those submitted on {paper_list.date.strftime("%Y-%m-%d")} (UTC)*\n'
    for idx, title in enumerate(paper_titles):
        parent_msg += f"{idx+1}. {title}\n"
    slack_resp = client.chat_postMessage(
        channel=args.channel_id, text=parent_msg, mrkdwn=True
    )

    # send detail of each paper to a thread dangling from the parent message
    for paper in paper_list.papers:
        # 0 byte image sometimes appears, so filter it out here
        if paper.first_figure_path and os.path.getsize(paper.first_figure_path) > 0:
            with open(paper.first_figure_path, "rb") as imagefile:
                fileupload_resp = client.files_upload_v2(
                    filename=os.path.basename(paper.first_figure_path),
                    content=imagefile.read(),
                )
                time.sleep(10)  # IMPORTANT: wait for the upload to complete!
            image_fileid = fileupload_resp.data["file"]["id"]  # type:ignore
        else:
            image_fileid = None
        try:
            client.chat_postMessage(
                text=f"summary of {paper.title}",
                channel=args.channel_id,
                blocks=get_paper_block(paper=paper, image_fileid=image_fileid),
                thread_ts=slack_resp.data["ts"],  # type:ignore
            )
        except SlackApiError:
            # some image files lead to "[ERROR] invalid slack file" error.
            # In that case, remove the image from the block and try to send again
            client.chat_postMessage(
                text=f"summary of {paper.title}",
                channel=args.channel_id,
                blocks=get_paper_block(paper=paper, image_fileid=None),
                thread_ts=slack_resp.data["ts"],  # type:ignore
            )
        time.sleep(1)  # sleep for 1 second
