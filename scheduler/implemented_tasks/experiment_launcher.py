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


from tasks.task import Task
from tasks.jobs import Job
from tasks.jobs import JobList
from utilities.logs import getServerLogs
from utilities.io import generateUniqueFolderName
from pymash import Client
from pymash import Message
from django.conf import settings
from django.template import defaultfilters
from django.core.files import locks
from servers.models import Server
from servers.models import Alert
from servers.models import Job as ServerJob
from heuristics.models import HeuristicVersion
from heuristics.models import HeuristicEvaluationStep
from experiments.models import Experiment
from experiments.models import Configuration
from experiments.models import Setting
from experiments.models import Notification
from experiments.models import ClassificationResults
from experiments.models import GoalPlanningResult,GoalPlanningRound
from instruments.models import Instrument
from instruments.models import DataReport
from classifiers.models import Classifier
from goalplanners.models import Goalplanner
from tools.models import PluginErrorReport
from mash.tasks.models import Task as DBTask
from datetime import datetime
import os
import time
import tarfile
import traceback


class Section(object):

    def __init__(self):
        self.started            = False
        self.name               = None
        self.parameters         = []
        self.settings_to_send   = None
        self.next_operation     = None


#-------------------------------------------------------------------------------
# The class of the jobs of the 'ExperimentLauncher' task
#-------------------------------------------------------------------------------
class ExperimentLauncherJob(Job):

    def __init__(self, server_job=None, command=None):
        super(ExperimentLauncherJob, self).__init__(server_job=server_job, command=command)

        self.application_server          = None
        self.nb_evaluation_rounds_done   = 0
        self.nb_goalplanning_rounds_done = 0
        self.seeds                       = None
        self.current_section             = None
        self.instruments_to_send         = None



#-------------------------------------------------------------------------------
# This task tries to perform an experiment
#-------------------------------------------------------------------------------
class ExperimentLauncher(Task):

    SUPPORTED_COMMANDS = { 'RUN_EXPERIMENT': [int],     # <heuristic_version_id>
                           'CANCEL_EXPERIMENT': [int],  # <heuristic_version_id>
                         }
    SUPPORTED_EVENTS   = {}


    #---------------------------------------------------------------------------
    # Constructor
    #---------------------------------------------------------------------------
    def __init__(self):
        super(ExperimentLauncher, self).__init__()
        self.jobs = JobList(jobs_class=ExperimentLauncherJob)


    #---------------------------------------------------------------------------
    # Starts the job-specific processing
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def process(self, job):

        # Retrieve the experiment
        try:
            experiment = Experiment.objects.get(id=job.command.parameters[0])
        except:
            self.processError(job, 'Unknown experiment ID: %d' % job.command.parameters[0])
            return

        job.markAsRunning(experiment=experiment)

        # Job-specific processing
        if job.command.name == 'RUN_EXPERIMENT':

            # Task-dependent processing
            if (experiment.configuration.task.type == DBTask.TYPE_CLASSIFICATION) or \
               (experiment.configuration.task.type == DBTask.TYPE_OBJECT_DETECTION):
                self.runImageBasedExperiment(job)
            elif experiment.configuration.task.type == DBTask.TYPE_GOALPLANNING:
                self.runGoalPlanningExperiment(job)
            else:
                self.processError(job, 'Unknown task type: %s' % experiment.configuration.task.type)


    #---------------------------------------------------------------------------
    # Method called at startup. Use it to look in the database if there is some
    # job already waiting. They must be put in the job list.
    #---------------------------------------------------------------------------
    def onStartup(self):
        for experiment in Experiment.objects.filter(status=Experiment.STATUS_SCHEDULED):
            self.jobs.addJob(command=Message('RUN_EXPERIMENT', [experiment.id]))


    #---------------------------------------------------------------------------
    # Called when a new command was received. It allows the task to process it
    # independently of the jobs mechanism.
    #
    # @param    command     The command
    # @return               'False' if the command must be handled by the
    #                       standard jobs mechanism
    #---------------------------------------------------------------------------
    def onCommandReceived(self, command):

        if command.name == 'CANCEL_EXPERIMENT':

            experiment_id = command.parameters[0]

            # Check that a job handling the experiment is in the queue
            if not(self.jobs.hasJob(Message('RUN_EXPERIMENT', [experiment_id]))):
                self.outStream.write("ERROR - Experiment ID not found in the queue of jobs: %d\n" % experiment_id)
                return True

            # Retrieve the job handling the experiment and mark it as cancelled
            job_to_cancel = self.jobs.getJobs(command=Message('RUN_EXPERIMENT', [experiment_id]))[0]
            job_to_cancel.markAsCancelled()
            self.jobs.removeJobs([job_to_cancel])

            # Send an event about the cancelling of the experiment
            self.channel.sendMessage(Message('EVT_EXPERIMENT_CANCELLED', [experiment_id]))

            return True

        return False


    #---------------------------------------------------------------------------
    # Perform an image-based experiment (classification or object detection)
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def runImageBasedExperiment(self, job):

        # Search a free Image Server providing the needed database
        db_name = job.server_job.experiment.configuration.databaseName()

        job.outStream.write("Searching a free Image Server providing the database '%s'...\n" % db_name)

        servers = Server.objects.filter(server_type=Server.APPLICATION_SERVER, subtype=Server.SUBTYPE_IMAGES,
                                        provided_databases__name__in=[db_name])
        job.application_server = None
        for server in servers:
            job.outStream.write("    Contacting '%s:%d'...\n" % (server.address, server.port))

            client = Client()
            if client.connect(server.address, server.port):
                client.sendCommand('STATUS')
                response = client.waitResponse()
                if response.name == 'READY':
                    job.outStream.write("    Image Server found\n")
                    job.application_server = server

            client.close()
            del client

            if job.application_server is not None:
                break

        if job.application_server is None:
            job.outStream.write("Failed to find a free Image Server providing the database '%s'\n" % db_name)
            job.markAsDelayed(60)
            return

        # Search a free Experiment Server
        if not(self.selectExperimentServer(job)):
            return

        # Store the date/time of the start of the experiment
        job.server_job.experiment.start = datetime.now()
        job.server_job.experiment.end = None
        job.server_job.experiment.save()

        # Tell the Experiment Server about the type of experiment
        if job.server_job.experiment.configuration.task.type == DBTask.TYPE_CLASSIFICATION:
            experiment_type_name = 'Classification'
        else:
            experiment_type_name = 'ObjectDetection'

        if not(job.client.sendCommand(Message('SET_EXPERIMENT_TYPE', [experiment_type_name]))):
            self.processError(job, 'Failed to set the experiment type')
            return

        job.operation = ExperimentLauncher.sendApplicationServerInfos


    #---------------------------------------------------------------------------
    # Perform a goal-planning experiment
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def runGoalPlanningExperiment(self, job):

        # Ensure that the type of experiment is supported
        if job.server_job.experiment.configuration.experiment_type == Configuration.EVALUATION:
            self.processError(job, "Evaluation experiments doesn't support goal-planning tasks")
            return

        # Search a free Interactive Application Server suitable for this experiment
        goal_name = job.server_job.experiment.configuration.goalName()
        environment_name = job.server_job.experiment.configuration.environmentName()

        job.outStream.write("Searching a free Interactive Application Server providing " \
                             "the goal '%s' and the environment '%s'...\n" % (goal_name, environment_name))

        servers = Server.objects.filter(server_type=Server.APPLICATION_SERVER, subtype=Server.SUBTYPE_INTERACTIVE,
                                        provided_goals__name__in=[goal_name],
                                        provided_goals__environments__name__in=[environment_name])
        job.application_server = None
        for server in servers:
            job.outStream.write("    Contacting '%s:%d'...\n" % (server.address, server.port))

            client = Client()
            if client.connect(server.address, server.port):
                client.sendCommand('STATUS')
                response = client.waitResponse()
                if response.name == 'READY':
                    job.outStream.write("    Interactive Application Server found\n")
                    job.application_server = server

            client.close()
            del client

            if job.application_server is not None:
                break

        if job.application_server is None:
            job.outStream.write("Failed to find a free Interactive Application providing " \
                                 "the goal '%s' and the environment '%s'...\n" % (goal_name, environment_name))
            job.markAsDelayed(60)
            return

        # Search a free Experiment Server
        if not(self.selectExperimentServer(job)):
            return

        # Store the date/time of the start of the experiment
        job.server_job.experiment.start = datetime.now()
        job.server_job.experiment.end = None
        job.server_job.experiment.save()

        # Tell the Experiment Server about the type of experiment
        if not(job.client.sendCommand(Message('SET_EXPERIMENT_TYPE', ['GoalPlanning']))):
            self.processError(job, 'Failed to set the experiment type')
            return

        job.operation = ExperimentLauncher.sendApplicationServerInfos


    #---------------------------------------------------------------------------
    # Send the infos about the Application Server to use
    #---------------------------------------------------------------------------
    def sendApplicationServerInfos(self, job):
        response = job.client.waitResponse()
        if response.name != 'OK':
            self.processError(job, "Failed to set the experiment type", response)
            return

        # Tell the Experiment Server about the Application Server to use
        if not(job.client.sendCommand(Message('USE_APPLICATION_SERVER', [job.application_server.address, job.application_server.port]))):
            self.processError(job, 'Failed to select the Application Server')
            return

        job.operation = ExperimentLauncher.sendGlobalSeed


    #---------------------------------------------------------------------------
    # Send the global seed
    #---------------------------------------------------------------------------
    def sendGlobalSeed(self, job, no_waiting=False):
        if not(no_waiting):
            response = job.client.waitResponse()
            if response.name != 'OK':
                if job.nb_evaluation_rounds_done > 0:
                    self.processError(job, "Failed to reset the Experiment Server", response, disable_error_report=True)
                else:
                    self.processError(job, "Failed to select the Application Server", response)
                return

        # Retrieve the global seed(s) from the database
        if job.seeds is None:
            configuration = job.server_job.experiment.configuration
            try:
                job.seeds = map(lambda x: int(x), configuration.settings.get(name='USE_GLOBAL_SEED').value.split(' '))
            except:
                job.seeds = [int(time.time())]
                configuration.addSetting('USE_GLOBAL_SEED', ' '.join(map(lambda x: str(x), job.seeds)))

        # Tell the Experiment Server about the global seed to use
        if job.server_job.experiment.configuration.experiment_type == Configuration.EVALUATION:
            seed = job.seeds[job.nb_evaluation_rounds_done]
        else:
            seed = job.seeds[0]

        if not(job.client.sendCommand(Message('USE_GLOBAL_SEED', [seed]))):
            self.processError(job, 'Failed to set the global seed')
            return

        job.operation = ExperimentLauncher.sendExperimentSetupSection


    #---------------------------------------------------------------------------
    # Start to send the 'experiment setup' section
    #---------------------------------------------------------------------------
    def sendExperimentSetupSection(self, job):
        response = job.client.waitResponse()
        if response.name != 'OK':
            self.processError(job, "Failed to set the global seed", response)
            return

        # Setup the job
        section                  = Section()
        section.name             = 'EXPERIMENT_SETUP'
        section.next_operation   = ExperimentLauncher.sendInstrumentsList
        section.settings_to_send = map(lambda x: (x.name[len(section.name) + 1:], x.value),
                                       Setting.objects.filter(configuration=job.server_job.experiment.configuration,
                                                              name__startswith=section.name + '/'))
        job.current_section = section

        self.sendSection(job, first=True)


    #---------------------------------------------------------------------------
    # Send the list of instruments
    #---------------------------------------------------------------------------
    def sendInstrumentsList(self, job):
        response = job.client.waitResponse()
        if response.name != 'OK':
            self.processError(job, "Failed to send the 'EXPERIMENT_SETUP' section", response)
            return

        # Setup the job
        job.instruments_to_send = list(Instrument.objects.filter(configuration=job.server_job.experiment.configuration).exclude(
                                                                 status=Instrument.DISABLED).exclude(
                                                                 status=Instrument.BUILTIN))
        job.current_section = None

        if len(job.instruments_to_send) > 0:
            self.sendNextInstrument(job, first=True)
        else:
            self.sendPredictorModel(job, no_waiting=True)


    #---------------------------------------------------------------------------
    # Send the next instrument
    #---------------------------------------------------------------------------
    def sendNextInstrument(self, job, first=False):

        if not(first):
            response = job.client.waitResponse()
            if response.name != 'OK':
                self.processError(job, "Failed to send the 'EXPERIMENT_SETUP' section", response)
                return

        # Test if we must send the parameters of the current instrument
        if job.current_section is not None:
            self.sendSection(job, first=True)
            return

        # Otherwise send the next instrument
        else:
            instrument = job.instruments_to_send[0]
            job.instruments_to_send = job.instruments_to_send[1:]

            section_full_name = 'INSTRUMENT_SETUP/%s/' % instrument.fullname()

            section                  = Section()
            section.name             = 'INSTRUMENT_SETUP'
            section.parameters       = [instrument.fullname()]

            if len(job.instruments_to_send) > 0:
                section.next_operation   = ExperimentLauncher.sendNextInstrument
            else:
                section.next_operation   = ExperimentLauncher.sendPredictorModel
                job.instruments_to_send = None

            section.settings_to_send = map(lambda x: (x.name[len(section_full_name):], x.value),
                                           Setting.objects.filter(configuration=job.server_job.experiment.configuration,
                                                                  name__startswith=section_full_name))
            job.current_section = section

            if not(job.client.sendCommand(Message('USE_INSTRUMENT', [instrument.fullname()]))):
                self.processError(job, "Failed to select the instrument '%s'" % instrument.fullname())
                return

            job.operation = ExperimentLauncher.sendNextInstrument


    #---------------------------------------------------------------------------
    # Send the predictor model
    #---------------------------------------------------------------------------
    def sendPredictorModel(self, job, no_waiting=False):

        if not(no_waiting):
            response = job.client.waitResponse()
            if response.name != 'OK':
                self.processError(job, "Failed to send the list of instruments", response)
                return

        try:
            model_filenames = Setting.objects.get(name='USE_PREDICTOR_MODEL', configuration=job.server_job.experiment.configuration).value.split(' ')

            if job.server_job.experiment.configuration.experiment_type == Configuration.EVALUATION:
                if job.nb_evaluation_rounds_done < len(model_filenames):
                    model_filename = model_filenames[job.nb_evaluation_rounds_done]
                else:
                    model_filename = model_filenames[-1]
            else:
                model_filename = model_filenames[0]

            if not(self.sendFile(job, 'USE_PREDICTOR_MODEL', os.path.join(settings.MODELS_ROOT, model_filename))):
                if job.server_job.status == ServerJob.STATUS_FAILED:
                    return

            job.operation = ExperimentLauncher.sendPredictorInternalData
        except:
            self.sendPredictor(job, no_waiting=True)


    #---------------------------------------------------------------------------
    # Send the predictor internal data
    #---------------------------------------------------------------------------
    def sendPredictorInternalData(self, job):
        response = job.client.waitResponse()
        if response.name != 'OK':
            self.processError(job, "Failed to send the predictor model", response)
            return

        try:
            internal_data_filenames = Setting.objects.get(name='USE_PREDICTOR_INTERNAL_DATA', configuration=job.server_job.experiment.configuration).value.split(' ')

            if job.server_job.experiment.configuration.experiment_type == Configuration.EVALUATION:
                if job.nb_evaluation_rounds_done < len(internal_data_filenames):
                    internal_data_filename = internal_data_filenames[job.nb_evaluation_rounds_done]
                else:
                    internal_data_filename = internal_data_filenames[-1]
            else:
                internal_data_filename = internal_data_filenames[0]

            if not(self.sendFile(job, 'USE_PREDICTOR_INTERNAL_DATA', os.path.join(settings.MODELS_ROOT, internal_data_filename))):
                if job.server_job.status == ServerJob.STATUS_FAILED:
                    return

            job.operation = ExperimentLauncher.sendPredictor
        except:
            self.sendPredictor(job, no_waiting=True)


    #---------------------------------------------------------------------------
    # Send the predictor name
    #---------------------------------------------------------------------------
    def sendPredictor(self, job, no_waiting=False):

        if not(no_waiting):
            response = job.client.waitResponse()
            if response.name != 'OK':
                self.processError(job, "Failed to send the internal data of the predictor", response)
                return

        # Retrieve the predictor name
        try:
            predictor_name = Setting.objects.get(configuration=job.server_job.experiment.configuration,
                                                 name='USE_PREDICTOR').value
        except:
            self.processError(job, 'No predictor specified')
            return


        # Tell the Experiment Server about the predictor to use
        if not(job.client.sendCommand(Message('USE_PREDICTOR', [predictor_name]))):
            self.processError(job, 'Failed to set the predictor')
            return

        job.operation = ExperimentLauncher.sendPredictorSettings


    #---------------------------------------------------------------------------
    # Start to send the settings of the predictor
    #---------------------------------------------------------------------------
    def sendPredictorSettings(self, job):
        response = job.client.waitResponse()
        if response.name != 'OK':
            self.processError(job, "Failed to set the predictor", response)
            return

        # Setup the job
        section                  = Section()
        section.name             = 'PREDICTOR_SETUP'
        section.next_operation   = ExperimentLauncher.sendHeuristicsRepositoryUrl
        section.settings_to_send = map(lambda x: (x.name[len(section.name) + 1:], x.value),
                                       Setting.objects.filter(configuration=job.server_job.experiment.configuration,
                                                              name__startswith=section.name + '/'))
        job.current_section = section

        self.sendSection(job, first=True)


    #---------------------------------------------------------------------------
    # Send the URL of the repository of heuristics
    #---------------------------------------------------------------------------
    def sendHeuristicsRepositoryUrl(self, job, no_waiting=False):

        if not(no_waiting):
            response = job.client.waitResponse()
            if response.name != 'OK':
                self.processError(job, "Failed to send the 'PREDICTOR_SETUP' section", response)
                return

        # Tell the Experiment Server about the repository to use
        if not(job.client.sendCommand(Message('USE_HEURISTICS_REPOSITORY',
                                              [settings.REPOSITORY_HEURISTICS_URL]))):
            self.processError(job, 'Failed to send the URL of the repository of heuristics')
            return

        job.operation = ExperimentLauncher.sendHeuristicsList


    #---------------------------------------------------------------------------
    # Send the list of heuristics
    #---------------------------------------------------------------------------
    def sendHeuristicsList(self, job):
        response = job.client.waitResponse()
        if response.name != 'OK':
            self.processError(job, "Failed to send the URL of the repository of heuristics", response)
            return

        # Setup the job
        job.heuristics_to_send = list(job.server_job.experiment.configuration.heuristics_set.filter(
                                                                        status=HeuristicVersion.STATUS_OK))
        job.current_section = None

        if len(job.heuristics_to_send) > 0:
            self.sendNextHeuristic(job, first=True)
        else:
            self.processError(job, 'No enabled heuristic version available')


    #---------------------------------------------------------------------------
    # Send the next heuristic
    #---------------------------------------------------------------------------
    def sendNextHeuristic(self, job, first=False):

        if not(first):
            response = job.client.waitResponse()
            if response.name != 'OK':
                self.processError(job, "Failed to send the 'EXPERIMENT_SETUP' section", response)
                return

        heuristic = job.heuristics_to_send[0]
        job.heuristics_to_send = job.heuristics_to_send[1:]

        if len(job.heuristics_to_send) > 0:
            job.operation = ExperimentLauncher.sendNextHeuristic
        else:
            job.operation = ExperimentLauncher.trainPredictor
            job.heuristics_to_send = None

        if not(job.client.sendCommand(Message('USE_HEURISTIC', [heuristic.fullname()]))):
            self.processError(job, "Failed to select the heuristic '%s'" % heuristic.fullname())


    #---------------------------------------------------------------------------
    # Ask the predictor to train itself
    #---------------------------------------------------------------------------
    def trainPredictor(self, job):
        response = job.client.waitResponse()
        if response.name != 'OK':
            self.processError(job, "Failed to send the list of heuristics", response)
            return

        if not(job.client.sendCommand(Message('TRAIN_PREDICTOR'))):
            self.processError(job, "Failed to tell the predictor to train itself")
            return

        # Task-dependent processing
        if job.server_job.experiment.configuration.task.type == DBTask.TYPE_GOALPLANNING:
            job.operation = ExperimentLauncher.processGoalPlanningTrainingResult
        else:
            job.operation = ExperimentLauncher.processImageBasedTrainingResult


    #---------------------------------------------------------------------------
    # Process the training result of an image-based experiment (classification
    # or object detection)
    #---------------------------------------------------------------------------
    def processImageBasedTrainingResult(self, job):
        response = job.client.waitResponse()

        # Process the notifications
        if response.name == 'NOTIFICATION':
            self.updateNotification(job, response.parameters)
            job.operation = ExperimentLauncher.processImageBasedTrainingResult
            return

        # Process the errors
        elif response.name != 'TRAIN_ERROR':
            self.processError(job, "Failed to train the predictor", response)
            return

        # Save the results
        if job.server_job.experiment.configuration.experiment_type != Configuration.EVALUATION:
            try:
                results = job.server_job.experiment.classification_results
            except:
                results = ClassificationResults()
                results.experiment = job.server_job.experiment

            results.train_error = float(response.parameters[0])
            results.save()
        else:
            evaluation_results = job.server_job.experiment.evaluation_results

            try:
                step = evaluation_results.steps.get(seed=job.seeds[job.nb_evaluation_rounds_done])
            except:
                step = HeuristicEvaluationStep()
                step.evaluation_results = evaluation_results
                step.seed = job.seeds[job.nb_evaluation_rounds_done]

            step.train_error = float(response.parameters[0])
            step.save()

        # Test the predictor
        if not(job.client.sendCommand(Message('TEST_PREDICTOR'))):
            self.processError(job, "Failed to tell the predictor to test itself")
            return

        job.operation = ExperimentLauncher.processImageBasedTestResult


    #---------------------------------------------------------------------------
    # Process the test result of an image-based experiment (classification or
    # object detection)
    #---------------------------------------------------------------------------
    def processImageBasedTestResult(self, job):
        response = job.client.waitResponse()

        # Process the notifications
        if response.name == 'NOTIFICATION':
            self.updateNotification(job, response.parameters)
            job.operation = ExperimentLauncher.processImageBasedTestResult
            return

        # Process the errors
        elif response.name != 'TEST_ERROR':
            self.processError(job, "Failed to test the predictor", response)
            return

        # Save the results
        if job.server_job.experiment.configuration.experiment_type != Configuration.EVALUATION:
            try:
                results = job.server_job.experiment.classification_results
            except:
                results = ClassificationResults()
                results.experiment = job.server_job.experiment

            results.test_error = float(response.parameters[0])
            results.save()
        else:
            evaluation_results = job.server_job.experiment.evaluation_results

            try:
                step = evaluation_results.steps.get(seed=job.seeds[job.nb_evaluation_rounds_done])
            except:
                step = HeuristicEvaluationStep()
                step.evaluation_results = evaluation_results
                step.seed = job.seeds[job.nb_evaluation_rounds_done]

            step.test_error = float(response.parameters[0])
            step.save()

        # Retrieve the data report, if necessary
        if (job.server_job.experiment.configuration.experiment_type != Configuration.EVALUATION) or \
           (job.nb_evaluation_rounds_done == len(job.seeds) - 1):
            if not(job.client.sendCommand(Message('REPORT_DATA'))):
                self.processError(job, "Failed to ask for the data report")
                return

            job.operation = ExperimentLauncher.processDataReport

        else:
            self.finalizeExperiment(job)


    #---------------------------------------------------------------------------
    # Process the training result of a goal-planning experiment
    #---------------------------------------------------------------------------
    def processGoalPlanningTrainingResult(self, job):
        response = job.client.waitResponse()

        # Process the notifications
        if response.name == 'NOTIFICATION':
            self.updateNotification(job, response.parameters)
            job.operation = ExperimentLauncher.processGoalPlanningTrainingResult
            return

        # Process the errors
        elif response.name != 'TRAIN_RESULT':
            self.processError(job, "Failed to train the predictor", response)
            return

        #TODO : Dummy function (not used anymore...only for the tests)
        job.nb_goalplanning_rounds_done = 0
        self.updateNotification(job, ['CURRENT_ROUND', '0 %d' % job.server_job.experiment.configuration.nbTestRounds()])
        self.updateNotification(job, ['TEST_STEP_DONE', '0 1000'])

        # Test the predictor
        try:
            nb_test_rounds = int(Setting.objects.get(name='TEST_PREDICTOR/NB_TEST_ROUNDS', configuration=job.server_job.experiment.configuration).value)
        except:
            nb_test_rounds = 1

        try:
            nb_max_actions = int(Setting.objects.get(name='TEST_PREDICTOR/NB_MAX_ACTIONS', configuration=job.server_job.experiment.configuration).value)
        except:
            nb_max_actions = 1000

        if not(job.client.sendCommand(Message('TEST_PREDICTOR', [nb_test_rounds, nb_max_actions]))):
            self.processError(job, "Failed to tell the predictor to test itself")
            return

        job.operation = ExperimentLauncher.processGoalPlanningTestResult


    #---------------------------------------------------------------------------
    # Process the test result of a goal-planning experiment
    #---------------------------------------------------------------------------
    def processGoalPlanningTestResult(self, job):
        response = job.client.waitResponse()

        # Process the notifications
        if response.name == 'NOTIFICATION':
            self.updateNotification(job, response.parameters)
            job.operation = ExperimentLauncher.processGoalPlanningTestResult
            return

        #create a summary result if it doesn't exist yet for current experiment
        validExperience = GoalPlanningResult.objects.filter(experiment=job.server_job.experiment)
        if not validExperience:
            GPsummary = GoalPlanningResult(experiment = job.server_job.experiment)
            GPsummary.save()
        else:
            GPsummary = GoalPlanningResult.objects.get(experiment = job.server_job.experiment)

        #Get values
        #Process the rounds
        if response.name == 'TEST_ROUND':
            #create a GP round result
            results = GoalPlanningRound(summary=GPsummary)
            results.round = int(response.parameters[0])

            #process batch messages
            while True:
                response = job.client.waitResponse()
                if response.name == 'RESULT':
                    if response.parameters[0] == 'GOAL_REACHED':
                        results.result = GoalPlanningRound.RESULT_GOAL_REACHED
                    elif response.parameters[0] == 'TASK_FAILED':
                        results.result = GoalPlanningRound.RESULT_TASK_FAILED
                    else:
                        results.result = GoalPlanningRound.RESULT_NONE

                elif response.name == 'SCORE':
                    results.score = float(response.parameters[0])
                elif response.name == 'NB_ACTIONS_DONE':
                    results.nbActionsDone = int(response.parameters[0])
                elif response.name == 'NB_MIMICKING_ERRORS':
                    results.nbMimickingErrors = int(response.parameters[0])
                elif response.name == 'NB_NOT_RECOMMENDED_ACTIONS':
                    results.nbNotRecommandedActions = int(response.parameters[0])
                elif response.name == 'TEST_ROUND_END':
                    # Save round results
                    results.save()
                    job.operation = ExperimentLauncher.processGoalPlanningTestResult
                    return
                else:
                    self.processError(job, "Failed to test the predictor", response)
                    return


        #Process the summary and save in it
        elif response.name == 'TEST_SUMMARY':
            #process batch messages
            while True:
                response = job.client.waitResponse()

                if response.name == 'NB_GOALS_REACHED':
                    GPsummary.nbGoalsReached = int(response.parameters[0])
                elif response.name == 'NB_TASKS_FAILED':
                    GPsummary.nbTasksFailed = int(response.parameters[0])
                elif response.name == 'NB_ACTIONS_DONE':
                    GPsummary.nbActionsDone = int(response.parameters[0])
                elif response.name == 'NB_MIMICKING_ERRORS':
                    GPsummary.nbMimickingErrors = int(response.parameters[0])
                elif response.name == 'NB_NOT_RECOMMENDED_ACTIONS':
                    GPsummary.nbNotRecommandedActions = int(response.parameters[0])
                elif response.name == 'TEST_SUMMARY_END':
                    GPsummary.save()
                    break
                else:
                    self.processError(job, "Failed to test the predictor", response)
                    return


        else:
            self.processError(job, "Failed to test the predictor", response)
            return

        # Notifications
        job.nb_goalplanning_rounds_done += 1
        self.updateNotification(job, ['CURRENT_ROUND', '%d %d' % (job.nb_goalplanning_rounds_done,
                                                                  job.server_job.experiment.configuration.nbTestRounds())])

        # Retrieve the data report
        if not(job.client.sendCommand(Message('REPORT_DATA'))):
            self.processError(job, "Failed to ask for the data report")
            return

        job.operation = ExperimentLauncher.processDataReport


    #---------------------------------------------------------------------------
    # Process the data report
    #---------------------------------------------------------------------------
    def processDataReport(self, job):
        response = job.client.waitResponse()

        if response.name == 'ERROR':
            self.processError(job, "Failed to retrieve the data report", response)
            return

        if (response.name != 'DATA') or (len(response.parameters) != 1) :
            self.finalizeExperiment(job)
            return

        filename = os.path.join(settings.DATA_REPORTS_ROOT, 'dataReports.lock')
        lock_file = open(filename, 'wb')
        try:
            os.chmod(filename, 0766)
        except:
            pass
        locks.lock(lock_file, locks.LOCK_EX)

        report_filename = generateUniqueFolderName() + '.tar.gz'
        fullpath = os.path.join(settings.DATA_REPORTS_ROOT, report_filename)
        if not(os.path.exists(os.path.dirname(fullpath))):
            os.makedirs(os.path.dirname(fullpath))

        outFile = open(fullpath, 'wb')

        lock_file.close()

        size = response.parameters[0]
        max_size = 10 * 1024
        while size > 0:
            nb = min(size, max_size)

            data = job.client.waitData(nb)
            if data is None:
                outFile.close()
                os.remove(fullpath)
                self.finalizeExperiment(job)
                return

            outFile.write(data)

            size -= nb

        outFile.close()

        report                 = DataReport()
        report.experiment      = job.server_job.experiment
        report.filename        = report_filename
        report.save()

        report.instruments_set = list(Instrument.objects.filter(configuration=job.server_job.experiment.configuration).exclude(
                                                                status=Instrument.DISABLED))
        report.save()

        self.finalizeExperiment(job)


    #---------------------------------------------------------------------------
    # Called when the experiment was successfully performed
    #---------------------------------------------------------------------------
    def finalizeExperiment(self, job):
        configuration = job.server_job.experiment.configuration

        job.server_job.logs = getServerLogs(job.client, job.server_job.logs, filter_list=['Predictor.log'])
        job.server_job.save()

        # Evaluation experiment: determine if another experiment must be performed
        if configuration.experiment_type == Configuration.EVALUATION:
            job.nb_evaluation_rounds_done += 1
            if job.nb_evaluation_rounds_done < len(job.seeds):
                if not(job.client.sendCommand(Message('RESET'))):
                    self.processError(job, "Failed to reset the Experiment Server")
                else:
                    job.operation = ExperimentLauncher.sendGlobalSeed
                return

        # Base contest experiment: create the configuration of the contest, based on
        # the results of the base experiment
        if configuration.experiment_type == Configuration.CONTEST_BASE:
            self.createContestConfiguration(job)

        # Store the date/time of the end of the experiment
        job.server_job.experiment.end = datetime.now()
        job.server_job.experiment.save()

        # The experiment is done
        if (configuration.experiment_type != Configuration.EVALUATION) and (job.nb_evaluation_rounds_done > 0):
            job.markAsDone(experiment_status=Experiment.STATUS_DONE_WITH_ERRORS)
        else:
            job.markAsDone()

        # Send an event about the success of the experiment, if necessary
        if configuration.experiment_type == Configuration.PUBLIC:
            self.channel.sendMessage(Message('EVT_PUBLIC_EXPERIMENT_DONE', [job.server_job.experiment.id]))
        elif configuration.experiment_type == Configuration.EVALUATION:
            self.channel.sendMessage(Message('EVT_HEURISTIC_EVALUATED', [job.server_job.experiment.evaluation_results.heuristic_version.id]))
        elif configuration.experiment_type == Configuration.CONTEST_ENTRY:
            self.channel.sendMessage(Message('RANK_CONTEST_ENTRIES', [configuration.experiment.contest_entry.contest.id]))
        elif configuration.experiment_type == Configuration.SIGNATURE:
            self.channel.sendMessage(Message('EVT_HEURISTIC_SIGNATURE_RECORDED', [job.server_job.experiment.signature.heuristic_version.id]))


    #---------------------------------------------------------------------------
    # Process the errors
    #---------------------------------------------------------------------------
    def processError(self, job, message, response=None, disable_error_report=False):
        def encode(text):
            return text.replace('\t', '    ').replace("'", "\\'").replace('"', '\\"')

        def parseHeuristicName(name):
            parts = name.split('/')
            if len(parts) == 3:
                return (parts[0], parts[1], int(parts[2]))
            else:
                return (parts[0], parts[1], 1)

        alert = Alert()
        alert.message = message

        if response is not None:
            if response.name == 'ERROR':
                alert.details = "Error: %s" % response.parameters[0]
            else:
                alert.details = "Unknown response from the Experiment Server. Expected: OK, got: %s" % response.toString()

        if alert.details is not None:
            job.outStream.write("ERROR - %s\n%s\n" % (alert.message, alert.details))
        else:
            job.outStream.write("ERROR - %s\n" % alert.message)

        can_retry = False

        # Ask for an error report
        if not(disable_error_report) and (job.client is not None) and job.client.sendCommand('REPORT_ERRORS'):
            response = job.client.waitResponse()

            error_report            = PluginErrorReport()
            error_report.experiment = job.server_job.experiment
            needContext             = False
            needStacktrace          = False

            if response.name == 'ERROR':
                alert.details = encode(response.parameters[0]).decode('utf-8')
                error_report  = None

            elif response.name.startswith('HEURISTIC_'):
                configuration = job.server_job.experiment.configuration

                (user_name, heuristic_name, version) = parseHeuristicName(response.parameters[0])
                error_report.heuristic_version = configuration.heuristics_set.get(
                                                                          heuristic__author__username=user_name,
                                                                          heuristic__name=heuristic_name,
                                                                          version=version)
                needContext = True

                if response.name == 'HEURISTIC_CRASH':
                    error_report.error_type = PluginErrorReport.ERROR_CRASH
                    needStacktrace          = True
                elif response.name == 'HEURISTIC_TIMEOUT':
                    error_report.error_type = PluginErrorReport.ERROR_TIMEOUT
                elif response.name == 'HEURISTIC_ERROR':
                    error_report.error_type  = PluginErrorReport.ERROR_OTHER
                    error_report.description = response.parameters[1]

                error_report.heuristic_version.status = HeuristicVersion.STATUS_DISABLED
                error_report.heuristic_version.status_date = datetime.now()
                error_report.heuristic_version.save()

                can_retry = (configuration.heuristics_set.filter(status=HeuristicVersion.STATUS_OK).count() > 0) and \
                            (configuration.experiment_type != Configuration.EVALUATION) and \
                            (configuration.experiment_type != Configuration.CONTEST_ENTRY)

            elif response.name.startswith('PREDICTOR_'):
                (user_name, predictor_name) = job.server_job.experiment.configuration.predictorName().split('/')

                if job.server_job.experiment.configuration.task.type != DBTask.TYPE_GOALPLANNING:
                    error_report.classifier = Classifier.objects.get(author__username=user_name, name=predictor_name)
                    # if error_report.classifier.status == Classifier.ENABLED:
                    #     error_report.classifier.status = Classifier.EXPERIMENTAL
                    #     error_report.classifier.status_date = datetime.now()
                    #     error_report.classifier.save()
                else:
                    error_report.goalplanner = Goalplanner.objects.get(author__username=user_name, name=predictor_name)
                    # if error_report.goalplanner.status == Goalplanner.ENABLED:
                    #     error_report.goalplanner.status = Goalplanner.EXPERIMENTAL
                    #     error_report.goalplanner.status_date = datetime.now()
                    #     error_report.goalplanner.save()

                needContext = True

                if response.name == 'PREDICTOR_CRASH':
                    error_report.error_type = PluginErrorReport.ERROR_CRASH
                    needStacktrace          = True
                elif response.name == 'PREDICTOR_ERROR':
                    error_report.error_type  = PluginErrorReport.ERROR_OTHER
                    error_report.description = encode(response.parameters[0]).decode('utf-8')

            elif response.name.startswith('INSTRUMENT_'):
                (user_name, instrument_name) = response.parameters[0].split('/')

                error_report.instrument = job.server_job.experiment.configuration.instruments_set.get(author__username=user_name, name=instrument_name)

                needContext = True
                can_retry = (job.server_job.experiment.configuration.experiment_type != Configuration.EVALUATION)

                if response.name == 'INSTRUMENT_CRASH':
                    error_report.error_type = PluginErrorReport.ERROR_CRASH
                    needStacktrace          = True
                elif response.name == 'INSTRUMENT_ERROR':
                    error_report.error_type = PluginErrorReport.ERROR_OTHER
                    error_report.description = response.parameters[1]

                error_report.instrument.status = Instrument.DISABLED
                error_report.instrument.save()

            else:
                error_report  = None

            # Retrieve the context (if necessary)
            if needContext:
                response = job.client.waitResponse()
                if response.name == 'CONTEXT':
                    error_report.context = encode(response.parameters[0])

            # Retrieve the stack trace (if necessary)
            if needStacktrace:
                response = job.client.waitResponse()
                if response.name == 'STACKTRACE':
                    error_report.stacktrace = encode(response.parameters[0])

            # Store the error report in the database (if necessary) and send an
            # e-mail about the error report (to whoever can solve the problem)
            if error_report is not None:
                error_report.save()
                error_report.send_mail()

        # Determine if the experiment failed or if we can retry to do it
        if not(can_retry):
            job.server_job.logs = getServerLogs(job.client, job.server_job.logs)
            job.server_job.save()

            # Store the date/time of the end of the experiment
            job.server_job.experiment.end = datetime.now()
            job.server_job.experiment.save()

            job.markAsFailed(alert=alert)

            # Send an event about the failure of the experiment
            if (job.server_job.experiment is not None) and \
               (job.server_job.experiment.configuration.experiment_type == Configuration.PUBLIC):
                self.channel.sendMessage(Message('EVT_PUBLIC_EXPERIMENT_FAILED', [job.server_job.experiment.id]))
        else:
            job.nb_evaluation_rounds_done += 1

            if not(job.client.sendCommand(Message('RESET'))):
                self.processError(job, "Failed to reset the Experiment Server")
            else:
                job.operation = ExperimentLauncher.sendGlobalSeed


    #---------------------------------------------------------------------------
    # Send the current section
    #---------------------------------------------------------------------------
    def sendSection(self, job, first=False):

        # Start the section if necessary
        if first:
            if not(job.client.sendCommand(Message('BEGIN_%s' % job.current_section.name, job.current_section.parameters))):
                self.processError(job, "Failed to start the '%s' section" % job.current_section.name)
                return

            job.operation = ExperimentLauncher.sendSection
            return

        # Process the response to the previous command sent
        response = job.client.waitResponse()
        if response.name != 'OK':
            self.processError(job, "Failed to send a setting")
            return

        job.current_section.started = True

        # If we are done, close the section
        if len(job.current_section.settings_to_send) == 0:
            if not(job.client.sendCommand(Message('END_%s' % job.current_section.name))):
                self.processError(job, "Failed to end the '%s' section" % job.current_section.name)
                return

            job.operation = job.current_section.next_operation
            job.current_section = None
            return

        # Otherwise send the next setting
        else:
            next_setting = job.current_section.settings_to_send[0]
            job.current_section.settings_to_send = job.current_section.settings_to_send[1:]

            if (job.current_section.name == 'EXPERIMENT_SETUP') and (next_setting[0] == 'LABELS'):

                all_labels = filter(lambda x: len(x) > 0, next_setting[1].replace('\r', '').split('\n'))

                if job.server_job.experiment.configuration.experiment_type == Configuration.EVALUATION:
                    if job.nb_evaluation_rounds_done < len(all_labels):
                        labels = all_labels[job.nb_evaluation_rounds_done].split(' ')
                    else:
                        labels = all_labels[-1].split(' ')
                else:
                    labels = all_labels[0].split(' ')

                if not(job.client.sendCommand(Message(next_setting[0], labels))):
                    self.processError(job, "Failed to send the setting '%s'" % next_setting[0])
                    return
            else:
                if not(job.client.sendCommand(Message(next_setting[0], [next_setting[1]]))):
                    self.processError(job, "Failed to send the setting '%s'" % next_setting[0])
                    return

            job.operation = ExperimentLauncher.sendSection


    #---------------------------------------------------------------------------
    # Send the content of a file
    #---------------------------------------------------------------------------
    def sendFile(self, job, command_name, filename):

        inFile = open(filename, 'rb')
        inFile.seek(0, os.SEEK_END)
        size = inFile.tell()
        inFile.seek(0, os.SEEK_SET)

        if size == 0:
            return False

        if not(job.client.sendCommand(Message(command_name, [size]))):
            inFile.close()
            self.processError(job, "Failed to send the '%s' command" % command_name)
            return False

        max_size = 10 * 1024
        while size > 0:
            nb = min(size, max_size)
            data = inFile.read(size)

            if not(job.client.sendData(data)):
                inFile.close()
                self.processError(job, "Failed to send the content of the file '%s'" % filename)
                return False

            size -= nb

        inFile.close()

        return True


    #---------------------------------------------------------------------------
    # Update (or create) a notification in the database
    #---------------------------------------------------------------------------
    def updateNotification(self, job, parameters):
        try:
            notification = job.server_job.experiment.notifications.get(name=parameters[0])
            notification.value = ' '.join(map(lambda x: str(x), parameters[1:]))
            notification.save()
        except:
            notification            = Notification()
            notification.name       = parameters[0]
            notification.value      = ' '.join(map(lambda x: str(x), parameters[1:]))
            notification.experiment = job.server_job.experiment
            notification.save()


    #---------------------------------------------------------------------------
    # Select a free Experiment Server
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def selectExperimentServer(self, job):
        job.outStream.write("Searching a free Experiment Server suitable for the task\n")

        experiment_type = job.server_job.experiment.configuration.experiment_type
        if experiment_type == Configuration.CONTEST_BASE:
            experiment_type = Configuration.CONTEST_ENTRY
        elif experiment_type == Configuration.SIGNATURE:
            experiment_type = Configuration.EVALUATION

        servers = []

        servers.extend(list(Server.objects.filter(server_type=Server.EXPERIMENTS_SERVER,
                                                  supported_tasks__in=[job.server_job.experiment.configuration.task],
                                                  restrict_experiment=experiment_type)))

        servers.extend(list(Server.objects.filter(server_type=Server.EXPERIMENTS_SERVER,
                                                  supported_tasks__in=[job.server_job.experiment.configuration.task],
                                                  restrict_experiment__isnull=True)))

        for server in servers:
            job.outStream.write("    Contacting '%s:%d'...\n" % (server.address, server.port))

            job.client = Client(outStream = job.outStream)
            if job.client.connect(server.address, server.port):
                job.client.sendCommand('STATUS')
                response = job.client.waitResponse()
                if response.name == 'READY':
                    job.client.sendCommand('INFO')
                    response = job.client.waitResponse()
                    if (response.name == 'TYPE') and (response.parameters[0] == 'ExperimentServer'):
                        response = job.client.waitResponse()
                        if (response.name == 'PROTOCOL') and (str(response.parameters[0]) == '1.7'):
                            job.outStream.write("    Image Server found\n")
                            job.server_job.server = server
                            job.server_job.save()
                            return True

            job.client.close()
            del job.client
            job.client = None

        job.outStream.write("Failed to find a free Experiment Server\n")
        job.markAsDelayed(60)
        return False


    #---------------------------------------------------------------------------
    # Create the configuration of a contest, based on the results of a base
    # experiment
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def createContestConfiguration(self, job):
        try:
            job.outStream.write("Creating the contest configuration...\n")

            # Retrieve the trained model
            report_filename = job.server_job.experiment.data_report.filename
            model_folder = report_filename.replace('.tar.gz', '')

            report_fullpath = os.path.join(settings.DATA_REPORTS_ROOT, report_filename)
            model_fullpath = os.path.join(settings.MODELS_ROOT, model_folder)

            os.makedirs(os.path.dirname(model_fullpath))

            tar = tarfile.open(report_fullpath, 'r:gz')
            try:
                tar.extract('predictor.model', path=model_fullpath)
                tar.extract('predictor.internal', path=model_fullpath)
            except:
                pass
            tar.close()

            model_path = None
            model_internal_path = None

            if os.path.exists(os.path.join(model_fullpath, 'predictor.model')):
                model_path = os.path.join(model_folder, 'predictor.model')

                if os.path.exists(os.path.join(model_fullpath, 'predictor.internal')):
                    model_internal_path = os.path.join(model_folder, 'predictor.internal')

            if model_path is None:
                job.outStream.write("Failed to extract the predictor model from the data report\n")
                return

            # Create the configuration
            template = job.server_job.experiment.configuration

            configuration = Configuration()

            if template.name.endswith('/base'):
                configuration.name = template.name.replace('/base', '')
            else:
                configuration.name = template.name + '/contest'    # Just in case, should not happen

            configuration.heuristics      = Configuration.CUSTOM_HEURISTICS_LIST
            configuration.experiment_type = Configuration.CONTEST_ENTRY
            configuration.task            = template.task
            configuration.save()

            # Add the list of instruments
            for instrument in template.instruments_set.all():
                configuration.instruments_set.add(instrument)

            # Save the configuration
            configuration.save()

            # Add the settings
            for setting in template.settings.exclude(name='USE_PREDICTOR_MODEL').exclude(name='USE_PREDICTOR_INTERNAL_DATA'):
                configuration.addSetting(setting.name, setting.value)

            configuration.addSetting('USE_PREDICTOR_MODEL', model_path)

            if model_internal_path is not None:
                configuration.addSetting('USE_PREDICTOR_INTERNAL_DATA', model_internal_path)

            # Add the heuristic versions referenced by the model
            inModel = open(os.path.join(model_fullpath, 'predictor.model'), 'r')

            in_heuristics_section = False
            while True:
                line = inModel.readline()
                if line[-1] == '\n':
                    line = line[:-1]

                if not(in_heuristics_section):
                    if line == 'HEURISTICS':
                        in_heuristics_section = True
                    continue
                else:
                    if line == 'END_HEURISTICS':
                        break

                parts = line.split(' ')[0].split('/')

                if len(parts) == 3:
                    author  = parts[0]
                    name    = parts[1]
                    version = int(parts[2])
                else:
                    author  = parts[0]
                    name    = parts[1]
                    version = 1

                configuration.heuristics_set.add(HeuristicVersion.objects.exclude(status=HeuristicVersion.STATUS_DELETED).get(
                                                                            heuristic__author__username=author,
                                                                            heuristic__name=name,
                                                                            version=version))

            inModel.close()
        except Exception, e:
            log_message = traceback.format_exc()
            job.outStream.write(log_message + "\n")



def tasks():
    return [ExperimentLauncher]
