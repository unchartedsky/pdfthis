import os
import unittest

from dynaconf import Dynaconf

from pdf_master import utils


class UtilsTests(unittest.TestCase):

    def setUp(self):
        settings = Dynaconf(
            envvar_prefix="PDFTHIS",
            settings_files=['settings.yaml', '.secrets.yaml'],
        )

        self._download_dir = settings.bot.download_dir
        if not os.path.exists(self._download_dir):
            os.mkdir(self._download_dir)

    def test_if_text_is_a_valid_url(self):
        self.assertTrue(utils.check_if_url_is_reachable("Github.com/uberple"))

    def test_parse_urls_1(self):
        text = "이것은 URLs을 담은 (github.com/uberple) 의미 없는 https://github.com/unchartedsky/ 문장입니다"
        self.assertEqual(len(utils.parse_urls(text)), 2)

    def test_parse_urls_2(self):
        text = "https://m.deepsearch.com/analytics/company-analysis/KRX:207940"
        self.assertEqual(len(utils.parse_urls(text)), 1)

    def test_parse_urls_3(self):
        text = "https://m.deepsearch.com/KRX:207940"
        self.assertEqual(len(utils.parse_urls(text)), 1)

    def test_parsed_urls_not_include_t_dot_me(self):
        text = '''[미래에셋증권 글로벌 인터넷 정용제]
페이팔 (PYPL US), 1Q21 리뷰: 강화되는 장기 성장성
 
텔레그램: https://t.me/miraeyj
 
1. 1Q21 리뷰:
- 페이팔 1Q21 실적 발표. 컨센서스 대비 매출액 3%, OP 13% 상회
- 매출액 60억달러 (+31% YoY), OP 17억달러 (+89% YoY) 기록. 컨센서스 상회
- 거래금액은 재난지원금 효과와 여행 수요 일부 회복되며 예상치 상회. +50% YoY
- 또한 신규 가입자 +14.5백만명 QoQ 기록. 소폭 둔화에 그치며 예상치 상회
- 다만 매출인식률은 1.97% (-0.08ppt YoY)로 둔화. P2P 강세, 이베이 비중 축소 때문
 
2. 결론
- 페이팔에 대한 투자의견 매수, 목표 주가 USD 311달러 유지
- 거래금액 및 사용자 호조를 반영하여 2021년, 2022년 EPS를 각각 12%, 10% 상향
- PEG 밸류에이션 활용한 타겟 P/E는 기존 50배에서 46배로 변경
- 페이팔 2022년 P/E 36배. 성장 가속화 나타난 2017~2018년 평균 37배와 유사
- 현재 페이팔은 온라인 결제에서 ‘슈퍼앱’으로 변화 시작 단계. 장기 성장성 강화 판단
- 레포트: https://bit.ly/3b8qRVT
 
감사합니다
        '''
        self.assertEqual(len(utils.parse_urls(text)), 1)

    def test_wget_1(self):
        url = "https://bit.ly/3aQ1Puy"

        file_path = utils.wget(url, cwd=self._download_dir)
        self.assertTrue(".pdf" in file_path)
        self.assertTrue(os.path.exists(file_path))

    def test_wget_2(self):
        url = 'https://bit.ly/3tfuGPm'
        file_path = utils.wget(url, cwd=self._download_dir)
        self.assertTrue(".pdf" in file_path)
        self.assertTrue(os.path.exists(file_path))

    def test_wget_3(self):
        url = 'https://bit.ly/3edkGly'
        file_path = utils.wget(url, cwd=self._download_dir)
        self.assertTrue(".pdf" in file_path)
        self.assertTrue('"' not in file_path)
        self.assertTrue(os.path.exists(file_path))

    def test_wget_better_1(self):
        url = 'https://bit.ly/3edkGly'
        file_path = utils.wget_better(url, cwd=self._download_dir)
        self.assertTrue(".pdf" in file_path)
        self.assertTrue('한국' in file_path)
        self.assertTrue(os.path.exists(file_path))

    def test_wget_better_2(self):
        url = "https://bit.ly/3b8qRVT"
        file_path = utils.wget_better(url, cwd=self._download_dir)
        self.assertTrue(".pdf" in file_path)
        self.assertTrue('페이팔' in file_path)
        self.assertTrue(os.path.exists(file_path))

    def test_wget_better_3(self):
        url = "https://bit.ly/3i5GbXs"
        file_path = utils.wget_better(url, cwd=self._download_dir)
        self.assertTrue(".pdf" in file_path)
        self.assertTrue('마이크로소프트' in file_path)
        self.assertTrue(os.path.exists(file_path))

    def test_check_url_has_pdf_1(self):
        url = "https://bit.ly/3aQ1Puy"
        filename = utils.get_pdf_filename(url)
        self.assertTrue('.pdf' in filename)

    def test_check_url_has_pdf_2(self):
        url = "https://bit.ly/3b8qRVT"
        filename = utils.get_pdf_filename(url)
        self.assertTrue('.pdf' in filename)

    def test_check_url_has_not_pdf(self):
        url = "https://github.com"
        self.assertIsNone(utils.get_pdf_filename(url))

    async def test_percollate_blog_naver(self):
        url = 'https://m.blog.naver.com/luy1978/222335229732'
        r = await utils.percollate(url, cwd=self._download_dir)
        self.assertTrue('.pdf' in r)

    def test_get_title_from_news_naver(self):
        url = 'https://news.naver.com/main/read.nhn?mode=LSD&mid=shm&sid1=101&oid=015&aid=0004542985'
        r = utils._get_title(url)
        self.assertTrue('삼성' in r)

    def test_get_title_from_itooza(self):
        url = 'https://www.itooza.com/common/iview.php?no=2021050311132007634&smenu=100&ss=99&qSearch=&qText=&qSort='
        r = utils._get_title(url)
        self.assertTrue('강세주' in r)

    def test_get_pdf_filename(self):
        url = 'http://bbs2.shinhaninvest.com/board/message/file.do?attachmentId=289356'
        filename = utils.get_pdf_filename(url)
        self.assertTrue('bbs' in filename)
