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


# TODO ok I need to build some sort of tree first
# tree is built on a set of documents? or for starters, single file is hopefully enough
# TODO mm, not sure. maybe I don't even need to warp anything? althouh my wrappers would def be nicer..


from typing import List, Set, Optional, Dict

import PyOrgMode # type: ignore

import sys, ipdb, traceback; exec("def info(type, value, tb):\n    traceback.print_exception(type, value, tb)\n    ipdb.pm()"); sys.excepthook = info # type: ignore

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
        return set(self.node.tags) # TODO get_all_tags??

    @property
    def heading(self) -> str:
        return self.node.heading #.strip() # TODO not sure about it...

    # TODO cache..
    @property
    def created(self) -> Optional[str]:
        pp = self.properties
        if pp is None:
            return None
        cprop = pp.get('CREATED', None)
        if cprop is None:
            return None
        return cprop.strip('[]')

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
    def iterate(self):
        # import ipdb; ipdb.set_trace() 
        yield self
        for c in self.children:
            yield from c.iterate()
        # yield from self.children

    def __repr__(self):
        return 'Org{{{}}}'.format(self.heading)
    # TODO tags??
    # TODO tags with inherited??
    # TODO parent caches its tags??


