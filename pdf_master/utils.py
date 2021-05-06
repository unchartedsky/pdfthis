import logging
import os
import re
import subprocess
import sys
from urllib.request import urlopen

import requests
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError
from urlextract import URLExtract

_logger = logging.getLogger()

_extractor = URLExtract()


def check_if_url_is_reachable(url):
    try:
        text = "http://" + url if "://" not in url else url

        r = requests.get(text, allow_redirects=True, timeout=1.0)
        return r.status_code == 200 or r.status_code == 201
    except IOError as err:
        return False


def parse_urls(text):
    urls = _extractor.find_urls(text)
    if not urls or len(urls) == 0:
        return []

    links = [("http://" + url if "://" not in url else url) for url in urls]
    links = [url.replace('://blog.naver.com', '://m.blog.naver.com') for url in links]
    return list(set(links))


def get_pdf_filename(url: str):
    try:
        headers = {'User-agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers)

        content_type = r.headers.get('content-type')
        if not content_type.startswith("application/pdf"):
            return None

        for record in r.history:
            location = record.headers.get('location')
            if '.pdf' in location:
                return os.path.basename(location)

        return "noname.pdf"
    except ConnectionError as err:
        _logger.warning(err)
        return None
    except:
        _logger.error("Unexpected error:", sys.exc_info()[0])
        return None


def wget(url: str, cwd: str = None):
    if not cwd:
        cwd = os.getcwd()

    result = subprocess.run(['wget', '--server-response=on',
                             '--adjust-extension=on', '--trust-server-names=on', url], capture_output=True,
                            text=True, cwd=cwd)
    output = result.stdout + result.stderr
    _logger.debug(output)

    actual_filename = _actual_filename(output)
    if not actual_filename:
        return None

    right_filename = _right_filename(output)
    if actual_filename == right_filename:
        return os.path.join(cwd, actual_filename)

    actual_filepath = os.path.join(cwd, actual_filename)
    right_filepath = os.path.join(cwd, right_filename)
    os.rename(actual_filepath, right_filepath)
    return right_filepath

def _actual_filename(output: str):
    match = re.search(r''' - ‘(.+)’ saved''', output)
    if match and match.regs and len(match.regs) > 0:
        location = match.group(1)
        return os.path.basename(location)

    return None

def _right_filename(output: str):
    match = re.search(r'''Content-Disposition: attachment;filename=(.*\.pdf)[;]*''', output)
    if match and match.regs and len(match.regs) > 0:
        location = match.group(1)
        return os.path.basename(location)

    match = re.search(r'''Location: (.*\.pdf)[;]*''', output)
    if match and match.regs and len(match.regs) > 0:
        location = match.group(1)
        return os.path.basename(location)

    return None

def _get_title(url: str):
    r = urlopen(url)
    soup = BeautifulSoup(r, 'html.parser')  # , from_encoding='ISO-8859-1')
    for title in soup.find_all('title'):
        text = title.get_text()
        if text:
            return text
    return None


def percollate(url: str, title: str = None, cwd: str = None):
    if not cwd:
        cwd = os.getcwd()

    if not title:
        title = _get_title(url)

    filename = os.path.normpath('{}.pdf'.format(title))
    _logger.debug(filename)

    result = subprocess.run(
        [
            'percollate', 'pdf', '--no-sandbox', '--css', '''@page { size: A3 }''', url, '-o', filename
        ],
        capture_output=True,
        text=True,
        cwd=cwd
    )
    output = result.stdout + result.stderr
    _logger.debug(output)

    match = re.search(r'''Saved PDF: (.*)''', output)
    if not match or not match.regs or len(match.regs) < 1:
        return ""

    matched = match.group(1)
    output_filename = os.path.basename(matched)
    return os.path.join(cwd, output_filename)
