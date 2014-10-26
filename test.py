# -*- coding: utf-8 -*-
import unittest
from pycdek import Client


class TestCDEK(unittest.TestCase):
    def test_get_delivery_points(self):
        response = Client.get_delivery_points(44)
        self.assertIsInstance(response, list)
        self.assertGreater(len(response), 0)

    def test_get_shipping_cost(self):
        response = Client.get_shipping_cost(137, 44, [11, 16, 137], goods=[
            {'weight': 2, 'length': 100, 'width': 10, 'height': 20}
        ])
        self.assertIsInstance(response, dict)
        self.assertIsNone(response.get('error'))
