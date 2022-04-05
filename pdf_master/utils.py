import logging
import os
import re
import subprocess
import urllib
from datetime import date
from urllib.error import HTTPError

import gdown
import requests
import tldextract
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError
from slugify import slugify
from urlextract import URLExtract

_logger = logging.getLogger()

_extractor = URLExtract()


# def slugify_better(text, with_ext=None):
#     r = text.replace('/', u'\u2215')  # 파일이름에 '/'가 들어간 경우
#     return r

def slugify_better(text, with_ext=False):
    # r = text.replace('/', u'\u2215')  # 파일이름에 '/'가 들어간 경우
    filename = text[:min(len(text), 64)]
    ext = ''
    if with_ext:
        filename = text[:text.find('.')]
        ext = text.replace(filename, '')

    basename_slugfied = slugify(
        filename,
        separator=' ',
        save_order=True,
        lowercase=False,
        entities=True,
        decimal=True,
        hexadecimal=True,
        allow_unicode=True,
        replacements=[['.', '.'], ['/', u'\u2215']]
    )
    return "{}{}".format(basename_slugfied, ext)


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

        if r.url.endswith('.pdf'):
            return os.path.basename(r.url)

        return None

    except (ConnectionError, HTTPError) as err:
        _logger.warning(err)
        return None
    # except:
    #     _logger.error("Unexpected error:", sys.exc_info()[0])
    #     return None


def contains_korean(text):
    hangul = re.compile('[\u3131-\u3163\uac00-\ud7a3]+')
    result = hangul.findall(text)
    return len(result)


def gdown_better(url: str, cwd: str = None):
    cwd_old = os.getcwd()
    if not cwd:
        os.chdir(cwd)

    filepath = gdown.download(url, quiet=False, fuzzy=True)
    if not cwd:
        os.chdir(cwd_old)

    if not filepath or not '.pdf' in filepath:
        _logger.error("gdown has failed.")
        return None

    # if bool(re.match('[a-zA-Z0-9\s]+$', filepath)):
    if not contains_korean(filepath):
        return filepath

    return rename_pdf(filepath)


def wget_better(url: str, cwd: str = None):
    filepath = wget(url, cwd)
    if not filepath:
        _logger.debug("wget has failed.")
        return None

    return rename_pdf(filepath)


def rename_pdf(filepath: str):
    extracted = _extract_pdftitle(filepath)
    if not extracted:
        _logger.debug("Extracting PDF title is failed.")
        return filepath

    if extracted.endswith('.pdf'):
        new_filename = slugify_better(extracted, True)
    else:
        new_filename = '{}.pdf'.format(
            slugify_better(extracted, False)
        )

    dirname = os.path.dirname(filepath)
    filename = os.path.basename(filepath)

    return _mv(dirname, filename, new_filename)


def _run_pdf_title(args: list):
    result = subprocess.run(
        args,
        capture_output=True,
        text=True
    )
    output = result.stdout + result.stderr
    output = output.strip()

    if result.returncode != 0:
        _logger.error(output)
        return ''

    if output:
        return os.path.normpath(output)


# TODO 일단 지저분하게 구현하자
def _extract_company(filepath: str):
    args_list = [
        ['pdftitle', "-a", "original", '-p', filepath],
        ['pdftitle', "-a", "max2", '-p', filepath],
    ]

    for i in range(0, 3):
        args_list.append(
            ['pdftitle', "-a", "eliot", "--eliot-tfs", "{}".format(i), '-p', filepath]
        )

    for args in args_list:
        title = _run_pdf_title(args)
        if not title:
            continue

    return title


def _extract_pdfsubtitles(filepath: str):
    company = _extract_company(filepath)
    if not company:
        return ('', '', '')

    comment = ""
    rate = ""

    for i in range(0, 3):
        text_args = ['pdftitle', "-a", "eliot", "--eliot-tfs", "{}".format(i), '-p', filepath]
        text = _run_pdf_title(text_args)
        if not text:
            continue
        if text == company:
            continue

        text_lowered = text.lower()

        if any(x in text_lowered for x in ['buy', 'overweight', 'sell', 'not rated']):
            rate = text
        else:
            comment = text

        if not comment and not rate:
            break

    if not comment:
        comment = date.today().isoformat()

    return (company, comment, rate)


def _extract_pdftitle(filepath: str):
    company, comment, rate = _extract_pdfsubtitles(filepath)
    if not company:
        return None

    text = company
    if comment:
        text = "{}; {}".format(text, comment)
    if rate:
        text = "{}; {}".format(text, rate)
    return text


def wget(url: str, cwd: str = None):
    if not cwd:
        cwd = os.getcwd()

    # with contextlib.suppress(FileNotFoundError):
    #     os.remove(filename)

    result = subprocess.run(
        [
            'wget',
            '--server-response=on', '--no-if-modified-since',
            '--no-use-server-timestamps', '--adjust-extension=on',
            '--trust-server-names=on', "--user-agent='Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)'",
            url
        ],
        capture_output=True,
        text=True, cwd=cwd
    )

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
        location = slugify_better(location, with_ext=True)
        location = os.path.normpath(location)
        return os.path.basename(location)

    match = re.search(r'''Location: (.*\.pdf)[;]*''', output)
    if match and match.regs and len(match.regs) > 0:
        location = match.group(1)
        _logger.debug("Header Location is found: {}".format(location))

        filename = os.path.basename(location)
        return slugify_better(filename, with_ext=True)

    return None


def _get_title(url: str):
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent',
                       'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0')
        r = urllib.request.urlopen(req)

        # from_encoding = None
        site_encodings = [
            ('kmib.co.kr', 'cp-949')
        ]
        for site_encoding in site_encodings:
            site, from_encoding = site_encoding
            if site in url.lower():
                break

        soup = BeautifulSoup(r, 'html.parser', from_encoding=from_encoding)
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
        title = slugify_better(title)

    filename = os.path.normpath('{}.pdf'.format(title))

    cmd = [
        'percollate', 'pdf', '--no-sandbox', '--css', '''@page { size: A4 }''', url, '-o', filename
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
