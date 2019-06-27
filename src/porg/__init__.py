# -*- coding: utf-8 -*-
        # TODO ok, so contents returns mix or str and tables? why not..
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
from typing import List, Set, Optional, Dict, Union, NoReturn, Tuple
from pathlib import Path
import re
import warnings


import orgparse # type: ignore

# TODO add py.typed?
from hiccup import xfind, xfind_all, Hiccup
from hiccup import IfParentType as IfPType, IfType, IfName


def get_logger():
    return logging.getLogger('porg')

def extract_org_datestr(s: str) -> Optional[str]:
    match = re.search(r'\[\d{4}-\d{2}-\d{2}.*?\]', s)
    if not match:
        return None
    else:
        return match.group(0)

Dateish = Union[datetime, date]

# TODO allow specifying custom date formats
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

def _is_separator(ll: str):
    TABLE_SEP = r'\|(\-+\+)*\-+\|'
    return re.match(TABLE_SEP, ll) is not None

def _parse_org_table(lines: List[str]) -> List[Dict[str, str]]:
    before_first_sep: List[List[str]] = []
    after_first_sep: List[List[str]] = []
    cur = before_first_sep
    for ll in lines:
        if _is_separator(ll):
            cur = after_first_sep
            continue
        cells = ll.strip('|').split('|')
        cur.append(cells)

    # TODO FIXME not sure how should the column names be treated if there are multiple lines before first separator...
    cols = before_first_sep[-1] # TODO FIXME is a table required to have column names at all?
    idx = [c.strip() for c in cols]
    res = []
    for row in after_first_sep:
        d: Dict[str, str] = {}
        for i, val in enumerate(row):
            d[idx[i]] = val.strip()
        res.append(d)
    return res

# TODO err.. needs a better name
class Base:
    def __init__(self, parent):
        self.parent = parent

class OrgTable(Base):
    def __init__(self, lines: List[str],  parent):
        super().__init__(parent=parent)
        self.table = _parse_org_table(lines)

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

    @classmethod
    def from_file(cls, fname: str):
        return cls.from_string(Path(fname).read_text())

    @staticmethod
    def from_string(s: str):
        base = orgparse.loads(s)
        return Org(base, parent=None)

    @property
    def _root(self) -> 'Org': # TODO cache?
        x = self
        while not x.is_root():
            x = x.parent
        return x

    @property
    def file_settings(self) -> Dict[str, List[str]]:
        return self._root.node._special_comments

    @property
    def _filetags(self) -> Set[str]: # TODO maybe, deserves to be non private?
        ftags = self.file_settings.get('FILETAGS', [])
        res: Set[str] = set()
        for ft in ftags:
            res.update(t for t in ft.split(':') if len(t.strip()) != 0)
        return res

    # TODO not sure if empty tags should be filtered?
    @property
    def tags(self) -> Set[str]:
        return self._filetags | set(self.node.tags)


    @property
    def self_tags(self) -> Set[str]:
        if self.is_root():
            return self._filetags
        else:
            return set(self.node.shallow_tags)


    @property
    def _preheading(self):
        # TODO hmm. format='plain' could be useful as well?? not sure where can I sue it here..
        # TODO orparse got self.node._timestamps, no good way of stripping it off from heading...
        hh = '' if self.is_root() else self.node.get_heading(format='raw')
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

    def is_root(self) -> bool:
        root = self.node.is_root()
        no_parent = self.parent is None
        assert root == no_parent # just in case during the transition period
        return root

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

    def _created_impl(self) -> Optional[Dateish]:
        cs = self._created_str
        if cs is not None:
            return parse_org_date(cs)
        return None

    def _throw(self, e: Exception) -> NoReturn:
        raise RuntimeError(f'Processing {self.node.heading} failed') from e

    @property
    def created(self) -> Optional[Dateish]:
        try:
            return self._created_impl()
        except Exception as e:
            self._throw(e)

    # TODO should be private?
    @property
    def contents(self) -> List[Union[str, OrgTable]]:
        TABLE_ROW = r'\s*(?P<cells>\|(.+\|)+)s*$'
        if self.is_root():
            lines = self.node._lines
        else:
            lines = self.node._body_lines

        items = []
        for line in lines:
            m = re.match(TABLE_ROW, line)
            if m is not None:
                items.append(m)
            else:
                items.append(line)

        res: List[Union[str, OrgTable]] = []
        for t, g in groupby(items, key=lambda c: type(c)):
            if t == type(''): # meh:
                res.extend(g) # type: ignore
            else: # should be table cells?
                rows = [m.group('cells') for m in g]
                res.append(OrgTable(rows, parent=self))
        return res

    @property
    def body(self) -> str:
        return '\n'.join(self.node._lines) if self.is_root() else self.node.get_body(format='raw')


    # TODO not a great function... semantics is pretty confusing
    @property
    def content(self) -> str:
        warnings.warn('Please use body instead', DeprecationWarning)
        return ''.join(c if isinstance(c, str) else str(c) for c in self.contents)


    @property
    def content_recursive(self) -> str:
        warnings.warn('Please use get_raw(recursive=True) instead', DeprecationWarning)
        return self.get_raw(heading=False, recursive=True)


    def _get_raw(self, heading: bool, recursive: bool) -> List[str]:
        lines: List[str] = []
        if self.is_root():
            assert not heading, "Including heading doesn't make sense for root node"
            lines.extend(self.node._lines)
        else:
            lines.extend(self.node._lines if heading else self.node._body_lines)
        if recursive:
            for c in self.children:
                lines.extend(c._get_raw(heading=True, recursive=True))
        return lines

    # TODO hmm orparse extracts some of the timestamps...
    def get_raw(self, heading=False, recursive=False) -> str:
        return '\n'.join(self._get_raw(heading=heading, recursive=recursive))

    @property
    def properties(self) -> Dict[str, str]:
        if self.is_root():
            # TODO ugh. would be convenient to have filetags as properties, but they are multivalues which breaks the return type :(
            return {}
        else:
            return self.node.properties

    @property
    def children(self) -> List['Org']:
        return [Org(c, parent=self) for c in self.node.children]

    @property
    def level(self):
        return self.node.level

    # None means infinite
    def iterate(self, depth=None):
        if not isinstance(self.node, orgparse.node.OrgRootNode):
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
                '_root',
                'content',
                'content_recursive',
        ]:
            h.exclude(IfPType(Org), IfName(att))

        for cls in [
                orgparse.node.OrgBaseNode,
                orgparse.node.OrgNode,
                orgparse.node.OrgRootNode,
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
