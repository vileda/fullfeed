#!/bin/env python

from setuptools import setup, find_packages
setup(
    name="fullfeed",
    version="0.1",
    packages=find_packages(),
    scripts=['fullfeed.py'],

    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=['tornado', 'beautifulsoup4', 'feedparser', 'sqlalchemy'],

    # metadata for upload to PyPI
    author="vileda",
    author_email="vileda@vileda.cc",
    description="extract full articles from rss feeds",
    license="MIT",
    keywords="rss fullfeed",
    url="https://github.com/vileda/fullfeed",   # project home page, if any

    # could also include long_description, download_url, classifiers, etc.
)
