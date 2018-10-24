#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from porg import Org

__author__ = "Dima Gerasimov"
__copyright__ = "Dima Gerasimov"
__license__ = "mit"


def test_fib():
    fname = "/L/repos/PyOrgMode/PyOrgMode/test.org"
    org = Org.from_file(fname)
    # TODO scheduling test / clock / properties
    assert 'xxxx' in org.tags

    [node] = ([n for n in org.iterate() if 'CLOCK' == n.heading])
    assert node.properties == {'ORDERED': 't', 'CLOCKSUM': '0'}
