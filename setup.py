#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup, find_packages

VERSION = __import__('coop_geo').__version__

import os
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name ='coop-geo',
    version = VERSION,
    description ='GeoDjango fields and geo widgets for django-coop',
    long_description = open('README.rst').read(),
    packages = ['coop_geo',
                'coop_geo.management',
                'coop_geo.templatetags',
                'coop_geo.management.commands',
                'coop_geo.migrations',],
    include_package_data = True,
    author = 'Etienne Loks',
    author_email = 'etienne.loks@peacefrogs.net',
    license ='BSD',
    url = "https://github.com/quinode/coop-geo/",
    download_url = "https://github.com/quinode/coop-geo/tarball/master",
    zip_safe = False,
    install_requires = ['django-floppyforms==0.4.7',
                        ],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
        'Natural Language :: English',
        'Natural Language :: French',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
)

