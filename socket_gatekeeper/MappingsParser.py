###
#    Copyright (c) 2015 Timothy Savannah <kata198@gmail.com> LGPL v2.1
#    See LICENSE for more information, or https://gnu.org/licenses/old-licenses/lgpl-2.1.txt
###

import re

COMMENT_RE = re.compile('[#].*$')
MAPPING_RE = re.compile("^(?P<password>[a-fA-F0-9]+)[ ]*[=][ ]*(?P<addr>[^:]+)[\:](?P<port>.+)$")

class ParseMappingException(ValueError):
    '''
        Exception raised by errors in parsing format or values
    '''
    pass


class MappingsParser(object):
    '''
        MappingsParser - parse a mapping string and return the mapping object. Use "getMappings" to get the mappings object needed by "Listener"

        Format should be:

        sha256sum = addr:port

        ex:

        edeaaff3f1774ad2888673770c6d64097e391bc362d7d6fb34982ddf0efd18cb = 0.0.0.0:80

    '''

    def __init__(self, contents):
        '''
            MappingsParser - Parses a mappings string. "contents" is a string of a mapping file.
        '''
        self.contents = contents

        self.cachedMapping = None

    def reset(self, contents):
        '''
            reset - Use this to reset the cached mapping and contents for this parser.
        '''
        self.contents = contents
        self.cachedMapping = None

    def getMappings(self):

        if self.cachedMapping is not None:
            return self.cachedMapping

        global COMMENT_RE
        global MAPPING_RE

        contentsSplitTmp = self.contents.split('\n')
        contentsSplit = []
        ret = {}

        for line in contentsSplitTmp:
            line = COMMENT_RE.sub('', line).replace('\t', ' ').strip()
            if not line:
                continue
            contentsSplit.append(line)

        del contentsSplitTmp

        for line in contentsSplit:
            matchObj = MAPPING_RE.match(line)
            if not matchObj:
                raise ParseMappingException('Cannot parse line: "%s". Must be in format sha256sum=addr:port ' %(line,))
            groupDict = matchObj.groupdict()

            (password, addr, port) = (groupDict['password'], groupDict['addr'], groupDict['port'])
            if password in ret:
                raise ParseMappingException('Password hash "%s" defined more than once. A password can only corropsond to a single mapping.' %(password,))

            if port.isdigit() is False:
                raise ParseMappingException('Port "%s" must be an integer.' %(port, ) )

            ret[password] = { 'addr' : addr, 'port' : port }

        self.cachedMapping = ret

        return ret
            

class MappingsFileParser(MappingsParser):
    '''
        Parse mapping data from a file.

        @see MappingsParser for more information.
    '''

    def __init__(self, filename):
        with open(filename, 'r') as f:
            contents = f.read()
        MappingsParser.__init__(self, contents)


# vim: ts=4 sw=4 expandtab
