import logging
import os
import re
import subprocess
import urllib
from urllib.error import HTTPError

import requests
import tldextract
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


def _find_js_redirect(r):
    try:
        content = r.read().decode()

        match = re.search(r'''^\s*window.location.href\s*=\s*["'](http[s*]://.*)["'].*;''', content,
                          re.IGNORECASE | re.MULTILINE)
        if match and match.regs and len(match.regs) > 0:
            return match.group(1)

        return None
    except (ConnectionError, HTTPError, UnicodeDecodeError) as err:
        _logger.warning(err)
        return None


def _parse_url(url):
    text = "http://" + url if "://" not in url else url

    try:
        req = urllib.request.Request(text)
        req.add_header('User-Agent',
                       'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0')
        r = urllib.request.urlopen(req)

        js_redirect = _find_js_redirect(r)
        if js_redirect:
            return js_redirect

        return r.url
    except (ConnectionError, HTTPError, urllib.error.URLError) as err:
        _logger.warning(err)
        return text
    # except:
    #     _logger.error("Unexpected error:", sys.exc_info()[0])
    #     return None


def _parse_urls(text):
    urls = _extractor.find_urls(text)
    if not urls or len(urls) == 0:
        return []

    links = []
    for url in urls:
        link = _parse_url(url)
        if not link:
            continue

        links.append(link)

    links = [("http://" + url if "://" not in url else url) for url in links]
    links = [url.replace('://blog.naver.com', '://m.blog.naver.com') for url in links]
    links = [url.replace('://cafe.naver.com', '://m.cafe.naver.com') for url in links]
    links = [url.replace('://post.naver.com', '://m.post.naver.com') for url in links]
    return list(set(links))


def parse_urls(text):
    urls = _parse_urls(text)

    allowed = []
    for url in urls:
        r = tldextract.extract(url)
        if not r:
            continue
        if not r.registered_domain:
            continue
        if r.registered_domain.casefold() == "t.me".casefold():
            continue
        allowed.append(url)

    return allowed


def get_pdf_filename(url: str):
    try:
        # headers = {'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0'}
        # r = requests.head(url, headers=headers, allow_redirects=True)
        req = urllib.request.Request(url)
        req.add_header('User-Agent',
                       'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0')
        r = urllib.request.urlopen(req)

        content_type = r.headers.get('content-type')
        if not content_type.startswith("application/pdf") and not content_type.startswith('application/octet-stream'):
            return None

        filename = r.info().get_filename()
        if filename and len(filename) > 0:
            return filename

        # disposition = r.headers.get('Content-Disposition')
        # if disposition:
        #     header = urllib.parse.unquote(disposition)
        #     parsed = rfc6266_parser.parse_headers(disposition)
        #
        #     if 'miraeasset.com/bbs' in r.url:
        #         filename_nfc = normalize('NFC', header)
        #         header = header.encode('ISO-8859-1').decode('cp949')
        #     else:
        #         encoded = header.encode()
        #         detected_encoding = chardet.detect(encoded).get('encoding')
        #         if detected_encoding:
        #             header = encoded.decode(detected_encoding)
        #     filename = re.findall("filename=(.+)", header)[0]
        #     return filename

        # for record in r.history:
        #     location = record.headers.get('location')
        #     if '.pdf' in location:
        #         return os.path.basename(location)

        if r.url.endswith('.pdf'):
            return os.path.basename(r.url)

        return None

    except (ConnectionError, HTTPError) as err:
        _logger.warning(err)
        return None
    # except:
    #     _logger.error("Unexpected error:", sys.exc_info()[0])
    #     return None


def wget_better(url: str, cwd: str = None):
    filepath = wget(url, cwd)
    if not filepath:
        _logger.debug("wget has failed.")
        return None

    extracted = _extract_pdftitle(filepath)
    if not extracted:
        _logger.debug("Extracting PDF title is failed.")
        return filepath

    new_filename = extracted if extracted.endswith('.pdf') else '{}.pdf'.format(extracted)
    new_filename = new_filename.replace('/', u'\u2215')

    dirname = os.path.dirname(filepath)
    filename = os.path.basename(filepath)

    _logger.debug("wget_better:_mv")
    return _mv(dirname, filename, new_filename)


def _extract_pdftitle(filepath: str):
    # filepath = f'"{filepath}"'
    args_list = [
        ['pdftitle', "-a", "original", '-p', filepath],
        ['pdftitle', "-a", "max2", '-p', filepath],
        ['pdftitle', "-a", "eliot", "--eliot-tfs", "1", '-p', filepath]
    ]

    for args in args_list:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True
        )
        output = result.stdout + result.stderr
        output = output.strip()

        if result.returncode != 0:
            _logger.error(output)
            continue

        if output:
            return os.path.normpath(output)

    return None


def wget(url: str, cwd: str = None):
    if not cwd:
        cwd = os.getcwd()

    result = subprocess.run([
        'wget',
        '--server-response=on', '--no-if-modified-since',
        '--no-use-server-timestamps', '--adjust-extension=on',
        '--trust-server-names=on', "--user-agent='Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)'",
        url],
        capture_output=True,
        text=True, cwd=cwd)

    output = result.stdout + result.stderr
    output = output.strip()

    if result.returncode != 0:
        _logger.error(output)
        _logger.error("Return value is {}".format(result.returncode))
        return None

    _logger.debug(output)

    actual_filename = _actual_filename(output)
    if not actual_filename:
        _logger.debug("The actual file name is not retrieved.")
        return None

    right_filename = _right_filename(output)
    if actual_filename == right_filename or not right_filename:
        return os.path.join(cwd, actual_filename)

    _logger.debug("wget:_mv")
    return _mv(cwd, actual_filename, right_filename)


def _mv(cwd, src, dst):
    _logger.debug("File {} in a directory {} is being moved to {}".format(src, cwd, dst))

    cwd_pushed = os.getcwd()
    os.chdir(cwd)
    os.rename(src, dst)
    os.chdir(cwd_pushed)
    return os.path.join(cwd, dst)


def _actual_filename(output: str):
    match = re.search(r''' - [‘'](.+)[’'] saved''', output)
    if match and match.regs and len(match.regs) > 0:
        location = match.group(1)
        return os.path.basename(location)

    # Server file no newer than local file ‘20210429_207940_bhh1026_757.pdf’ -- not retrieving.
    match = re.search(r'''local file [‘'](.+)[’'] -- not retrieving''', output)
    if match and match.regs and len(match.regs) > 0:
        location = match.group(1)
        return os.path.basename(location)

    if not output.endswith(".pdf"):
        return '{}.pdf'.format(output)

    return None


def _right_filename(output: str):
    match = re.search(r'''Content-Disposition:.*filename=["]*(.*\.pdf)[";]*''', output, re.IGNORECASE)
    if match and match.regs and len(match.regs) > 0:
        location = match.group(1)
        _logger.debug("Header Content-Disposition is found: {}".format(location))

        location = urllib.parse.unquote(location)
        location = location.replace('/', u'\u2215')  # 파일이름에 '/'가 들어간 경우
        location = os.path.normpath(location)
        return os.path.basename(location)

    match = re.search(r'''Location: (.*\.pdf)[;]*''', output)
    if match and match.regs and len(match.regs) > 0:
        location = match.group(1)
        _logger.debug("Header Location is found: {}".format(location))

        filename = os.path.basename(location)
        return filename.replace('/', u'\u2215')

    return None


def _get_title(url: str):
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent',
                       'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0')
        r = urllib.request.urlopen(req)

        soup = BeautifulSoup(r, 'html.parser')  # , from_encoding='ISO-8859-1')
        for title in soup.find_all('title'):
            text = title.get_text()
            if text:
                return text
        return None
    except (ConnectionError, HTTPError) as err:
        _logger.warning(err)
        return None


def percollate(url: str, title: str = None, cwd: str = None):
    if not cwd:
        cwd = os.getcwd()

    if not title:
        title = _get_title(url)

    filename = os.path.normpath('{}.pdf'.format(title))

    cmd = [
        'percollate', 'pdf', '--no-sandbox', '--css', '''@page { size: A3 }''', url, '-o', filename
    ]
    _logger.debug("Percollate is being run: ".join(cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd
    )

    output = result.stdout + result.stderr
    output = output.strip()

    if result.returncode != 0:
        _logger.error(output)
        return None

    _logger.debug(output)

    match = re.search(r'''Saved PDF: (.*)''', output)
    if not match or not match.regs or len(match.regs) < 1:
        return ""

    matched = match.group(1)
    output_filename = os.path.basename(matched)
    return os.path.join(cwd, output_filename)
