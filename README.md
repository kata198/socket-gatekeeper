
Socket Gatekeeper
=================


Socket Gatekeeper provides a means of password securing and routing arbitrary sockets.

It listens on a socket and waits for a connection. Upon connection, it sends a 1024-bit RSA public key to the client.
The client uses this public key to encrypt the password and sends it back over the wire.
That password is hashed using SHA-256 and compared against a provided mapping file. This mapping file specifies where that password
is to be routed. Example, giving password "abc" may route to some management info on one port, giving a different password "foo" may
route to an information service running somewhere else. Giving a password that is not mapped will result in a terminated connection.
There is no information to the client describing what is running where, or that this is even a gatekeeper socket (for security).


You can use Socket Gatekeeper for many tasks:

# Securing protocols that do not have any inherit security
# Only opening one port on a machine where several administrative services are running. Admins are given their own unique passwords to acccess the services they require
# Opening a port to the outside world which then routes using secure passwords to any number of internal services
# Several others!


Mapping File
============

The routing provided by the daemon is controlled by a mapping file.

This file is in the format:

    sha256sum=Addr:Port

Example, for a password "abc" to route to localhost port 6379, use:

    ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad = 127.0.0.1:6379

You can derive a sha256 sum with the following script:

    echo -n "your_password_here" | sha256sum | awk {'print $1'}

You may have multiple passwords lead to the same endpoint, but a single password may only lead to one endpoint.


Starting The Server
===================

Use the provided command "socket-gatekeeperd" to start a gatekeeper daemon.

Required Arguments:

    You must provide "--mappings=/path/to/file" (or "-m /path/to/file") to the mapping file.
    You must also provide "--bind=addr:port" (or "-b addr:port") example: 127.0.0.1:50001

Other Arguments:

    --client-buffer-len=X        This will use X as the number of bytes transmitted/received at one time to/from the client
    --endpoint-buffer-len=X      This will use X as the number of bytes transmitted/received at one time to/from the endpoint

    Both buffer arguments default to 4096.

    --enable-quit                This will intercept the messages "quit" and "exit" and cause them to terminate the connection.


Connecting To The Server
========================

Once you have a server up and running, you can connect to it with the provided "socket-gatekeeper-connect" program.
You specify the address and port on which to connect, and it handles the RSA portion, prompts for a password which is not echoed
to the screen, and then serves as an in-between to you and the endpoint.



Dependencies
============

Depends on python 2.7 and ArgumentParser (https://pypi.python.org/pypi/argumentparser) as well as PyCrypto (https://pypi.python.org/pypi/pycrypto)
