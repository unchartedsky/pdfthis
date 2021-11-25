import unittest

import gdown
import pytest


class GoogleDriveTests(unittest.TestCase):
    @pytest.mark.skip(reason="in progress")
    def test_gdown(self):
        url = 'https://drive.google.com/file/d/1XXVsAD-3uYoYMU-LJZ9AllzREQgNuvIY'
        output = '/tmp/20150428_collected_images.pdf'
        r = gdown.download(url, output, quiet=False)
        self.assertEqual(r, output)


if __name__ == '__main__':
    unittest.main()
