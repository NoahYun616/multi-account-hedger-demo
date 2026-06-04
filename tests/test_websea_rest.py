from __future__ import annotations

import unittest

from clients.websea_rest import WebseaRestClient


class WebseaRestClientTest(unittest.TestCase):
    def test_check_response_raises_on_api_error(self):
        with self.assertRaisesRegex(RuntimeError, "errno=20522"):
            WebseaRestClient._check_response(
                "/v1/futures/wallet",
                {"errno": 20522, "errmsg": "not getting the current user"},
            )

    def test_extracts_net_position(self):
        data = {
            "errno": 0,
            "errmsg": "success",
            "result": [
                {"type": 1, "amount": "5"},
                {"type": 2, "amount": "2"},
            ],
        }

        self.assertEqual(str(WebseaRestClient._extract_position_size(data)), "3")


if __name__ == "__main__":
    unittest.main()
