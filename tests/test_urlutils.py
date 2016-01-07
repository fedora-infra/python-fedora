#!/usr/bin/python2 -tt
# -*- coding: utf-8 -*-

""" Test the OpenIdBaseClient. """

import unittest

from fedora.urlutils import update_qs

base = 'http://threebean.org/'

class TestURLUtils(unittest.TestCase):
    def test_simple_add(self):
        original = base
        expected = base + "?foo=yes"
        params = dict(foo="yes")
        actual = update_qs(original, params)
        self.assertEqual(actual, expected)

    def test_simple_idempotence(self):
        original = base + "?foo=yes"
        expected = base + "?foo=yes"
        params = dict(foo="yes")
        actual = update_qs(original, params)
        self.assertEqual(actual, expected)

    def test_simple_with_overwrite(self):
        original = base + "?foo=yes"
        expected = base + "?foo=no"
        params = dict(foo="no")
        actual = update_qs(original, params)
        self.assertEqual(actual, expected)

    def test_simple_without_overwrite(self):
        original = base + "?foo=yes"
        expected = base + "?foo=yes&foo=no"
        params = dict(foo="no")
        actual = update_qs(original, params, overwrite=False)
        self.assertEqual(actual, expected)

    def test_simple_without_overwrite_and_same(self):
        original = base + "?foo=yes"
        expected = base + "?foo=yes&foo=yes"
        params = dict(foo="yes")
        actual = update_qs(original, params, overwrite=False)
        self.assertEqual(actual, expected)

    def test_simple_with_tuples(self):
        original = base
        expected = base + "?foo=yes"
        params = [('foo', 'yes')]
        actual = update_qs(original, params)
        self.assertEqual(actual, expected)
