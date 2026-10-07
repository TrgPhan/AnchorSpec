"""Read-only web discovery; logs errors as evidence, never assumes success."""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urljoin


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(value for key, value in attrs if key == 'href')


if __name__ == '__main__':
    url = 'https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/data-sets-and-download'
    try:
        body = urlopen(url, timeout=30).read().decode()
        parser = Links()
        parser.feed(body)
        result = {'url': url, 'links': sorted(set(urljoin(url, x) for x in parser.links))}
    except Exception as error:
        result = {'url': url, 'error': repr(error)}
    target = Path(__file__).resolve().parent / 'source_discovery.json'
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))