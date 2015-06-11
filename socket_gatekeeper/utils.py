###
#    Copyright (c) 2015 Timothy Savannah <kata198@gmail.com> LGPL v2.1
#    See LICENSE for more information, or https://gnu.org/licenses/old-licenses/lgpl-2.1.txt
###

import socket


def closeSocket(openSocket):
    try:
        openSocket.shutdown(socket.SHUT_RDWR)
    except:
        pass
    try:
        openSocket.close()
    except:
        pass



# vim: ts=4 sw=4 expandtab
