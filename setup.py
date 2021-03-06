#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup
import djangomosql

VERSION = djangomosql.__version__

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


def get_install_requires():
    filename = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(filename) as f:
        return f.readlines()


def get_readme():
    with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
        return f.read()


setup(
    name='django-mosql',
    version=VERSION,
    packages=['djangomosql', 'djangomosql.db'],
    include_package_data=True,
    install_requires=get_install_requires(),
    license='BSD License',
    description='Django model integration for MoSQL.',
    long_description=get_readme(),
    url='http://github.com/uranusjr/django-mosql',
    author='Tzu-ping Chung',
    author_email='uranusjr@gmail.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
