# -*- coding: utf-8 -*-
from pkg_resources import get_distribution, DistributionNotFound

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = __name__
    __version__ = get_distribution(dist_name).version
except DistributionNotFound:
    __version__ = 'unknown'
finally:
    del get_distribution, DistributionNotFound


from datetime import datetime, date
import logging
from itertools import groupby
from typing import List, Set, Optional, Dict, Union
import re
from lxml import etree as ET # type: ignore

import warnings

import PyOrgMode # type: ignore


def get_logger():
    return logging.getLogger('porg')

def extract_org_datestr(s: str) -> Optional[str]:
    match = re.search(r'\[\d{4}-\d{2}-\d{2}.*]', s)
    if not match:
        return None
    else:
        return match.group(0)

Dateish = Union[datetime, date]

def parse_org_date(s: str) -> Dateish:
    s = s.strip('[]').strip() # just in case
    for fmt, cl in [
            ("%Y-%m-%d %a %H:%M", datetime),
            ("%Y-%m-%d %H:%M", datetime),
            ("%Y-%m-%d %a", date),
            ("%Y-%m-%d", date),
    ]:
        try:
            res = datetime.strptime(s, fmt)
            if cl == date:
                return res.date()
            else:
                return res
        except ValueError:
            continue
    else:
        raise RuntimeError(f"Bad date string {str(s)}")

def is_crazy_date(d: Dateish) -> bool:
    YEAR = datetime.now().year
    return not (YEAR - 100 <= d.year <= YEAR + 5)

"""
actually it's more like an iterator over tree right?

TODO hmm. maybe that was an overkill and I could have just mapped full xpath expression back..
"""
class Cid:
    def __init__(self, where: str, cid: int) -> None:
        self.where = where
        self.cid = cid

    @staticmethod
    def child(cid: int):
        return Cid('child', cid)

    @staticmethod
    def content(cid: int):
        return Cid('content', cid)

    def serialise(self):
        return f'{self.where}|{self.cid}'

    @staticmethod
    def deserialise(cs):
        [where, cid] = cs.split('|')
        return Cid(where, int(cid))

    def locate(self, orgnote):
        if self.where == 'child':
            return orgnote.children[self.cid]
        elif self.where == 'content':
            return orgnote.contents[self.cid]
        else:
            raise RuntimeError(self.where)

    def __repr__(self):
        return 'Cid{' + self.where + ',' + str(self.cid) + '}'

_HACK_RE = re.compile(r'\s(?P<time>\d{3}) (AM|PM)($|\s)')

def extract_date_fuzzy(s: str) -> Optional[Dateish]:
    # TODO wonder how slow it is..
    logger = get_logger()
    try:
        import datefinder # type: ignore
    except ImportError as e:
        warnings.warn("Install datefinder for fuzzy date extraction!")
        return None

    # try to hack AM/PM dates without leading zero
    mm = _HACK_RE.search(s)
    if mm is not None:
        start = mm.span()[0] + 1
        tgroup = mm.group('time')
        s = s[:start] + '0' + s[start:]

    # could remove this after I fix the org mode tag issuell..


    dates = list(datefinder.find_dates(s))
    dates = [d for d in dates if not is_crazy_date(d)]

    if len(dates) == 0:
        return None
    if len(dates) > 1:
        logger.warning("Multiple dates extracted from %s. Choosing first.", s)
    return dates[0]

def _parse_org_table(table) -> List[Dict[str, str]]:
    # TODO with_header?
    cols = [s.strip() for s in table.content[0]]
    idx = dict(enumerate(cols))
    res = []
    for row in table.content[2:]:
        d = {}
        for i, val in enumerate(row): d[idx[i]] = val.strip()
        res.append(d)
    return res

# TODO err.. needs a better name
class Base:
    def __init__(self, cid, parent):
        self.parent = parent
        self.cid = cid

    # TODO cache it as well..?
    @property
    def _path(self) -> List[Cid]:
        if self.cid is None:
            return []
        else:
            prev = [] if self.parent == None else self.parent._path
            prev.append(self.cid)
            return prev

    @property
    def _xpath_helper(self) -> str:
        return ','.join(map(lambda c: c.serialise(), self._path))

class OrgTable(Base):
    def __init__(self, root, cid, parent):
        super().__init__(cid=cid, parent=parent)
        self.table = _parse_org_table(root)

    @property
    def columns(self) -> List[str]:
        return list(self.table[0].keys())

    @property
    def lines(self):
        for l in self.table:
            yield l

    def __getitem__(self, idx):
        (line, col) = idx # TODO not sure if it's a good idea..
        return self.table[line][col]

    def __repr__(self):
        return "OrgTable{" + repr(self.table) + "}"

class Org(Base):
    def __init__(self, root, cid, parent):
        super().__init__(cid=cid, parent=parent)
        self.node = root

    @staticmethod
    def from_file(fname: str):
        base = PyOrgMode.OrgDataStructure()
        base.load_from_file(fname)
        return Org(base.root, cid=None, parent=None)

    @staticmethod
    def from_string(s: str):
        base = PyOrgMode.OrgDataStructure()
        base.load_from_string(s)
        return Org(base.root, cid=None, parent=None)

    def _by_xpath_helper(self, helper: str) -> 'Org':
        helpers: List[str]
        if helper == '':
            helpers = []
        else:
            helpers = helper.split(',')
        cur = self
        for cidstr in helpers:
            cid = Cid.deserialise(cidstr)
            cur = cid.locate(cur)
        return cur

    @property
    def tags(self) -> Set[str]:
        return set(sorted(self.node.get_all_tags()))

    @property
    def _preheading(self):
        hh = self.node.heading
        ds = extract_org_datestr(hh)
        if ds is not None:
            hh = hh.replace(ds, '') # meh, but works?
        return (hh, ds)

    @property
    def _implicit_created(self) -> Optional[str]:
        return self._preheading[1]

    @property
    def heading(self) -> str:
        return self._preheading[0].strip()

    # TODO cache..
    @property
    def _created_str(self) -> Optional[str]:
        pp = self.properties
        if pp is not None:
            cprop = pp.get('CREATED', None)
            if cprop is not None:
                return cprop
        ic = self._implicit_created
        if ic is not None:
            return ic

        return None

    @property
    def created(self) -> Optional[Dateish]:
        cs = self._created_str
        if cs is not None:
            return parse_org_date(cs)
        return extract_date_fuzzy(self.heading)

    @property
    def _content_split(self):
        Table = PyOrgMode.OrgTable.Element
        Scheduled = PyOrgMode.OrgSchedule.Element
        Properties = PyOrgMode.OrgDrawer.Element

        cc = self.node.content
        cont = []
        elems = []
        props = None
        for i, c in enumerate(cc):
            if isinstance(c, str):
                # NOTE ok, various unparsed properties can be str... so we just concatenate them
                # assert len(elems) == 0
                cont.append(c)
            elif isinstance(c, Properties):
                assert props is None
                props = c
            elif isinstance(c, Table):
                cont.append(c)
            elif not isinstance(c, (Scheduled,)):
                elems.append(c)
        return (cont, elems, props)

    @property
    def contents(self):
        Table = PyOrgMode.OrgTable.Element

        raw_conts = self._content_split[0]


        conts = []
        for t, g in groupby(raw_conts, key=lambda c: type(c)):
            if t == type(''): # meh
                conts.append(''.join(g))
            else:
                conts.extend(g)

        res = []
        for cid, c in enumerate(conts):
            if isinstance(c, str):
                res.append(c)
            elif isinstance(c, Table):
                res.append(OrgTable(c, cid=Cid.content(cid), parent=self))
            else:
                raise RuntimeError(f"Unexpected type {type(c)}")
        return res

    @property
    def content(self) -> str:
        conts = self.contents
        return ''.join(c if isinstance(c, str) else str(c) for c in conts)

    # TODO better name?...
    @property
    def content_recursive(self) -> str:
        res = []
        head = False
        for n in self.iterate():
            if not head:
                head = True
            else:
                res.append(n.heading)
            res.append(n.content)
        return ''.join(res)

    @property
    def properties(self) -> Optional[Dict[str, str]]:
        Property = PyOrgMode.OrgDrawer.Property
        pp = self._content_split[2]
        if pp is None:
            return None
        props = {} # TODO ordered??
        for p in pp.content:
            if not isinstance(p, Property):
                # TODO can it actually happen?..
                warnings.warn("{} is not instance of Property".format(p))
                continue
            props[p.name] = p.value
        return props

    @property
    def children(self) -> List['Org']:
        # TODO scheduled/deadline things -- handled separately
        return [Org(c, Cid.child(cid), parent=self) for cid, c in enumerate(self._content_split[1])]

    @property
    def level(self):
        return self.node.level

    # None means infinite
    def iterate(self, depth=None):
        yield self
        if depth == 0:
            return
        for c in self.children:
            yield from c.iterate(None if depth is None else depth - 1)

    def __repr__(self):
        return 'Org{{{}}}'.format(self.heading)
    # TODO parent caches its tags??

    # TODO line numbers

    # TODO choose date format?
    def as_xml(self) -> ET.Element:
        ee = ET.Element('root' if self.parent is None else 'org')
        ee.set('xpath_helper', self._xpath_helper)
        he = ET.SubElement(ee, 'heading')
        he.text = self.heading
        cne = ET.SubElement(ee, 'contents')

        # TODO maybe, strings going one after another should be merged? implement a test for that..
        for c in self.contents:
            if isinstance(c, str):
                elem = ET.SubElement(cne, 'text')
                elem.text = c
            elif isinstance(c, OrgTable):
                telem = ET.SubElement(cne, 'table')
                telem.set('xpath_helper', c._xpath_helper)
            else:
                raise RuntimeError(f'Unexpected type {type(c)}')


        ce = ET.SubElement(ee, 'children')
        child_xmls = [c.as_xml() for c in self.children]
        ce.extend(child_xmls)
        return ee

    def xpath(self, q: str) -> List['Org']:
        [res] = self.xpath_all(q)
        return res

    def xpath_all(self, q: str):
        xml = self.as_xml()
        xelems = xml.xpath(q)
        return [self._by_xpath_helper(x.attrib['xpath_helper']) for x in xelems]


__all__ = ['Org', 'OrgTable', 'parse_org_date']
