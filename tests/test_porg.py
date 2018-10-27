#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from datetime import datetime

from porg import Org

__author__ = "Dima Gerasimov"
__copyright__ = "Dima Gerasimov"
__license__ = "mit"


def find(org: Org, heading: str):
    [node] = ([n for n in org.iterate() if n.heading == heading])
    return node

def match(org: Org, hpart: str):
    [node] = ([n for n in org.iterate() if hpart in n.heading])
    return node

def load_test_file():
    # TODO import this file in project
    fname = "/L/repos/PyOrgMode/PyOrgMode/test.org"
    return Org.from_file(fname)


def test_basic():
    org = load_test_file()
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
* [2018-10-11 20:55] note-with-implicit-date
  sup
** [#A] [2018-10-23 Tue 20:55] also-priority

* [2010-01-03 Fri  ] messed-up

* DONE TODO from-kindle Added on Tuesday, October 31, 2017 12:37:24 PM
    this is from kindle...
    TODO ugh, the date probably gets eaten by org parser...

    """
    org = Org.from_string(ORG)

    cc = find(org, 'something')
    assert cc.created == datetime(year=2018, month=10, day=23, hour=20, minute=55)

    cc2 = find(org, 'etc')
    assert cc2.created is None

    cc3 = find(org, 'note-with-implicit-date')
    assert cc3.created == datetime(year=2018, month=10, day=11, hour=20, minute=55)

    cc4 = find(org, 'messed-up')
    assert cc4.created is not None

    cc5 = match(org, 'from-kindle')
    assert cc5.created is not None
    # TODO FIXME must be issue in org parser (look at cc5.heading)
    # assert cc5.created == datetime(year=2017, month=10, day=31, hour=12, minute=37, second=24)


def test_query():
    org = load_test_file()
    print(org.query("//org[contains(heading, 'TAGS TEST')]"))
    # TODO ok, how to get the org entry back?
    # TODO use some sort of id?
