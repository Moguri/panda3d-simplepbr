from setuptools import setup

__version__ = ''
#pylint: disable=exec-used
exec(open('simplepbr/version.py').read())

setup(
    version=__version__,
    keywords='panda3d',
    packages=['simplepbr'],
    python_requires='>=3.6.0',
    install_requires=[
        'panda3d>=1.10.8',
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
