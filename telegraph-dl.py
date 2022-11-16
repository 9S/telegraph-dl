#!/usr/bin/env python3

import os.path
import sys
from argparse import Namespace
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import argparse
from urllib.parse import urljoin, urlparse

from requests import Response, get


class TelegraphParser(HTMLParser):
    title: str = ""
    image_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Extracting the Title
        if tag == 'meta':
            # Check if we are in the og:title tag
            tag_matches = len([(name, value) for (name, value) in attrs if name == 'property' and value == 'og:title'])
            if tag_matches != 1:
                return
            # Extract the content
            value: list[str] = [value for (name, value) in attrs if name == 'content' and value is not None]
            if len(value) != 1:
                fallback: str = datetime.now().isoformat(timespec='minutes')
                print(f"Cannot extract title from document. Falling back to `{fallback}`", file=sys.stderr)
                self.title = fallback
                return
            # Set the title
            self.title = value[0]

        # Extracting the image sources
        if tag == "img":
            extracted_src: list[str] = [value for (name, value) in attrs if name == 'src' and value is not None]
            if len(extracted_src) != 1:
                return

            self.image_urls.append(extracted_src[0])


if __name__ == '__main__':
    argsparser = argparse.ArgumentParser(description="download images from https://telegra.ph/")
    argsparser.add_argument("--outdir", metavar='outdir', type=str, nargs='?', default='.', help="output directory")
    argsparser.add_argument("urls", metavar='url', type=str, nargs='+', help="urls to download")

    args: Namespace = argsparser.parse_args()

    for url in args.urls:
        print(f"Fetching {url}")
        html_response: Response = get(url)

        parser = TelegraphParser()
        parser.feed(html_response.content.decode())

        title: str = parser.title.replace('<>:"/\\|?* ', '')
        image_urls: list[str] = [urljoin(url, image_url) for image_url in parser.image_urls]
        total_count = len(image_urls)
        print(f"Title: {title}")
        print(f"Extracted {total_count} image urls")

        Path(args.outdir, title).mkdir(parents=True, exist_ok=True)

        for index, image_url in enumerate(image_urls):
            url_path: str = urlparse(image_url).path
            base_name: str = os.path.basename(url_path)
            print(f"({index+1}/{total_count}) Downloading {base_name}")

            image_response: Response = get(image_url)
            with open(Path(args.outdir, title, base_name), 'wb') as file:
                file.write(image_response.content)

        print("Done!")
