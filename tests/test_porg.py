#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime

from porg import Org, OrgTable

import pytest

__author__ = "Dima Gerasimov"
__copyright__ = "Dima Gerasimov"
__license__ = "mit"


def _load_test_file(name: str) -> Org:
    return Org.from_file(Path(__file__).parent / 'data' / name)


def test_file() -> Org:
    return _load_test_file('test.org')


def org_brain_file() -> Org:
    # TODO need to touch every date and note
    return _load_test_file('org-brain-readme.org')


def org_sublime_file() -> Org:
    return _load_test_file('sublime_text2_shortcuts.org')


def test_heading():
    org = test_file()
    assert org.children[0].heading == 'Test Orgmode'


def test_file_body():
    org = test_file()
    assert org.body == '''
#+FILETAGS: :xxxx:yyy:
preamble...'''.lstrip()


def test_filetags():
    org = test_file()
    assert org.tags == {'xxxx', 'yyy'}


def test_file_settings():
    org = org_sublime_file()
    assert org.file_settings == {
        'TITLE' : ['Sublime Text 2 Shortcuts'],
        'ROOT'  : ['Sublime Text 2'],
        'AUTHOR': ['Sreejith Kesavan'],
    }


def test_unicode():
    org = org_sublime_file()
    assert org.children[0].children[1].heading == 'Go to Project (⌘ + Control + P)'


def test_children():
    org = org_sublime_file()
    assert len(org.children[3].children) == 20


def find(org: Org, heading: str):
    [node] = ([n for n in org.iterate() if n.heading == heading])
    return node

def match(org: Org, hpart: str):
    [node] = ([n for n in org.iterate() if hpart in n.heading])
    return node


def test_properties():
    org = test_file()
    node = find(org, 'entry with props')
    assert isinstance(node, Org)

    assert node.properties == {
        'CUSTOM_ID': 'alalal',
        'PUBLISHED': '[2019-05-06 Mon 16:25]',
    }
    # TODO logbook?


ORG = """
somthing on top...


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
** xxxx child node

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
    assert cc.properties == {'CREATED': '[2018-10-23 Tue 20:55]'}
    assert cc.created == datetime(year=2018, month=10, day=23, hour=20, minute=55)

    cc2 = find(org, 'etc')
    assert cc2.created is None

    cc3 = find(org, 'note-with-implicit-date')
    assert cc3.created == datetime(year=2018, month=10, day=11, hour=20, minute=55)

    cc4 = find(org, 'messed-up')
    assert cc4.created is not None

    cc5 = match(org, 'from-kindle')
    cc6 = match(org, 'Your Highlight on page 153')
    cc7 = match(org, 'Your Highlight on Location')


def test_xpath():
    org = org_brain_file()
    res = org.xpath("//org[contains(heading, 'ifle')]")

    assert res.heading == '[[https://github.com/alphapapa/helm-org-rifle][helm-org-rifle]]'
    assert res.parent.heading == 'Other useful packages'


def test_url_heading():
    org = Org.from_string("""
* [2016-05-14 Sat 15:33] [[https://www.reddit.com/r/androidapps/comments/4i36z9/how_you_use_your_android_to_the_maximum/d2uq24i][sc4s2cg comments on How you use your android to the maximum?]] :android:
    """)

    assert org.children[0].heading == '[[https://www.reddit.com/r/androidapps/comments/4i36z9/how_you_use_your_android_to_the_maximum/d2uq24i][sc4s2cg comments on How you use your android to the maximum?]]'


_root_org = """
#+FILETAGS: :whatever:tag2:

top
* note1
* note2
* note3
    """.lstrip()

def test_root():
    org = Org.from_string(_root_org)

    assert org.heading == ''
    assert org.tags == {'whatever', 'tag2'}
    assert org.self_tags == {'whatever', 'tag2'}
    assert org.file_settings == {'FILETAGS': [':whatever:tag2:']}

    # TODO not so sure about including filetags...
    # TODO what semantics does heading have for root node??
    assert org.get_raw(recursive=False) == """
#+FILETAGS: :whatever:tag2:

top""".lstrip()
    assert len(org.children) == 3
    assert [c.heading for c in org.children] == ['note1', 'note2', 'note3']
    assert org.level == 0


def test_root_xpath():
    org = Org.from_string(_root_org)
    root = org.xpath('//root')
    assert root == org

    orgs = org.xpath_all('//org')
    assert len(orgs) == 3

    # TODO ugh. need to do something like that?...
    rc = org.firstlevel()
    assert len(rc) == 3


def test_table():
    org = org_brain_file()

    tparent = org.xpath("//org[contains(heading, 'org-brain-visualize')]")
    # TODO not sure how contents is meant to behave with respect to newlines..
    [table1, _] = [c for c in tparent.contents if isinstance(c, OrgTable)]
    assert table1.columns == ['Key', 'Command', 'Description']

    assert table1[(0, 'Key')] == 'm' # meh

    assert len(list(table1.lines)) == 25


def test_single():
    o = """
* hello
"""
    org = Org.from_string(o)

    entries = org.xpath_all('//org')

    assert len(entries) == 1

def test_table_xpath():
    o  = """
| table | a |
|-------+---|
| xxx   | 1 |
    """
    org = Org.from_string(o)

    contents = org.contents
    assert len(contents) == 3 # TODO careful about empty line handling..
    assert isinstance(contents[1], OrgTable)

    # TODO ugh... it's cause it's conflict between table as a field and table as class name...
    # ugh. how to make it consistent?..
    tentry = org.xpath("//table")

    assert isinstance(tentry, OrgTable)


def test_table_xpath_2():
    org = Org.from_string("""
#+tblname: something
| date                 | value | comment                       |
|----------------------+-------+-------------------------------|
| 14.04.17             |  11   | aaaa                          |
| May 26 2017 08:00    |  12   | what + about + pluses?        |
| May 26 09:00 - 10:00 |  13   | time is                       |

    some comment

#+BEGIN_SRC python :var fname="plot.png" :var table=something :results file
fig.savefig(fname)
return fname
#+END_SRC

#+RESULTS:
[[file:plot.png]]
""")
    tbl = org.xpath('//table')
    assert isinstance(tbl, OrgTable)


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

    res = org.with_tag('kindle', with_inherited=False)
    assert len(res) == 1

    res = org.with_tag('kindle', with_inherited=True)
    assert len(res) == 2

def test_raw():
    org = Org.from_string("""
* [2018-12-02 Sun 13:00] alala :wlog:
uu
** 7
hello
** 6
** 4""")
    note = org.children[0]
    assert note.heading == 'alala'
    assert note.get_raw(heading=False, recursive=True) == '''
uu
** 7
hello
** 6
** 4
'''.strip()
    assert note.created == datetime(year=2018, month=12, day=2, hour=13, minute=0)


# TODO ugh; it's pretty slow now... I guess I should limit the interesting attributes somehow?...

def test_broken_tags():
    org = Org.from_string("""
* [2018-07-11 Wed 21:14] for some reasong there is a newline before tags :( 
  :social:talking:

    """)
    assert len(org.firstlevel()) == 1

def test_bad_date():
    org = Org.from_string("""
* [#B] [2018-08-21 Tue 22:35] uu [1234 01234567] :hello:
""")
    res = org.with_tag('hello')
    assert len(res) == 1
    assert res[0].created == datetime(year=2018, month=8, day=21, hour=22, minute=35)


@pytest.mark.skip("not sure if this should be taken into account?")
def test_active_created():
    org = Org.from_string("""
* TODO <2017-11-29 Wed 22:24> something :taggg:
    """)
    [res] = org.with_tag('taggg')
    assert res.created == datetime(year=2017, month=11, day=29, hour=22, minute=24)


def test_1111():
    org = Org.from_string("""
* qm test http://www.quantified-mind.com/lab/take_tests/6156220345354
    """)
    for x in org.iterate():
        assert x.created is None


# TODO move that to orgparse?
def test_empty_heading():
    org = Org.from_string("""
* [2019-05-26 Sun 09:11]                                            :hello:

abacaba

** TODO database
 :PROPERTIES:
 :CREATED:  [2019-05-26 Sun 09:15]
 :END:
""")
    c = org.children[0]
    assert c.heading == ''
    assert c.tags == {'hello'}

    cc = c.children[0]
    assert cc.heading == 'database'

