""" Pulls IP lists from URLs and makes a file to trust them in Apache's remoteip module. """

from datetime import datetime, timezone
from ipaddress import ip_address,  IPv4Network , IPv6Network
import logging
import os
from shutil import copy
import sys
from typing import List

import requests

__version__ = "0.0.1"

def backup_file(original_filename: str, logger: logging.Logger):
    """ makes a backup copy of a file """
    backup_timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M")
    backup_filename = f"{original_filename}-{backup_timestamp}.bak"
    if os.path.exists(backup_filename):
        logger.error("Backup file (%s) already exists, that's a surprise. Bailing hard!", backup_filename)
        sys.exit(1)
    logger.debug("Making a backup of '%s' to '%s'", original_filename, backup_filename)
    return copy(original_filename, backup_filename)


def get_results(input_data: List[str], action: str, url: List[str], logger: logging.Logger) -> List[str]:
    """ does the processing bit """
    return_results = []
    for url_to_grab in url:
        for address in get_url_lines(url_to_grab, logger):
            if action == "append" and address not in input_data:
                logger.debug("Adding new IP %s to list.", address)
                return_results.append(address)
            elif action == "replace":
                logger.debug("Adding %s to list.", address)
                return_results.append(address)
            else:
                logger.debug("Address %s already in list, skipping.", address)
    return return_results

def get_url_lines(url: str, logger: logging.Logger) -> list:
    """ grabs a URL and returns a list of IP addresses """
    lines = []
    try:
        response = requests.get(url)
        response.raise_for_status()
    # TODO: maybe catch some exceptions
    # pylint: disable=broad-except
    except Exception as error_message:
        logger.error("Failed to get %s, bailing: %s", url, error_message)

    for line in response.text.split("\n"):
        if not is_valid_ip(line.strip()):
            raise ValueError()
        lines.append(line)
    return lines

def is_valid_ip(address: str):
    """ tests if a given IP is valid """
    try:
        ip_address(address)
    except ValueError as error_message:
        #print(f"Failed to parse {IP}: {error_message}")
        if ':' in address:
            try:
                IPv6Network(address)
                return True
            except ValueError as error_message:
                print(f"Failed to parse {address}: {error_message}")
        else:
            try:
                IPv4Network(address)
                return True
            except ValueError as error_message:
                print(f"Failed to parse {address}: {error_message}")
        return False
    return True


def make_output_list(input_data: list[str]) -> list[str]:
    """ makes a list of lines of strings, each line will be:

        RemoteIPTrustedProxy <line>
    """

    return [ f"RemoteIPTrustedProxy {ip}" for ip in input_data ]

def output_file(filename: str, data: list, logger: logging.Logger, append: bool=False):
    """ writes a file to a given path, set append to true if you only want to append to the file

        returns a tuple and the original filename and the backup filename, if there was one made
    """
    made_backup = False
    if os.path.exists(filename):
        made_backup = backup_file(filename, logger)

    if not data and append:
        logger.debug("Nothing to change, bailing on output_file")
        return made_backup

    file_mode = "a" if append else "w"
    if append:
        logger.debug("Appending the following entries to the file: %s", ",".join(data))

    update_timestamp = datetime.now(tz=timezone.utc).strftime(" # Updated: %Y-%m-%dT%H:%M:%S%z")
    try:
        with open(filename, file_mode) as file_handle:
            file_handle.write(f"{update_timestamp}\n")
            for line in make_output_list(data):
                file_handle.write(f"{line}\n")
    except PermissionError as error_message:
        logger.error("Permission Error raised attempting to open '%s': %s", filename, error_message)
        sys.exit(1)
    except Exception as error_message: # pylint: disable=broad-except
        logger.error("Exception raised attempting to open '%s': %s", filename, error_message)
        sys.exit(1)

    return made_backup
