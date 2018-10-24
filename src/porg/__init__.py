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


import re
from datetime import datetime, date
from typing import List, Set, Optional, Dict, Union

import PyOrgMode # type: ignore

def extract_org_datestr(s: str) -> Optional[str]:
    match = re.search(r'\[\d{4}-\d{2}-\d{2}.*]', s)
    if not match:
        return None
    else:
        return match.group(0)

Dateish = Union[datetime, date]

def parse_org_date(s: str) -> Dateish:
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

# def extract_date_fuzzy(s: str) -> Optional[Dateish]:
#     import datefinder # type: ignore
#     # TODO wonder how slow it is..
#     dates = list(datefinder.find_dates(s))
#     if len(dates) == 0:
#         return None
#     if len(dates) > 1:
#         raise RuntimeError
#     return dates[0]


class Org:
    def __init__(self, root, parent=None):
        self.node = root
        self.parent = parent
        # import ipdb; ipdb.set_trace()

    @staticmethod
    def from_file(fname: str):
        base = PyOrgMode.OrgDataStructure()
        base.load_from_file(fname)
        return Org(base.root)

    @staticmethod
    def from_string(s: str):
        base = PyOrgMode.OrgDataStructure()
        base.load_from_string(s)
        return Org(base.root)

    @property
    def tags(self) -> Set[str]:
        return set(sorted(self.node.get_all_tags()))

    @property
    def _preheading(self):
        hh = self.node.heading #.strip() # TODO not sure about it...
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

        # TODO also support fuzzy as in kython.org?
        return None

    @property
    def created(self) -> Optional[Dateish]:
        cs = self._created_str
        if cs is None:
            return cs
        cs = cs.strip('[]').strip() # paranoid, but just in case
        return parse_org_date(cs)

    @property
    def _content_split(self):
        Table = PyOrgMode.OrgTable.Element
        Scheduled = PyOrgMode.OrgSchedule.Element
        Properties = PyOrgMode.OrgDrawer.Element

        cc = self.node.content
        cont = ""
        elems = []
        props = None
        for i, c in enumerate(cc):
            if isinstance(c, str):
                # NOTE ok, various unparsed properties can be str... so we just concatenate them
                # assert len(elems) == 0
                cont += c
            elif isinstance(c, Properties):
                assert props is None
                props = c
            elif not isinstance(c, (Table, Scheduled)):
                elems.append(c)
        return (cont, elems, props)

    @property
    def content(self) -> str:
        return self._content_split[0]

    @property
    def properties(self) -> Optional[Dict[str, str]]:
        Property = PyOrgMode.OrgDrawer.Property
        pp = self._content_split[2]
        if pp is None:
            return None
        props = {} # TODO ordered??
        for p in pp.content:
            if not isinstance(p, Property): # eh, rare, but can happen apparently..
                continue
            props[p.name] = p.value
        return props

    # TODO parent
    @property
    def children(self) -> List['Org']:
        # Deadline = PyOrgMode.OrgD
        # TODO scheduled/deadline things -- handled separately
        return [Org(c, self) for c in self._content_split[1]]

    @property
    def level(self):
        return self.node.level

    # TODO handle table elements
    # None means infinite
    def iterate(self, depth=None):
        yield self
        if depth == 0:
            return
        for c in self.children:
            yield from c.iterate(None if depth is None else depth - 1)
        # yield from self.children

    def __repr__(self):
        return 'Org{{{}}}'.format(self.heading)
    # TODO tags??
    # TODO tags with inherited??
    # TODO parent caches its tags??

    # TODO line numbers

__all__ = ['Org']
