from setuptools import setup, find_packages
from codecs import open
from os import path
import os

here = path.abspath(path.dirname(__file__))

with open(os.path.join(here, 'release_tools', 'VERSION')) as version_file:
    version = version_file.read().strip()

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='release-tools',
    version=version,
    description='Python tools for release management',
    long_description=long_description,
    url='https://github.com/withrocks/release-tools',
    author='withrocks',

    package_data={'': ['*.j2']},
    include_package_data=True,

    license='MIT',
    classifiers=[
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='development deployment release',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['requests[security]', 'click', 'pyyaml', 'python-dateutil', 'jinja2'],

    # $ pip install -e .[dev,test]
    extras_require={
        'dev': [],
        'test': [],
    },

    entry_points={
        'console_scripts': [
            'release-tools=release_tools.cli:cli_main',
        ],
    },
)

