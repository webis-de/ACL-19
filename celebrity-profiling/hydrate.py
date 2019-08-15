#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from pathlib import Path
import yaml
from tweepy.api import API
from tweepy import OAuthHandler, Cursor, AppAuthHandler
import logging
import concurrent.futures
from queue import Queue
from functools import partial


def setup_environment(_config: dict):
    """ make sure the files and paths required are available """
    logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', level=logging.INFO)
    logging.info("Setup Environment")

    _input_file = Path(_config.get("input_file", "./webis-celebrity-corpus-2019-distribution.ndjson"))
    if not _input_file.exists():
        logging.exception("Input distribution file given in the config does not exits, exiting.")
        exit(1)

    _output_path = Path(_config.get("output_path", "./hydrated"))
    if not _output_path.is_dir():
        _output_path.mkdir(parents=True)

    if _config.get("aggregation", "compact") == "complete" and not Path(_output_path / "timelines").is_dir():
        Path(_output_path / "timelines").mkdir()

    return _input_file, _output_path


def get_api_pool(account_config: list) -> Queue:
    """ generates tweepy.api objects for all app and user authentications given in the config """
    account_pool = Queue()
    for account in account_config:
        app_token = account["consumer_key"]
        app_secret = account["consumer_secret"]

        # add app auth
        app_auth = AppAuthHandler(app_token, app_secret)
        account_pool.put(API(app_auth, wait_on_rate_limit=True))

        # add all user auth for this app
        for user_auth in account["user_auth"]:
            auth = OAuthHandler(app_token, app_secret)
            auth.set_access_token(user_auth["access_key"], user_auth["access_secret"])
            account_pool.put(API(auth, wait_on_rate_limit=True))

    return account_pool


def get_celebrity_worker(user: str, api_queue: Queue):
    """ Worker to download user description and timeline """
    user_id = json.loads(user)["id"]
    twitter_api = api_queue.get()
    status = "Done"

    logging.info("getting timeline for user %s" % user_id)
    try:
        user_response = twitter_api.get_user(user_id)._json
        timeline_response = [status._json for status in
                             Cursor(twitter_api.user_timeline, id=user_id, tweet_mode='extended').items()]
    except Exception as e:
        logging.exception("failed %d due to: %s", user_id, str(e))
        status = str(e)
        user_response = None
        timeline_response = None

    api_queue.put(twitter_api)
    return user_id, status, user_response, timeline_response


def store_response(job_result: tuple, output_path: Path, aggregation: str):
    """
    Write the results to output_path, based on the given aggregation method. Logs the results here, skips failed requests
    (i.e. because of deleted, private accounts)
    :param job_result: Tuple given from celebrity_workers with (user_id, status_string, user_json, timeline_list)
    :param output_path: Where to write results
    :param aggregation: method of agg. given in the config
    """
    open("log.txt", "a+").write("{},{}\n".format(job_result[0], job_result[1]))
    if job_result[2] is None or job_result[3] is None:
        return

    if aggregation == "complete":
        open(str(output_path / "users.ndjson"), "a").write(
            json.dumps(job_result[2]) + "\n")
        open(str(output_path / "timelines" / ("%s.ndjson" % job_result[0])), "w").writelines([
            json.dumps(tweet) + "\n" for tweet in job_result[3]
        ])
    elif aggregation == "compact":
        open(str(output_path / "webis-celebrity-corpus-2019-hydrated.ndjson"), "a").write(
            json.dumps({"id": job_result[0], "statuses_count": job_result[2]["statuses_count"],
                        "screen_name": job_result[2]["screen_name"], "lang": job_result[2]["lang"],
                        "followers_count": job_result[2]["followers_count"], "name": job_result[2]["name"],
                        "timeline": [t["full_text"] for t in job_result[3]]}) + "\n"
        )
    else:
        logging.exception("Invalid aggregation method in the config, exiting")
        exit(1)


def hydrate(input_file: Path, output_path: Path, accounts: list, aggregation: str):
    """
    Hydrate the celebrity corpus from the dehydrated version.
    Parameters depend on values in the config.yaml when running this as __main__

    :param input_file: The Path to the dehydrated file
    :param output_path: the output directory, where to store the hydrated version
    :param accounts: a list of Twitter access information
    :param aggregation: "file_wise" one file per author, one line per tweet
                        "compact" one file, one author per line
    """
    api_pool = get_api_pool(accounts)
    logging.info("Start hydration with %s accounts, \nReading from %s \nWriting output to %s",
                 api_pool.qsize(), input_file, output_path)

    job = partial(get_celebrity_worker, api_queue=api_pool)
    with concurrent.futures.ThreadPoolExecutor(max_workers=api_pool.qsize()) as executor:
        for job_result in executor.map(job, open(str(input_file), "r")):
            store_response(job_result, output_path, aggregation)


if __name__ == "__main__":
    """
    This is the hydrator script for the Webis Celebrity Corpus 2019, see https://github.com/webis-de/ACL-19

    Usage:
    (1) Make sure the config.yaml is correct.
    (2) Install the requirements:
      ~# pip install -r requirements.txt
    (3) Run the script
      ~# python3 hydrate.py 

    Contact:
    Matti Wiegmann - matti.wiegmann[at]uni-weimar.de
    Martin Potthast - martin.potthast[at]uni-leipzig.de
    Benno Stein - benno.stein[at]uni-weimar.de

    https://www.webis.de
    """
    config = yaml.load(open("config.yaml", "r"), Loader=yaml.Loader)
    inf, out = setup_environment(config)
    hydrate(inf, out, config["twitter_accounts"], config.get("aggregation", "compact"))
