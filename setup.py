#!/usr/bin/env python
import subprocess as sp
from pathlib import Path

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = sp.run(
    'python publish/version.py', check=True, shell=True, stdout=sp.PIPE, stderr=sp.PIPE, encoding='utf8'
).stdout


def read(fname):
    try:
        return (Path(__file__).parent / fname).read_text()
    except (IOError, OSError, FileNotFoundError):
        return ''


setup(
    name='publish',
    version=version,
    description='tool to publish file from declarative settings',
    license='LICENSE',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    author='Mark Muetzelfeldt',
    author_email='mark.muetzelfeldt@reading.ac.uk',
    maintainer='Mark Muetzelfeldt',
    maintainer_email='mark.muetzelfeldt@reading.ac.uk',
    url='https://github.com/markmuetz/publish',
    project_urls={
        'Documentation': 'https://markmuetz.github.io/publish',
        'Bug Tracker': 'https://github.com/markmuetz/publish/issues',
    },
    packages=[
        'publish',
    ],
    python_requires='>=3.10',
    install_requires=[
        'pydantic',
    ],
    entry_points={'console_scripts': ['publish=publish.publish:main']},
    classifiers=[
        'Environment :: Console',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.9',
        'Development Status :: 5 - Alpha',
    ],
)
