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

import warnings

from hiccup import xfind, xfind_all, Hiccup
from hiccup import IfParentType as IfPType, IfType, IfName
import PyOrgMode # type: ignore


def get_logger():
    return logging.getLogger('porg')

def extract_org_datestr(s: str) -> Optional[str]:
    match = re.search(r'\[\d{4}-\d{2}-\d{2}.*?\]', s)
    if not match:
        return None
    else:
        return match.group(0)

Dateish = Union[datetime, date]

def parse_org_date(s: str) -> Dateish:
    s = s.strip().strip('[]').strip() # just in case
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
    def __init__(self, parent):
        self.parent = parent

class OrgTable(Base):
    def __init__(self, root,  parent):
        super().__init__(parent=parent)
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
    def __init__(self, root, parent):
        super().__init__(parent=parent)
        self.node = root

    @staticmethod
    def from_file(fname: str):
        base = PyOrgMode.OrgDataStructure()
        base.load_from_file(fname)
        return Org(base.root, parent=None)

    @staticmethod
    def from_string(s: str):
        base = PyOrgMode.OrgDataStructure()
        base.load_from_string(s)
        return Org(base.root, parent=None)

    @property
    def tags(self) -> Set[str]:
        return set(self.node.get_all_tags(use_tag_inheritance=True))

    @property
    def self_tags(self) -> Set[str]:
        return set(self.node.get_all_tags(use_tag_inheritance=[]))

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
                if c.name == 'PROPERTIES':
                    assert props is None
                # TODO add logbook to tests
                    props = c
            elif isinstance(c, Table):
                cont.append(c)
            elif not isinstance(c, (Scheduled,)): # TODO assert instance of OrgNode ekement...? # TODO for now just ignore drawer element
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
        for c in conts:
            if isinstance(c, str):
                res.append(c)
            elif isinstance(c, Table):
                res.append(OrgTable(c, parent=self))
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
    def raw_contents(self) -> str:
        res = ""
        for c in self.node.content:
            if isinstance(c, str):
                res += c
            else:
                res += c.output()
        return res
        #res = []
        #head = False
        #for n in self.iterate():
        #    if not head:
        #        head = True
        #    else:
        #        res.append(n.heading + '\n')
        #    res.append(n.content)
        #return ''.join(res)

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
        return [Org(c, parent=self) for c in self._content_split[1]]

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

    def with_tag(self, tag: str, with_inherited=True) -> List['Org']:
        if with_inherited:
            tt = 'tags'
        else:
            tt = 'self_tags'

        return self.xpath_all(f"//org[./{tt}/*[text()='{tag}']]")

    def xpath(self, q: str):
        r = self.xpath_all(q)
        [res] = self.xpath_all(q)
        return res

    def firstlevel(self) -> List['Org']:
        return self.xpath_all('/root/children/org')

    def xpath_all(self, q: str) -> List['Org']:
        import types

        h = Hiccup()
        for cls in (datetime, date, OrgTable):
            h.exclude(IfPType(cls))

        # TODO ignore by default?..
        h.exclude(IfType(types.GeneratorType))
        h.exclude(IfPType(Base), IfName('parent'))

        for att in [
                'parent',
                '_content_split',
        ]:
            h.exclude(IfPType(Org), IfName(att))

        for cls in [
                PyOrgMode.OrgTable.Element,
                PyOrgMode.OrgSchedule.Element,
                PyOrgMode.OrgDrawer.Element,
                PyOrgMode.OrgNode.Element,
        ]:
            h.exclude(IfType(cls))

        def set_root(x):
            x.tag = 'root'
        h.xml_hook = set_root

        h.type_name_map.maps[Org] = 'org'
        h.type_name_map.maps[OrgTable] = 'table'
        # h.primitive_factory.converters[datetime] = lambda x: x.strftime('%Y%m%d%H:%M:%S')

        return h.xfind_all(self, q)


__all__ = ['Org', 'OrgTable', 'parse_org_date']
