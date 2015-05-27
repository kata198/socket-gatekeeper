
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



CHILD_JOIN_SECONDS = .1

class Listener(multiprocessing.Process):
    '''
        Listener - The process which listens on the incoming port for connections, verifies their authentication,
            and creates the router (Handler) for interaction with the destination.
    '''


    def __init__(self, localAddr, localPort, mappings, overrideClientBufferLen=None, overrideEndpointBufferLen=None):
        '''
            localAddr - Local Address to bind
            localPort - Local port to bind
            mappings - Dictionary of sha256 password to an address and port

            overrideClientBufferLen - Bytes - Provide an integer to override the buffer size used in transactions to/from the client (incoming connection)
            overrideEndpointBufferLen - Bytes - Provide an integer to override the buffer size used in transactions to/from the endpoint (destination)
        '''
        multiprocessing.Process.__init__(self)
        self.localAddr = localAddr
        self.localPort = localPort

        self.mappings = mappings

        self.myWorkers = []


        self.tmpConnections = []

        self.tmpThreads = []
        self.cleanupThread = None

        self.listenSocket = None
        self.keepGoing = True

        self.overrideClientBufferLen = overrideClientBufferLen or None
        self.overrideEndpointBufferLen = overrideEndpointBufferLen or None

        self.rsaKey = None # Call _initRSA after fork

    def _initRSA(self):
        '''
            _initRSA - Init the RSA generator. This must be called AFTER the fork.
        '''
        randomGenerator = Random.new().read
        self.rsaKey = RSA.generate(1024, randomGenerator)


    def cleanup(self):
        '''
            cleanup - This is run in the context of a thread and runs through the subprocesses and threads
                used by this class, joining them and removing from the worker list.
        '''

        time.sleep(2) # Wait for things to kick off
        while self.keepGoing is True:
            currentWorkers = self.myWorkers[:]
            for worker in currentWorkers:
                try:
                    worker.join(CHILD_JOIN_SECONDS)
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
                    thread.join(CHILD_JOIN_SECONDS)
                    if thread.is_alive() == False:
                        self.tmpThreads.remove(thread)
                except:
                    try:
                        self.tmpThreads.remove(thread)
                    except:
                        pass

            if self.keepGoing is True:
                time.sleep(2)

    def closeWorkers(self, *args):
        '''
            closeWorkers - the signal handler used to terminate and cleanup the workings and subprocesses/threads of this class.
        '''

        sys.stderr.write("Listener got signal on %s:%d\n" %(self.localAddr, self.localPort))

        # Set this flag which terminates the subthread loops
        self.keepGoing = False

        # Stop listening on incoming
        closeSocket(self.listenSocket)

        # Close any incoming connections
        for tmpSocket in self.tmpConnections:
            closeSocket(tmpSocket)

        
        # Wait for the cleanup thread to finish nicely
        try:
            self.cleanupThread.join(3 + (CHILD_JOIN_SECONDS * len(self.myWorkers)) + (CHILD_JOIN_SECONDS * len(self.tmpThreads)) )
        except:
            pass

        # If everything went clean, just exit
        if not self.myWorkers:
            sys.exit(0)

        # Force termination
        for myWorker in self.myWorkers:
            try:
                myWorker.terminate()
            except:
                pass
            try:
                os.kill(myWorker.pid, signal.SIGTERM)
            except:
                pass

        time.sleep(1.5)

        # Try to join workers, keep track of which didn't die
        remainingWorkers = []
        for myWorker in self.myWorkers:
            myWorker.join(CHILD_JOIN_SECONDS / 2)
            if myWorker.is_alive() == True:
                remainingWorkers.append(myWorker)

        if len(remainingWorkers) > 0:
            time.sleep(1)
            # Force kill all remaining workers
            for myWorker in remainingWorkers:
                myWorker.join(CHILD_JOIN_SECONDS * 2)
                if myWorker.is_alive() == True:
                    try:
                        os.kill(myWorker.pid, signal.SIGKILL)
                    except:
                        pass
            time.sleep(CHILD_JOIN_SECONDS)

        sys.exit(0)



    def handleConnection(self, clientConnection, clientAddr):
        '''
            handleConnection - Handles an incoming connection. Checks auth and starts a Handler process.

            @param clientConnection - Socket
            @param clientAddr - Address
        '''

        # First, send our public key for them to encrypt password
        clientConnection.send(self.rsaKey.publickey().exportKey())

        # Accept up to 4K of encrypted data and don't use an intermediate variable before decrpying and sha256 summing
        passwordSummed = sha256(self.rsaKey.decrypt(clientConnection.recv(4096).strip())).hexdigest()


        if passwordSummed not in self.mappings:
            # No match, terminate connection
            closeSocket(clientConnection)
            self.tmpConnections.remove(clientConnection)
            return

        # Gather the endpoint information
        workerInfo = self.mappings[passwordSummed]

        # Create the worker
        worker = Handler(clientConnection, clientAddr, workerInfo['addr'], workerInfo['port'], self.overrideClientBufferLen, self.overrideEndpointBufferLen)

        # Apply any filters to worker object
        self.applyFiltersToHandler(worker, passwordSummed, workerInfo)

        # Start worker, and update accounting.
        worker.start()
        self.tmpConnections.remove(clientConnection)
        self.myWorkers.append(worker)
        

    def run(self):
        '''
            run - post-fork execution of Listener. This is the workhorse.
        '''

        # Add handler for shutting down
        signal.signal(signal.SIGTERM, self.closeWorkers)

        # Init RSA engine
        self._initRSA()

        # Check and abort if keepGoing switches to False here, incase we are terminated while failing to bind to a socket.
        while self.keepGoing is True:
            # Try to bind to socket, looping until we get in or terminate
            try:
                self.listenSocket = listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listenSocket.bind( (self.localAddr, self.localPort) )
                break
            except Exception as e:
                if self.keepGoing is True:
                    sys.stderr.write('Failed to bind to %s:%d. "%s" Retrying in 5 seconds.\n' %(self.localAddr, self.localPort, str(e)))
                    time.sleep(5)
                else:
                    closeSocket(self.listenSocket)
                    sys.exit(0)
                    return

        listenSocket.listen(5)

        # Create and kick off the cleanup thread. This thread will start 2 seconds from now, and join/cleanup connections child processes and threads
        self.cleanupThread = cleanupThread = threading.Thread(target=self.cleanup)
        cleanupThread.start()

        # Loop until we are told to stop
        try:
            while self.keepGoing is True:
                try:
                    (clientConnection, clientAddr) = listenSocket.accept()
                    self.clientConnection = clientConnection
                except:
                    if self.keepGoing is True:
                        sys.stderr.write('Cannot bind to %s:%s\n' %(self.localAddr, self.localPort))
                        time.sleep(.1) # Something happened, wait a bit but only if we are to continue
                        continue
                    else:
                        # Otherwise we are shutting down and this is expected
                        raise

                # Keep accounting on this connection incase we have to shut down
                self.tmpConnections.append(self.clientConnection)

                # Pass off the connecting and validation to a thread
                connectThread = threading.Thread(target=self.handleConnection, args=(clientConnection, clientAddr))
                connectThread.start()

                # Keep accounting on connect thread. This will be removed from the list at the end of handleConnection
                self.tmpThreads.append(connectThread)
        except Exception as e:
            sys.stderr.write('Got exception: %s, shutting down worker on %s:%d\n' %(str(e), self.localAddr, self.localPort))
            self.closeWorkers()

        sys.exit(0)


    def applyFiltersToHandler(self, handler, shaPass, mapping):
        '''
            applyFiltersToHandler - callback function used to apply filters to the handler. 
                The connector should set this
        '''
        return

    def setApplyFiltersToHandlerFunction(self, applyFunc):
        '''
            setApplyFiltersToHandlerFunction - Sets the callback function which will apply filters to the handler.
            
            @see applyFiltersToHandler
        '''
        self.applyFiltersToHandler = applyFunc

# vim: ts=4 sw=4 expandtab
