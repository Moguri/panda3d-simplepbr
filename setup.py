from setuptools import setup

__version__ = ''
#pylint: disable=exec-used
exec(open('simplepbr/version.py').read())

setup(
    version=__version__,
    keywords='panda3d',
    packages=['simplepbr'],
    install_requires=[
        'panda3d',
    ],
    setup_requires=[
        'pytest-runner'
    ],
    tests_require=[
        'pytest',
        'pylint==2.4.*',
        'pytest-pylint',
    ],
)
