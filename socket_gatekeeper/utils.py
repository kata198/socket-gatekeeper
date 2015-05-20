
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
