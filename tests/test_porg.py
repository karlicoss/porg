#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from porg import Org

__author__ = "Dima Gerasimov"
__copyright__ = "Dima Gerasimov"
__license__ = "mit"


def find(org: Org, heading: str):
    [node] = ([n for n in org.iterate() if n.heading == heading])
    return node

def test_fib():
    fname = "/L/repos/PyOrgMode/PyOrgMode/test.org"
    org = Org.from_file(fname)
    # TODO scheduling test / clock / properties
    assert 'xxxx' in org.tags
    node = find(org, 'CLOCK')
    assert node.properties == {'ORDERED': 't', 'CLOCKSUM': '0'}


def test_dates():
    ORG = """
* Hello
** something
 :PROPERTIES:
 :CREATED: [2018-10-23 Tue 20:55]
 :END:

* etc
* [2018-10-23 Tue 20:55] note-with-implicit-date
  sup
** [#A] [2018-10-23 Tue 20:55] also-priority
    """
    org = Org.from_string(ORG)
    node = find(org, 'something')
    print(node.created)


