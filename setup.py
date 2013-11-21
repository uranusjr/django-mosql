#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup
import djangomosql

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()
VERSION = djangomosql.__version__

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-mosql',
    version=VERSION,
    packages=['djangomosql'],
    include_package_data=True,
    install_requires=['django>=1.4', 'mosql>=0.6'],
    license='BSD License',
    description='Django model integration for MoSQL.',
    long_description=README,
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
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
