import os
from setuptools import setup

# variables used in buildout
here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()

requires = [
    'pytest-runner',
    'dcicutils',
    'biopython',
    'GEOparse',
    'xlrd',
    'xlutils'
]

tests_require = [
    'pytest',
    'pytest-mock',
    'pytest-cov',
]

setup(
    name='dcicwrangling',
    version=open(
        "scripts/_version.py").readlines()[-1].split()[-1].strip("\"'"),
    description='4DN-DCIC Scripts for wrangling metadata and data.',
    long_description=README,
    packages=['scripts', 'functions'],
    include_package_data=True,
    zip_safe=False,
    author='4DN-DCIC',
    author_email='support@4dnucleome.org',
    license='MIT',
    install_requires=requires,
    setup_requires=requires,
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
    },
)
