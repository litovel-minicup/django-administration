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
        name='litovel-minicup-model',
        version='1.0.0',
        url='https://github.com/litovel-minicup/model',
        description='Core package with Litovel MINICUP models in Django.',
        author='Josef Kolář',
        author_email='thejoeejoee@gmail.com',
        packages=find_packages(),
        install_requires=[
            'Django',
            'mysqlclient',
            'django-extensions',
        ],
        entry_points=dict(
            console_scripts=[
                'litovel-minicup-model-manage=minicup_model.manage:manage',
            ]
        )
    )


if __name__ == '__main__':
    setup()
