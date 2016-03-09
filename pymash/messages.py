#-------------------------------------------------------------------------------
#################################################################################
# The MASH web application contains the source code of all the servers
# in the "computation farm" of the MASH project (http://www.mash-project.eu),
# developed at the Idiap Research Institute (http://www.idiap.ch).
#
# Copyright (c) 2016 Idiap Research Institute, http://www.idiap.ch/
# Written by Philip Abbet (philip.abbet@idiap.ch)
#
# This file is part of the MASH web application (mash-web).
#
# The MASH web application is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# version 2 as published by the Free Software Foundation.
#
# The MASH web application is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the MASH web application. If not, see
# <http://www.gnu.org/licenses/>.
################################################################################


 Represents a message
#-------------------------------------------------------------------------------
class Message(object):

    #---------------------------------------------------------------------------
    # Constructor
    #
    # @param name           Name of the message
    # @param parameters     Parameters of the message
    #---------------------------------------------------------------------------
    def __init__(self, name, parameters=None):
        self.name = name
        self.parameters = parameters

        if self.parameters is not None:
            if len(self.parameters) == 0:
                self.parameters = None

    #---------------------------------------------------------------------------
    # Indicates if the message is the same than the provided one
    #---------------------------------------------------------------------------
    def equals(self, message):
        return (self.name == message.name) and (self.parameters == message.parameters)

    #---------------------------------------------------------------------------
    # Returns a string representation of the message
    #---------------------------------------------------------------------------
    def toString(self):
        s = self.name

        if self.parameters is None:
            return s

        for param in self.parameters:
            param = str(param)

            encoded = Message._encode(param)

            mustQuote = False
            if param != encoded:
                param = encoded
                mustQuote = True

            if mustQuote or (param.find(' ') >= 0):
                param = "'%s'" % param

            s += ' %s' % param

        return s

    #---------------------------------------------------------------------------
    # Returns a message from a string representation
    #---------------------------------------------------------------------------
    @staticmethod
    def fromString(text):
        parts = text.split(' ')

        name = parts[0]

        if len(parts) == 1:
            return Message(name)

        parameters = []
        quotedString = False

        for part in parts[1:]:
            if not(quotedString):
                if part.startswith("'"):
                    parameters.append(part[1:])
                    quotedString = True
                else:
                    decoded = Message._decode(part)

                    try:
                        parameters.append(int(decoded))
                        continue
                    except ValueError:
                        pass

                    try:
                        parameters.append(float(decoded))
                        continue
                    except ValueError:
                        pass

                    parameters.append(decoded)
            else:
                if part.endswith("'") and ((len(part) == 1) or not(part.endswith("\\'"))):
                    parameters[-1] += ' ' + part[:-1]
                    parameters[-1] = Message._decode(parameters[-1])
                    quotedString = False
                else:
                    parameters[-1] += ' ' + part

        return Message(name, parameters)

    #---------------------------------------------------------------------------
    # Encode a string
    #---------------------------------------------------------------------------
    @staticmethod
    def _encode(text):
        return text.replace("'", "\\'").replace("\n", "\\n")

    #---------------------------------------------------------------------------
    # Decode a string
    #---------------------------------------------------------------------------
    @staticmethod
    def _decode(text):
        return text.replace("\\'", "'").replace("\\n", "\n")
