#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Setup file for porg.
    Use setup.cfg to configure your project.

    This file was generated with PyScaffold 3.1.
    PyScaffold helps you to put up the scaffold of your new Python project.
    Learn more under: https://pyscaffold.org/
"""
import sys

from pkg_resources import require, VersionConflict
from setuptools import setup

try:
    require('setuptools>=38.3')
except VersionConflict:
    print("Error: version of setuptools is too old (<38.3)!")
    sys.exit(1)


if __name__ == "__main__":
    setup(
        use_pyscaffold=True,
        dependency_links=[
            # ugh. tests are broken in master... https://github.com/bjonnh/PyOrgMode/issues/47
            # TODO what's the egg thing for???
            'https://github.com/bjonnh/PyOrgMode/archive/cfd430afea3b1baad650c8bd0330474907b73f89.zip#egg=PyOrgMode-0.1',
            'git+https://github.com/karlicoss/hiccup.git#egg=hiccup-0.3',
        ],
    )
