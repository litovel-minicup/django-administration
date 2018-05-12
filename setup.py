#!/usr/bin/env python3
# coding=utf-8

import sys
from distutils import core
from os.path import abspath, dirname

from setuptools import find_packages

__author__ = "Josef Kolář"

if sys.version_info < (3, 5):
    print('Run in python >= 3.5 please.', file=sys.stderr)
    exit(1)

base_path = abspath(dirname(__file__))


def setup():
    core.setup(
        name='litovel-minicup-administration',
        version='1.0.0',
        packages=find_packages(exclude=['*.settings', ]),
        requires=[
            'Django',
        ],
    )


if __name__ == '__main__':
    setup()
