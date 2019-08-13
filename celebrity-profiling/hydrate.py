#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from pathlib import Path
import yaml
from tweepy.api import API
from tweepy import OAuthHandler, RateLimitError, Cursor
from tweepy.error import TweepError
from time import sleep
import logging
from math import inf


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


def download_users(input_file, accounts):
    for user in open(str(input_file), "r"):
        u = json.loads(user)
        logging.info("getting timeline for user %s" % u["id"])
        try:
            yield get_user(u["id"], accounts), get_timeline(u["id"], accounts)
        except TweepError:
            logging.info("user %s not available" % u["id"])


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
    logging.info("Start hydration with %s accounts, \nReading from %s \nWriting output to %s",
                 len(accounts), input_file, output_path)
    for user_data, timeline in download_users(input_file, accounts):
        logging.info("Start aggregation")
        if aggregation == "complete":
            open(str(output_path / "users.ndjson"), "a").write(
                json.dumps(user_data) + "\n")
            open(str(output_path / "timelines" / ("%s.ndjson" % user_data["id"])), "w").writelines([
                json.dumps(tweet) + "\n" for tweet in timeline
            ])
        elif aggregation == "compact":
            open(str(output_path / "webis-celebrity-corpus-2019-hydrated.ndjson"), "a").write(

                json.dumps({"id": user_data["id"], "statuses_count": user_data["statuses_count"],
                            "screen_name": user_data["screen_name"], "lang": user_data["lang"],
                            "followers_count": user_data["followers_count"], "name": user_data["name"],
                            "timeline": [t["full_text"] for t in timeline]}) + "\n"
            )
        else:
            logging.exception("Invalid aggregation method in the config, exiting")
            exit(1)


def get_api(accounts: list, limit_type: tuple = None):
    """
    return a tweepy api element, based on which account has a free limit.
    If non is free, sleep here until it is.
    If there is only one account configured, wait via tweepy
    """
    if len(accounts) == 1:
        # there is only one account, so we don't consider account switching to circumvent rate limits
        auth = OAuthHandler(accounts[0]["consumer_key"], accounts[0]["consumer_secret"])
        auth.set_access_token(accounts[0]["access_key"], accounts[0]["access_secret"])
        return API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

    lowest_to_reset = inf
    for account in accounts:
        auth = OAuthHandler(account["consumer_key"], account["consumer_secret"])
        auth.set_access_token(account["access_key"], account["access_secret"])
        twitter = API(auth)
        rate_limit = twitter.rate_limit_status()
        if rate_limit['resources'][limit_type[0]][limit_type[1]]["remaining"] > 0:
            return twitter
        lowest_to_reset = min(lowest_to_reset, rate_limit['resources'][limit_type[0]][limit_type[1]]["reset"])
    else:
        logging.info("all rate limits reached, sleeping %s ms until reset", lowest_to_reset)
        sleep(lowest_to_reset / 1000)
        return get_api(accounts, limit_type)


def get_user(user_id: int, accounts: list):
    """ Get the latest Twitter user object of a given user_id and return. """
    twitter = get_api(accounts, ('users', '/users/show/:id'))
    return twitter.get_user(user_id)._json


def get_timeline(user_id: int, accounts: list):
    """ Get the latest Twitter timeline of the given user as a list of status responses. """
    twitter = get_api(accounts, ('statuses', '/statuses/user_timeline'))
    try:
        return [status._json for status in Cursor(twitter.user_timeline, id=user_id, tweet_mode='extended').items()]
    except RateLimitError as e:
        logging.warning("RateLimitError while downloading a timeline, will try again with a different account. "
                        "This may be a common event.", e)
        return get_timeline(user_id, accounts)


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
