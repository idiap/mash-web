################################################################################
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


from pymash.server import ServerListener
from pymash.messages import Message
import tarfile
import os


class MockEchoListener(ServerListener):

    def handleCommand(self, command):
        self.sendResponse(command)
        return ServerListener.ACTION_NONE



class MockCompilationServerListener(ServerListener):

    FAIL_CONDITION = None

    def handleCommand(self, command):

        if command.name == 'INFO':
            self.sendResponse(Message('TYPE', ['CompilationServer']))
            self.sendResponse(Message('PROTOCOL', ['1.0']))

        elif command.name == 'DONE':
            self.sendResponse('GOODBYE')
            return ServerListener.ACTION_CLOSE_CONNECTION

        elif command.name == 'LOGS':
            self.sendResponse('END_LOGS')

        elif command.name == 'STATUS':
            if MockCompilationServerListener.FAIL_CONDITION != command.name:
                self.sendResponse(Message('READY'))
            else:
                self.sendResponse(Message('BUSY'))

        elif command.name == 'USE_HEURISTICS_REPOSITORY':
            if MockCompilationServerListener.FAIL_CONDITION != command.name:
                self.sendResponse(Message('OK'))
            else:
                self.sendResponse(Message('ERROR', ['Because the test said so!']))

        elif command.name == 'CHECK_HEURISTIC':
            if MockCompilationServerListener.FAIL_CONDITION == 'COMPILATION__ERROR':
                self.sendResponse(Message('ERROR', ['Because the test said so!']))
            elif MockCompilationServerListener.FAIL_CONDITION == 'COMPILATION__COMPILATION_ERROR':
                self.sendResponse(Message('COMPILATION_ERROR', ['Because the test said so!']))
            elif MockCompilationServerListener.FAIL_CONDITION == 'COMPILATION__UNKNOWN':
                self.sendResponse(Message('UNKNOWN_RESPONSE', ['Because the test said so!']))
            else:
                self.sendResponse(Message('COMPILATION_OK'))

                if MockCompilationServerListener.FAIL_CONDITION == 'ANALYSIS__ANALYZE_ERROR':
                    self.sendResponse(Message('ANALYZE_ERROR', ['Because the test said so!']))
                elif MockCompilationServerListener.FAIL_CONDITION == 'ANALYSIS__UNKNOWN':
                    self.sendResponse(Message('UNKNOWN_RESPONSE', ['Because the test said so!']))
                else:
                    self.sendResponse(Message('ANALYZE_OK'))

                    if MockCompilationServerListener.FAIL_CONDITION == 'TEST__TEST_ERROR':
                        self.sendResponse(Message('TEST_ERROR', ['Because the test said so!']))
                        self.sendResponse(Message('CONTEXT', ['Somewhere']))
                    elif MockCompilationServerListener.FAIL_CONDITION == 'TEST__HEURISTIC_CRASH':
                        self.sendResponse(Message('HEURISTIC_CRASH'))
                        self.sendResponse(Message('CONTEXT', ['Somewhere']))
                        self.sendResponse(Message('STACKTRACE', ['Stacktrace']))
                    elif MockCompilationServerListener.FAIL_CONDITION == 'TEST__HEURISTIC_TIMEOUT':
                        self.sendResponse(Message('HEURISTIC_TIMEOUT'))
                        self.sendResponse(Message('CONTEXT', ['Somewhere']))
                    elif MockCompilationServerListener.FAIL_CONDITION == 'TEST__UNKNOWN':
                        self.sendResponse(Message('UNKNOWN_RESPONSE', ['Because the test said so!']))
                    else:
                        self.sendResponse(Message('TEST_OK'))
        
        else:
            self.sendResponse(Message('UNKNOWN_COMMAND', [command.name]))

        return ServerListener.ACTION_NONE


class MockExperimentServerListener(ServerListener):

    FAIL_CONDITION          = None
    ERROR_REPORT            = None
    ERROR_REPORT_PARAMETERS = None
    ERROR_REPORT_CONTEXT    = None
    ERROR_REPORT_STACKTRACE = None
    LAST_COMMAND            = None


    def __init__(self, socket, channel):
        super(MockExperimentServerListener, self).__init__(socket, channel)
        self.goalplanning = False
    

    def handleCommand(self, command):

        if command.name not in ['DONE', 'LOGS', 'REPORT_ERRORS']:
            MockExperimentServerListener.LAST_COMMAND = command

        if command.name == 'INFO':
            self.sendResponse(Message('TYPE', ['ExperimentServer']))
            self.sendResponse(Message('PROTOCOL', ['1.7']))

        elif command.name == 'DONE':
            self.sendResponse('GOODBYE')
            return ServerListener.ACTION_CLOSE_CONNECTION

        elif command.name == 'LOGS':
            self.sendResponse('END_LOGS')

        elif command.name == 'STATUS':
            if MockExperimentServerListener.FAIL_CONDITION != command.name:
                self.sendResponse(Message('READY'))
            else:
                self.sendResponse(Message('BUSY'))

        elif (command.name == 'SET_EXPERIMENT_TYPE'):
            self.goalplanning = (command.parameters[0] == 'GoalPlanning')

            if MockExperimentServerListener.FAIL_CONDITION != command.name:
                self.sendResponse(Message('OK'))
            else:
                self.sendResponse(Message('ERROR', ['Because the test said so!']))

        elif (command.name == 'USE_APPLICATION_SERVER') or \
             (command.name == 'USE_GLOBAL_SEED') or \
             (command.name == 'BEGIN_EXPERIMENT_SETUP') or \
             (command.name == 'DATABASE_NAME') or \
             (command.name == 'GOAL_NAME') or \
             (command.name == 'ENVIRONMENT_NAME') or \
             (command.name == 'END_EXPERIMENT_SETUP') or \
             (command.name == 'USE_INSTRUMENT') or \
             (command.name == 'BEGIN_INSTRUMENT_SETUP') or \
             (command.name == 'INSTRUMENT_TEST') or \
             (command.name == 'END_INSTRUMENT_SETUP') or \
             (command.name == 'USE_PREDICTOR') or \
             (command.name == 'BEGIN_PREDICTOR_SETUP') or \
             (command.name == 'PREDICTOR_TEST') or \
             (command.name == 'END_PREDICTOR_SETUP') or \
             (command.name == 'USE_HEURISTICS_REPOSITORY') or \
             (command.name == 'USE_HEURISTIC') or \
             (command.name == 'RESET'):
            if MockExperimentServerListener.FAIL_CONDITION != command.name:
                self.sendResponse(Message('OK'))
            else:
                self.sendResponse(Message('ERROR', ['Because the test said so!']))

        elif (command.name == 'USE_PREDICTOR_MODEL') or \
             (command.name == 'USE_PREDICTOR_INTERNAL_DATA'):
            
            size = command.parameters[0]
            max_size = 10 * 1024
            while size > 0:
                nb = min(size, max_size)
                data = self.waitData(nb)
                size -= nb
            
            if MockExperimentServerListener.FAIL_CONDITION != command.name:
                self.sendResponse(Message('OK'))
            else:
                self.sendResponse(Message('ERROR', ['Because the test said so!']))

        elif (command.name == 'TRAIN_PREDICTOR'):
            if MockExperimentServerListener.FAIL_CONDITION != command.name:
                self.sendResponse(Message('NOTIFICATION', ['notification1', 1]))
                self.sendResponse(Message('NOTIFICATION', ['notification1', 2]))
                if self.goalplanning:
                    self.sendResponse(Message('TRAIN_RESULT', ['GOAL_REACHED']))
                else:
                    self.sendResponse(Message('TRAIN_ERROR', [0.5]))
            else:
                self.sendResponse(Message('ERROR', ['Because the test said so!']))
            
        elif (command.name == 'TEST_PREDICTOR'):
            if MockExperimentServerListener.FAIL_CONDITION != command.name:
                self.sendResponse(Message('NOTIFICATION', ['notification2', 10]))
                self.sendResponse(Message('NOTIFICATION', ['notification2', 20]))
                if self.goalplanning:
                    self.sendResponse(Message('TEST_ROUND', [0]))
                    self.sendResponse(Message('RESULT', ['GOAL_REACHED']))
                    self.sendResponse(Message('SCORE', [0]))
                    self.sendResponse(Message('NB_ACTIONS_DONE', [247]))
                    self.sendResponse(Message('TEST_ROUND_END'))
                    
                    self.sendResponse(Message('TEST_ROUND', [1]))
                    self.sendResponse(Message('RESULT', ['NONE']))
                    self.sendResponse(Message('SCORE', [-2]))
                    self.sendResponse(Message('NB_ACTIONS_DONE', [289]))
                    self.sendResponse(Message('NB_MIMICKING_ERRORS', [186]))
                    self.sendResponse(Message('TEST_ROUND_END'))

                    self.sendResponse(Message('TEST_ROUND', [2]))
                    self.sendResponse(Message('RESULT', ['TASK_FAILED']))
                    self.sendResponse(Message('SCORE', [-4]))
                    self.sendResponse(Message('NB_ACTIONS_DONE', [283]))
                    self.sendResponse(Message('NB_MIMICKING_ERRORS', [146]))
                    self.sendResponse(Message('NB_NOT_RECOMMENDED_ACTIONS', [106]))
                    self.sendResponse(Message('TEST_ROUND_END'))

                    self.sendResponse(Message('TEST_SUMMARY'))
                    self.sendResponse(Message('NB_GOALS_REACHED', [10]))
                    self.sendResponse(Message('NB_TASKS_FAILED', [4]))
                    self.sendResponse(Message('NB_ACTIONS_DONE', [536]))
                    self.sendResponse(Message('NB_MIMICKING_ERRORS', [460]))
                    self.sendResponse(Message('NB_NOT_RECOMMENDED_ACTIONS', [234]))
                    self.sendResponse(Message('TEST_SUMMARY_END'))

                else:
                    self.sendResponse(Message('TEST_ERROR', [0.6]))
            else:
                self.sendResponse(Message('ERROR', ['Because the test said so!']))

        elif (command.name == 'REPORT_DATA'):
            if MockExperimentServerListener.FAIL_CONDITION != command.name:
                outFile = open('predictor.model', 'w')
                outFile.write('HEURISTICS\nuser1/heuristic1 1000\nuser2/heuristic2 2000\nEND_HEURISTICS\n')
                outFile.close()
                
                tar = tarfile.open('temp.tar.gz', 'w:gz')
                tar.add('predictor.model')
                tar.close()
                
                inFile = open('temp.tar.gz', 'rb')
                content = inFile.read()
                inFile.close()
                
                os.remove('temp.tar.gz')
                os.remove('predictor.model')

                self.sendResponse(Message('DATA', [ len(content) ]))
                self.sendData(content)
            else:
                self.sendResponse(Message('ERROR', ['Because the test said so!']))

        elif (command.name == 'REPORT_ERRORS'):
            if MockExperimentServerListener.ERROR_REPORT is not None:
                self.sendResponse(Message(MockExperimentServerListener.ERROR_REPORT,
                                          MockExperimentServerListener.ERROR_REPORT_PARAMETERS))

                if MockExperimentServerListener.ERROR_REPORT_CONTEXT is not None:
                    self.sendResponse(Message('CONTEXT', [MockExperimentServerListener.ERROR_REPORT_CONTEXT]))

                    if MockExperimentServerListener.ERROR_REPORT_STACKTRACE is not None:
                        self.sendResponse(Message('STACKTRACE', [MockExperimentServerListener.ERROR_REPORT_STACKTRACE]))
                
                MockExperimentServerListener.FAIL_CONDITION = None
            else:
                self.sendResponse(Message('NO_ERROR'))

        else:
            self.sendResponse(Message('UNKNOWN_COMMAND', [command.name]))

        return ServerListener.ACTION_NONE


class MockImageServerListener(ServerListener):

    def handleCommand(self, command):

        if command.name == 'INFO':
            self.sendResponse(Message('TYPE', ['ApplicationServer']))
            self.sendResponse(Message('SUBTYPE', ['Images']))
            self.sendResponse(Message('PROTOCOL', ['1.2']))

        elif command.name == 'DONE':
            self.sendResponse('GOODBYE')
            return ServerListener.ACTION_CLOSE_CONNECTION

        elif command.name == 'STATUS':
            self.sendResponse(Message('READY'))

        else:
            self.sendResponse(Message('UNKNOWN_COMMAND', [command.name]))

        return ServerListener.ACTION_NONE


class MockInteractiveServerListener(ServerListener):

    def handleCommand(self, command):

        if command.name == 'INFO':
            self.sendResponse(Message('TYPE', ['ApplicationServer']))
            self.sendResponse(Message('SUBTYPE', ['Interactive']))
            self.sendResponse(Message('PROTOCOL', ['1.2']))

        elif command.name == 'DONE':
            self.sendResponse('GOODBYE')
            return ServerListener.ACTION_CLOSE_CONNECTION

        else:
            self.sendResponse(Message('UNKNOWN_COMMAND', [command.name]))

        return ServerListener.ACTION_NONE
