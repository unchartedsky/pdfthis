import os
import tempfile
import unittest

from pdf_master import utils


class UtilsTests(unittest.TestCase):
    _tmpdir = tempfile.mkdtemp()

    def test_if_text_is_a_valid_url(self):
        self.assertTrue(utils.check_if_url_is_reachable("Github.com/uberple"))

    def test_parse_urls(self):
        text = "이것은 URLs을 담은 (github.com/uberple) 의미 없는 https://github.com/unchartedsky/ 문장입니다"
        self.assertEqual(len(utils.parse_urls(text)), 2)

    def test_wget_1(self):
        url = "https://bit.ly/3aQ1Puy"

        file_path = utils.wget(url, cwd=self._tmpdir)
        self.assertTrue(".pdf" in file_path)
        self.assertTrue(os.path.exists(file_path))

    def test_wget_2(self):
        url = 'https://bit.ly/3tfuGPm'
        file_path = utils.wget(url, cwd=self._tmpdir)
        self.assertTrue(".pdf" in file_path)
        self.assertTrue(os.path.exists(file_path))

    def test_wget_3(self):
        url = 'https://bit.ly/3edkGly'
        file_path = utils.wget(url, cwd=self._tmpdir)
        self.assertTrue(".pdf" in file_path)
        self.assertTrue('"' not in file_path)
        self.assertTrue(os.path.exists(file_path))

    def test_wget_better_1(self):
        url = 'https://bit.ly/3edkGly'
        file_path = utils.wget_better(url, cwd=self._tmpdir)
        self.assertTrue(".pdf" in file_path)
        self.assertTrue('한국' in file_path)
        self.assertTrue(os.path.exists(file_path))

    def test_check_url_has_pdf(self):
        url = "https://bit.ly/3aQ1Puy"
        self.assertTrue('.pdf' in utils.get_pdf_filename(url))

    def test_check_url_has_not_pdf(self):
        url = "https://github.com"
        self.assertIsNone(utils.get_pdf_filename(url))

    def test_percollate_blog_naver(self):
        url = 'https://m.blog.naver.com/luy1978/222335229732'
        r = utils.percollate(url, cwd=self._tmpdir)
        self.assertTrue('.pdf' in r)

    def test_get_title_from_itooza(self):
        url = 'https://www.itooza.com/common/iview.php?no=2021050311132007634&smenu=100&ss=99&qSearch=&qText=&qSort='
        r = utils._get_title(url)
        self.assertTrue('강세주' in r)

