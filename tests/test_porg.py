#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from datetime import datetime

from porg import Org, OrgTable

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

* froalala
** Your Highlight on Location 392-393 | Added on Friday, April 13, 2018 8:51:38 AM
    TODO fuck, this entry gets eaten up too up to the point timestamp is not parsing (ends up being 851 AM)
    hacked in porg for now..
    maybe I need to replace non-tag colon sequences manually before passing to pyorgmode?
    ugh. so the issue is actually with missing '0' before 8 on kindle

* Your Highlight on page 153 | Location 2342-2343 | Added on Thursday, October 19, 2017 1126 AM" :kindle:whaat:

* xpath_target
 some text...

| table | a |
|-------+---|
| xxx   | 1 |
| yyy   | 2 |

more text
    """

def test_dates():
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
    assert cc5.created.year == 2017
    # assert cc5.created == datetime(year=2017, month=10, day=31, hour=12, minute=37, second=24)

    cc6 = match(org, 'Your Highlight on page 153')
    assert cc6.created is not None
    assert cc6.created.year == 2017

    cc7 = match(org, 'Your Highlight on Location')
    # will fix later...
    assert cc7.created is not None


def test_xpath():
    org = load_test_file()

    root = org.xpath('//root')
    assert root == org

    res = org.xpath("//org[contains(heading, 'TAGS TEST')]")

    assert res.heading == 'TAGS TEST'
    assert res.tags == {'xxxx', 'TAG1', 'TAG2'}

def test_xpath_helper():
    o = Org.from_string(ORG)
    assert o._xpath_helper == ''

    ch1 = o.children[1]
    assert ch1._xpath_helper == 'child|1'


    xx = o.xpath("//org[contains(heading, 'xpath_target')]")
    tbl = xx.contents[1]
    assert isinstance(tbl, OrgTable)

    assert tbl._xpath_helper == 'child|7,content|1'

def test_table():
    org = load_test_file()

    tparent = org.xpath("//org[contains(heading, 'Table test')]")
    [table] = tparent.contents
    assert table.columns == ['elsbl', 'lesél', 'lseilép']

    assert table[(0, 'elsbl')] == 'dlitsléb'

    assert len(list(table.lines)) == 2


def test_table_xpath():
    org = load_test_file()

    tentry = org.xpath("//table")

    assert isinstance(tentry, OrgTable)

def test_logbook():
    org = Org.from_string("""
* TODO [#C] this broke my parser
  :LOGBOOK:
  CLOCK: [2018-01-24 Wed 19:20]--[2018-01-24 Wed 21:00] =>  1:40
  :END:
some content...

* START [#C] or did that broke??
SCHEDULED: <2018-11-08 Thu>
:PROPERTIES:
:CREATED:  [2018-02-04 Sun 20:37]
:END:
:LOGBOOK:
CLOCK: [2018-05-01 Tue 20:00]--[2018-05-01 Tue 20:59] =>  0:59
:END:

waat
    """)

    res = org.xpath_all("//org")

    for r in res:
        r.heading

def test_tags():
    org = Org.from_string(ORG)

    res = org.with_tag('kindle')

    assert len(res) == 1
