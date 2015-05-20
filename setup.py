#!/usr/bin/env python2


f = open('README.md', 'r')
long_description = f.read()
f.close()


from setuptools import setup

setup(name='socket-gatekeeper',
        version='1.0',
        packages=['socket_gatekeeper',],
        scripts=['socket-gatekeeperd', 'socket-gatekeeper-connect'],
        requires=['argumentparser', 'pycrypto'],
        install_requires=['argumentparser', 'pycrypto'],
        keywords=['socket', 'password', 'gatekeeper', 'security', 'auth', 'access', 'control'],
        long_description=long_description,
        author='Tim Savannah',
        author_email='kata198@gmail.com',
        maintainer='Tim Savannah',
        maintainer_email='kata198@gmail.com',
        license='LGPLv2',
        description='A security layer for managing access to external/internal applications',
        classifiers=['Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2 :: Only',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Networking',
        'Topic :: Security',
    ]

)
