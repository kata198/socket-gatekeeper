
# Based off code by Timothy Savannah (c) 2015, granted GPL exclusion to NCBI. NCBI Has full rights to modify and redistribute this code as seen fit
#  without being bound by the terms of GPL.

import multiprocessing
import os
import socket
import sys
import signal
import time
import threading

from hashlib import sha256
from Crypto.PublicKey import RSA
from Crypto import Random

from .Handler import Handler
from .utils import closeSocket



class Listener(multiprocessing.Process):


    def __init__(self, localAddr, localPort, mappings, overrideClientBufferLen=None, overrideEndpointBufferLen=None):
        '''
            localAddr - Local Address to bind
            localPort - Local port to bind
            mappings - Dictionary of sha256 password to an address and port
        '''
        multiprocessing.Process.__init__(self)
        self.localAddr = localAddr
        self.localPort = localPort

        self.mappings = mappings

        self.myWorkers = []


        self.tmpConnections = []

        self.tmpThreads = []

        self.listenSocket = None
        self.keepGoing = True

        self.overrideClientBufferLen = overrideClientBufferLen or None
        self.overrideEndpointBufferLen = overrideEndpointBufferLen or None

        self.rsaKey = None # Call _initRSA after fork

    def _initRSA(self):
        randomGenerator = Random.new().read
        self.rsaKey = RSA.generate(1024, randomGenerator)


    def cleanup(self):
        time.sleep(2) # Wait for things to kick off
        while self.keepGoing is True:
            currentWorkers = self.myWorkers[:]
            for worker in currentWorkers:
                try:
                    worker.join(.1)
                    if worker.is_alive() == False:
                        self.myWorkers.remove(worker)
                except:
                    try:
                        self.myWorkers.remove(worker)
                    except:
                        pass

            currentThreads = self.tmpThreads[:]
            for thread in currentThreads:
                try:
                    thread.join(.1)
                    if thread.is_alive() == False:
                        self.tmpThreads.remove(thread)
                except:
                    try:
                        self.tmpThreads.remove(thread)
                    except:
                        pass

            time.sleep(1.5)
        sys.stderr.write('cleanup thread is done')

    def closeWorkers(self, *args):
        sys.stdout.write("GOT SIGNAL on %s:%d\n" %(self.localAddr, self.localPort))
        self.keepGoing = False

        for tmpSocket in self.tmpConnections:
            closeSocket(tmpSocket)
        closeSocket(self.listenSocket)

        try:
            self.cleanupThread.join(3)
        except:
            pass

        if not self.myWorkers:
            sys.exit(0)

        for myWorker in self.myWorkers:
            try:
                myWorker.terminate()
                os.kill(myWorker.pid, signal.SIGTERM)
            except:
                pass

        time.sleep(1)

        remainingWorkers = []
        for myWorker in self.myWorkers:
            myWorker.join(.05)
            if myWorker.is_alive() == True:
                remainingWorkers.append(myWorker)

        if len(remainingWorkers) > 0:
            time.sleep(1)
            for myWorker in remainingWorkers:
                myWorker.join(.2)
                if myWorker.is_alive() == True:
                    try:
                        os.kill(myWorker.pid, signal.SIGKILL)
                    except:
                        pass
            time.sleep(.1)

        sys.stdout.write('Listener done\n')
        sys.exit(0)

    def applyFiltersToHandler(self, handler, shaPass, mapping):
        return

    def setApplyFiltersToHandlerFunction(self, applyFunc):
        self.applyFiltersToHandler = applyFunc


    def handleConnection(self, clientConnection, clientAddr):
        self.tmpConnections.append(clientConnection)

        clientConnection.send(self.rsaKey.publickey().exportKey())
        data = clientConnection.recv(1024).strip()
        passwordSummed = sha256(self.rsaKey.decrypt(data)).hexdigest()

        if passwordSummed not in self.mappings:
            closeSocket(clientConnection)
            self.tmpConnections.remove(clientConnection)
            return
        workerInfo = self.mappings[passwordSummed]
        worker = Handler(clientConnection, clientAddr, workerInfo['addr'], workerInfo['port'], self.overrideClientBufferLen, self.overrideEndpointBufferLen)
        self.applyFiltersToHandler(worker, passwordSummed, workerInfo)
        worker.start()
        self.tmpConnections.remove(clientConnection)
        self.myWorkers.append(worker)
        

    def run(self):
        signal.signal(signal.SIGTERM, self.closeWorkers)
        self._initRSA()

        while True:
            try:
                listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listenSocket.bind( (self.localAddr, self.localPort) )
                self.listenSocket = listenSocket
                break
            except Exception as e:
                sys.stderr.write('Failed to bind to %s:%d. "%s" Retrying in 5 seconds.\n' %(self.localAddr, self.localPort, str(e)))
                time.sleep(5)

        listenSocket.listen(5)

        cleanupThread = threading.Thread(target=self.cleanup)
        cleanupThread.start()

        try:
            while True:
                if self.keepGoing is False:
                    break
                try:
                    (clientConnection, clientAddr) = listenSocket.accept()
                    self.clientConnection = clientConnection
                except:
                    sys.stderr.write('Cannot bind to %s:%s\n' %(self.localAddr, self.localPort))
                    if self.keepGoing is True:
                        time.sleep(3)
                        continue
                    
                    raise
                # TODO: Fork thread for routing password here

                connectThread = threading.Thread(target=self.handleConnection, args=(clientConnection, clientAddr))
                connectThread.start()
                self.tmpThreads.append(connectThread)
        except Exception as e:
            sys.stderr.write('Got exception: %s, shutting down worker on %s:%d\n' %(str(e), self.localAddr, self.localPort))
            self.closeWorkers()

        sys.stderr.write('listener shutting down...\n')
        # If we got here, must have been signlaed to terminate. Stay open for a short bit to try to close children, then tank.
        time.sleep(6)
        sys.exit(0)

# vim: ts=4 sw=4 expandtab
