#!/usr/bin/env python2

long_description = """
Socket Gatekeeper
=================


Socket Gatekeeper provides a means of password securing and routing arbitrary sockets. It can add security to existing services that provide no/weak authentication,
  and replace several ports to the outside world with a single point of entry.

It listens on a socket and waits for a connection. Upon connection, it sends a 1024-bit RSA public key to the client.
The client uses this public key to encrypt the password and sends it back over the wire.
That password is hashed using SHA-256 and compared against a provided mapping file. This mapping file specifies where that password
is to be routed. Example, giving password "abc" may route to some management info on one port, giving a different password "foo" may
route to an information service running somewhere else. Giving a password that is not mapped will result in a terminated connection.
There is no information to the client describing what is running where, or that this is even a gatekeeper socket (for security).


You can use Socket Gatekeeper for many tasks:

* Securing protocols that do not have any inherit security
* Only opening one port on a machine where several administrative services are running. Admins are given their own unique passwords to acccess the services they require
* Opening a port to the outside world which then routes using secure passwords to any number of internal services
* Several others!


Mapping File (configuration)
============================

The routing provided by the daemon is controlled by a mapping file.

This file is in the format:

    sha256sum=Addr:Port

Example, for a password "abc" to route to localhost port 6379, use:

    ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad = 127.0.0.1:6379

You can derive a sha256 sum with the following script:

    echo -n "your_password_here" | sha256sum | awk {'print $1'}

You may have multiple passwords lead to the same endpoint, but a single password may only lead to one endpoint.


Starting The Server (in front of other services)
================================================

Use the provided command *socket-gatekeeperd* to start a gatekeeper daemon.

Required Arguments:

    You must provide "--mappings=/path/to/file" (or "-m /path/to/file") to the mapping file.
    You must also provide "--bind=addr:port" (or "-b addr:port") example: 127.0.0.1:50001

Other Arguments:

    --client-buffer-len=X        This will use X as the number of bytes transmitted/received at one time to/from the client
    --endpoint-buffer-len=X      This will use X as the number of bytes transmitted/received at one time to/from the endpoint

    Both buffer arguments default to 4096.

    --enable-quit                This will intercept the messages "quit" and "exit" and cause them to terminate the connection.


Connecting To The Server (telnet style)
=======================================

Once you have a server up and running, you can connect to it with the provided *socket-gatekeeper-connect* program.

You specify the address and port on which to connect, and it handles the RSA portion, prompts for a password which is not echoed
to the screen, and then serves as an in-between to you and the endpoint.


    Usage: ./socket-gatekeeper-connect Addr:port

        Connects to a gatekeeper socket. This is basically the same as telnetting to the socket, except it will not echo the password
        back on the screen, so this is more secure.


Integrating Into Applications (socket style)
============================================

*socket-gatekeeperd* sits in front of your daemons to add security to any protocol. 

But you want to connect to that service using existing tools?


You should use socket_gatekeeper.GatekeeperSocket. It extends the standard python "socket" with methods that either perform the handshake with

a given password, or prompt the user and perform the handshake that way. After authentication, it behaves just as a normal socket. Thus, you can

extend any code by replacing socket with GatekeeperSocket.

For use with other languages as the client, see GatekeeperSocket for the simple implementation of the handshake. It should be easy to implement in 

other languages.



Example:
--------

    sock = GatekeeperSocket(socket.AF_INET, socket.SOCK_STREAM)

    try:

        sock.connect( (addrSplit[0], int(addrSplit[1])) )

    except socket.error:

        sys.stderr.write('Failed to connect to %s\n' %(sys.argv[1],))

        sys.exit(1)


    sock.doAuthenticationFromInput()


Dependencies
============

Depends on python 2.7 and ArgumentParser (https://pypi.python.org/pypi/argumentparser) as well as PyCrypto (https://pypi.python.org/pypi/pycrypto)


"""

from setuptools import setup

setup(name='socket-gatekeeper',
        version='1.3.1',
        packages=['socket_gatekeeper',],
        scripts=['socket-gatekeeperd', 'socket-gatekeeper-connect'],
        requires=['argumentparser', 'pycrypto'],
        install_requires=['argumentparser', 'pycrypto'],
        keywords=['socket', 'password', 'gatekeeper', 'security', 'auth', 'access', 'control', 'add', 'authenticate', 'RSA'],
        url='https://github.com/kata198/socket-gatekeeper',
        long_description=long_description,
        author='Tim Savannah',
        author_email='kata198@gmail.com',
        maintainer='Tim Savannah',
        maintainer_email='kata198@gmail.com',
        license='LGPLv2',
        description='Add authentication and enhance security to any existing service/protocol',
        classifiers=['Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2 :: Only',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Networking',
        'Topic :: Security',
    ]

)
