###
#    Copyright (c) 2015 Timothy Savannah <kata198@gmail.com> LGPL v2.1
#    See LICENSE for more information, or https://gnu.org/licenses/old-licenses/lgpl-2.1.txt
###
import multiprocessing
import select
import signal
import socket
import sys
import traceback

from .utils import closeSocket


DEFAULT_CLIENT_BUFFER_LEN = 4096
DEFAULT_ENDPOINT_BUFFER_LEN = 4096


class HandlerStop(Exception):
    ''' 
        HandlerStop - Raise this exception to indicate that the handler should close the connection and stop processing.
    '''
    pass


def handlerFilterQuit(contents):
    '''
        handlerFilterQuit - A filter that can be added to a handler which intercepts "quit" and "exit" as the contents of a line,
            and terminates connection.
    '''
    if len(contents) > 10: # Performance 
        return None
    stripped = contents.strip().lower()
    if stripped in ('quit', 'exit'):
        raise HandlerStop

    return None

def handlerFilterDos2Unix(contents):
    '''
        handlerFilterDos2Unix - A filter that can be added to a handler which strips carriage returns.
    '''
    origLen = len(contents)
    contents = contents.replace('\r', '')
    if len(contents) != origLen:
        return contents
    return None
    

class Handler(multiprocessing.Process):
    '''
        Handler -- represents the handler who handles the in-between of data.
    '''

    def __init__(self, clientSocket, clientAddr, endpointAddr, endpointPort, clientBufferLen=DEFAULT_CLIENT_BUFFER_LEN, endpointBufferLen=DEFAULT_ENDPOINT_BUFFER_LEN):
        multiprocessing.Process.__init__(self)

        self.clientSocket = clientSocket
        self.clientAddr = clientAddr
        self.endpointAddr = endpointAddr
        self.endpointPort = int(endpointPort)

        self.endpointSocket = None

        self.clientBufferLen = clientBufferLen or DEFAULT_CLIENT_BUFFER_LEN
        self.endpointBufferLen = endpointBufferLen or DEFAULT_ENDPOINT_BUFFER_LEN


        self.fromClientFilters = []


    def addIncomingFilter(self, filterFunc):
        '''
            addIncomingFilter - Add a filter which will be applied to data coming from the client. Use this to restrict usage, e.x. preventing "CONFIG" commands from going to redis.

            @param filterFunc - A function which takes an argument of the data from the client prior to going to the endpoint. This function should return "None" to take no action,
              or any string that is returned will replace the data sent to the client. This is chained, so if the first filter returns data, that will be passed to the second and so on.
              Your function may raise "HandlerStop" to close the connection between the client and endpoint (e.x. for a "Quit" command.) See examples "handlerFilterQuit" and "handlerFilterDos2Unix"
        '''
        self.fromClientFilters.append(filterFunc)

    def _runIncomingFilters(self, contents):
        for filter in self.fromClientFilters:
            newContents = filter(contents)
            if newContents is not None:
                contents = newContents
        return contents


    def _closeConnectionsAndExit(self, *args, **kwargs):
        closeSocket(self.clientSocket)
        closeSocket(self.endpointSocket)
        sys.exit(0)

    def run(self):

        signal.signal(signal.SIGTERM, self._closeConnectionsAndExit)
        signal.signal(signal.SIGINT, self._closeConnectionsAndExit)

        clientSocket = self.clientSocket

        try:
            endpointSocket = self.endpointSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            endpointSocket.connect( (self.endpointAddr, self.endpointPort) )
        except:
            self.clientSocket.send('Error: unable to connect to endpoint.\n')
            self._closeConnectionsAndExit()
            return

        clientBufferLen = self.clientBufferLen
        endpointBufferLen = self.endpointBufferLen

        dataToClient = ''
        dataFromClient = ''
        while True:
            waitingToWrite = []

            if dataToClient:
                waitingToWrite.append(clientSocket)
            if dataFromClient:
                waitingToWrite.append(endpointSocket)


            (hasDataForRead, readyForWrite, hasError) = select.select( [clientSocket, endpointSocket], waitingToWrite, [clientSocket, endpointSocket], .2)

            if hasError:
                break

            # TODO: Possibly loop on reading here until the socket is empty with select. May work better with filters.
            #   For now, stick with what has been extensively tested.
            if clientSocket in hasDataForRead:
                nextData = clientSocket.recv(clientBufferLen)
                if not nextData:
                    break
                try:
                    nextData = self._runIncomingFilters(nextData)
                except HandlerStop:
                    self._closeConnectionsAndExit()
                    return
                except Exception as e:
                    sys.stderr.write('Exception filtering client data: %s\n' %(str(e,)))
                    sys.stderr.write(traceback.format_exc(sys.exc_info()) + '\n')

                dataFromClient += nextData

            if endpointSocket in hasDataForRead:
                nextData = endpointSocket.recv(endpointBufferLen)
                if not nextData:
                    break
                dataToClient += nextData

            if endpointSocket in readyForWrite:
                while dataFromClient:
                    endpointSocket.send(dataFromClient[:endpointBufferLen])
                    dataFromClient = dataFromClient[endpointBufferLen:]

            if clientSocket in readyForWrite:
                while dataToClient:
                    clientSocket.send(dataToClient[:clientBufferLen])
                    dataToClient = dataToClient[clientBufferLen:]


        self._closeConnectionsAndExit()

# vim: ts=4 sw=4 expandtab
