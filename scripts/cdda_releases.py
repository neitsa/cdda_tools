#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import datetime
import json
import logging
import re
import sys
from timeit import default_timer as timer
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


OWNER = "CleverRaven"
REPO = "Cataclysm-DDA"
URL_TEMPLATE = "https://api.github.com/repos/{owner}/{repository}/releases"
HEADERS = {'User-Agent': 'neitsa'}


class Asset:
    def __init__(self, asset_content: Dict) -> None:
        self._asset_content = asset_content

    def __getattr__(self, item: str):
        return self._asset_content[item]

    def __str__(self) -> str:
        return f"{self.display_name}: {self.download_count}"

    @property
    def display_name(self) -> str:
        return self.label if self.label else self.name

    @property
    def is_curses(self) -> bool:
        return "curses" in self.name.lower()

    @property
    def is_tiles(self) -> bool:
        if "tiles" in self.name.lower():
            return True
        if self.is_android:
            return True
        return False

    @property
    def is_mac(self) -> bool:
        return self.name.endswith(".dmg")

    @property
    def is_windows(self) -> bool:
        name = self.name.lower()
        return "windows" in name or "win" in name

    @property
    def is_linux(self) -> bool:
        return "linux" in self.name.lower()

    @property
    def is_android(self) -> bool:
        return self.name.lower().endswith("apk")

    @property
    def is_32_bit(self) -> bool:
        if "x64" in self.name.lower():
            return False

        if self.is_mac or self.is_android:
            return False

        return True

    @property
    def is_64_bit(self) -> bool:
        return not self.is_32_bit


class Release:
    def __init__(self, content_dict: Dict) -> None:
        logger.debug(f"[TAG] {content_dict['tag_name']}")
        self._content_dict = content_dict
        self.assets: List[Asset] = list()
        assets = content_dict.get("assets")
        if assets:
            for asset_content in assets:
                asset = Asset(asset_content)
                self.assets.append(asset)
                assert asset.is_android or asset.is_linux or asset.is_mac or asset.is_windows
                assert asset.is_curses or asset.is_tiles
            self.assets.sort(key=lambda a: a.display_name)

    def __getattr__(self, item: str):
        return self._content_dict[item]

    @property
    def total_downloads(self) -> int:
        if not self.assets:
            return 0

        return sum([asset.download_count for asset in self.assets])

    def sum_os(self) -> Dict[str, int]:
        f_names = {
            "Android": "is_android",
            "Linux": "is_linux",
            "OSX": "is_mac",
            "Windows": "is_windows"
        }

        result = dict()
        for os_name, func_name in f_names.items():
            os_sum = sum([a.download_count for a in self.assets if getattr(a, func_name)])
            result[os_name] = os_sum

        return result


class PageLoader:
    def __init__(self, owner: str, repository: str) -> None:
        self.url = URL_TEMPLATE.format(owner=owner, repository=repository)
        self._num_pages: int = 1
        self.releases: List[Release] = list()

    @staticmethod
    def _parse_links(headers: dict) -> Optional[List[int]]:
        link: Optional[str] = headers.get("link")
        if not link:
            return None

        matches: List[int] = list()
        for m in re.finditer(r"page=(\d+)", link):
            page_num = int(m.group(1))
            matches.append(page_num)

        matches.sort()
        return matches

    @staticmethod
    def convert_date_time(date_time: str) -> datetime.datetime:
        return datetime.datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%S%z")

    @staticmethod
    def _get_page_content(url: str, **kwargs) -> str:
        start = timer()
        response = requests.get(url, headers=HEADERS)
        end = timer()
        request_time = end - start
        if response.status_code != 200:
            msg = f"Error requesting url: {response.status_code} - url: {url}"
            logger.error(msg)
            raise RuntimeError(msg)
        logger.debug(f"Request time: {request_time} seconds.")
        headers = kwargs.get("headers")
        if headers is not None:
            if isinstance(headers, list):
                headers.append(response.headers)
            else:
                logger.error(f"headers must be a list. Got: '{type(headers)}'.")
        return response.text

    def _get_first_page(self):
        headers = list()
        page_content = self._get_page_content(self.url, headers=headers)
        links = self._parse_links(headers[0])
        if len(links) == 2:
            self._num_pages = links[1]
        logger.info(f"Detected {self._num_pages} release pages.")
        return page_content

    def _parse_release(self, content: List[dict], page_num: int):
        for i, release_content in enumerate(content):
            logger.debug(f"Parsing release #{i} on page {page_num}")
            release = Release(release_content)
            self.releases.append(release)

    def parse_releases(self):
        content = self._get_first_page()
        for i in range(1, self._num_pages + 1):
            if i > 1:
                url = self.url + f"?page={i}"
                content = self._get_page_content(url)
            json_content = json.loads(content)
            self._parse_release(json_content, i)


def main(args):
    page_loader = PageLoader(OWNER, REPO)
    page_loader.parse_releases()

    downloads = list()
    for release in page_loader.releases:
        download = release.total_downloads
        downloads.append(download)
        print(f"{release.name}: {download} [{release.published_at}]")
        for asset in release.assets:
            print(f"    - {asset.display_name}: {asset.download_count}")

    # ---- totals
    total_downloads = sum(downloads)
    print(f"{'-' * 79}\nTotal: {total_downloads}")
    total_per_os = dict()
    for release in page_loader.releases:
        for k, v in release.sum_os().items():
            if k not in total_per_os.keys():
                total_per_os[k] = 0
            total_per_os[k] += v

    print('Total per OS:')
    for k, v in total_per_os.items():
        print(f"    - {k}: {v} [{(v / total_downloads) * 100:.2f}%]")

    return 0


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="TODO")

    arg_parser.add_argument("-l", "--log-level",
                            choices=['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO',
                            help="Set the logging level")

    parsed_args = arg_parser.parse_args()

    logging_level = logging.getLevelName(parsed_args.log_level)
    logging.basicConfig(level=logging_level)
    logger.setLevel(logging_level)

    sys.exit(main(parsed_args))
