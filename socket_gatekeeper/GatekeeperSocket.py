###
#    Copyright (c) 2015 Timothy Savannah <kata198@gmail.com> LGPL v2.1
#    See LICENSE for more information, or https://gnu.org/licenses/old-licenses/lgpl-2.1.txt
###

import getpass
import random
import socket
import threading

from Crypto.PublicKey import RSA

from .utils import closeSocket


class GatekeeperSocket(socket.socket):
    '''
        This represents a socket with the ability to authenticate to a service running behind socket-gatekeeperd.

        Call either "doAuthentication" or "doAuthenticationFromInput" after calling 'connect'. This will perform the handshake necessary to continue the connection.

        After authenticated, use like a normal socket object.
    '''


    def doAuthentication(self, password):
        '''
            doAuthentication - Performs the authentication with given password. This is not very secure, don't use plaintext passwords.
        '''
        publicKey = self.recv(4200)
        encryptor = RSA.importKey(publicKey)
        password = encryptor.encrypt(password, random.randint(1, 40))[0]

        self.send(password + "\r\n")
        
    def doAuthenticationFromInput(self):
        '''
            doAuthenticationFromInput - Prompts tty for password and then performs the gatekeeper handshake.
        '''
        publicKey = self.recv(4200)
        encryptor = RSA.importKey(publicKey)
        self.send(encryptor.encrypt(getpass.getpass(), random.randint(1, 40))[0] + "\r\n")

