#!/usr/bin/env python3

""" Pulls IP lists from URLs and makes a file to trust them in Apache's remoteip module. """

from typing import List

import logging
import os
import re
import sys
#import tempfile

import click
# from sudo import run_as_sudo

from . import get_results, is_valid_ip, output_file

URL_LIST = [
    "https://www.cloudflare.com/ips-v4",
    "https://www.cloudflare.com/ips-v6",
]


def load_file(filename: str, logger: logging.Logger) -> list:
    """ loads a file, will look for existing IPs with a regex, returns a list of valid IPs """
    filematcher = re.compile(r".*RemoteIPTrustedProxy\s+(?P<address>[a-f0-9\:\/\.]+)")

    loaded_results: List[str] = []
    if not os.path.exists(filename):
        logger.warning("File not found: %s", filename)
        return loaded_results

    logger.debug("Loading and parsing file: %s", filename)
    with open(filename, 'r') as file_handle:
        for line in file_handle.readlines():
            searchresult = filematcher.search(line)
            if searchresult:
                if 'address' not in searchresult.groupdict():
                    logger.debug("Skipping %s, not an IP", line)
                    continue
                if is_valid_ip(searchresult.groupdict()['address']):
                    logger.debug("Adding %s to input data", searchresult.groupdict()['address'])
                    loaded_results.append(searchresult.groupdict()['address'])
    return loaded_results


@click.command()
@click.option("--input", "-i", "input_file", default="./cloudflare-ip-list.conf", type=click.Path(exists=False), help="Load existing list from a file, defaults to ./cloudflare-ip-list.conf")
@click.option("--output", "-o", default="./cloudflare-ip-list.conf", type=click.Path(exists=False), help="Write list to a file, defaults to ./cloudflare-ip-list.conf")
@click.option("--url", "-u", default=URL_LIST, multiple=True, help="URLs to grab, specify multiple times for more than one URL. Defaults to cloudflare's IPv4 and IPv6 lists.")
@click.option("--noop", "-n", is_flag=True, help="Don't make changes")
@click.option("--action", "-a", type=click.Choice(["append", "replace"]), default="replace", help="Either append new entries or replace the file. Default: replace")
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Set logging to debug",
)
# pylint: disable=too-many-arguments,too-many-branches
def cli(input_file: str, output: str, noop: bool, url: list, action: str, debug: bool):
    """ CLI Interface for pulling lists of IPs and making an Apache configuration with RemoteIPTrustedProxy <IP> lines."""

    if debug:
        log_level = "DEBUG"
    else:
        log_level = "INFO"
    log_format = "%(levelname)s\t%(message)s"
    logging.basicConfig(level=getattr(logging, log_level), format=log_format)
    logger = logging.getLogger(__name__)

    logger.debug("In %s mode", action)
    logger.debug("Input file:  %s", input_file)
    logger.debug("Output file: %s", output)

    if noop:
        logger.warning("In noop mode, no files will be changed.")
    else:
        logger.debug("Will modify files.")
    if action == "append" and not os.path.exists(input_file):
        logger.error("Asking to append but input file doesn't exist, bailing.")
        sys.exit(1)
    elif action == "append":
        if output != input_file:
            logger.warning("Setting output to '%s', was '%s' as append mode is enabled.", input_file, output)
        input_data = load_file(input_file, logger)
    else:
        input_data = []

    results = get_results(input_data, action, url, logger)

    if action == "append":
        logger.debug("New IPs to add to list: %s", results)
        if not results:
            logger.debug("Quitting now, no changes to be made")
            sys.exit()
    else:
        logger.debug("Full list: %s", results)

    if not noop:
        _, backup_filename = output_file(output, results, logger, append=(action == "append"))
        if backup_filename:
            logger.warning("Need to clean up backup file %s", backup_filename)
        # TODO: handle testing apachectl config
        # TODO: handle cleaning up when it breaks
        # TODO: clean up when it succeeds
        # TODO: cake


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    cli()
