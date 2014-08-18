from setuptools import setup
from pycdek import __version__

setup(
    name='pycdek',
    url='http://github.com/onrik/pycdek/',
    version=__version__,
    description='Client for CDEK API',
    author='Andrey',
    author_email='and@rey.im',
    license='MIT',
    packages=['pycdek'],
    package_data={'pycdek': [
        'pycdek/*.py',
    ]},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    install_requires=[
        'lxml',
    ],
)