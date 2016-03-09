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
from utilities.logs import getServerLogs
from pymash import Message
from django.conf import settings
from heuristics.models import Heuristic
from heuristics.models import HeuristicVersion
from heuristics.models import HeuristicEvaluationResults
from heuristics.models import HeuristicSignature
from experiments.models import Experiment
from experiments.models import Configuration
from servers.models import Alert
from servers.models import Job as ServerJob
from datetime import datetime
import os
import traceback


#-------------------------------------------------------------------------------
# This task tries to compile and test a heuristic
#-------------------------------------------------------------------------------
class ExperimentScheduler(Task):

    SUPPORTED_COMMANDS = { 'SCHEDULE_PUBLIC_EXPERIMENTS': [],
                           'SCHEDULE_HEURISTIC_EVALUATION': [int],  # <heuristic_version_id>
                           'EVALUATE_ALL_HEURISTICS': [],
                           'SCHEDULE_HEURISTIC_SIGNATURE_RECORDING': [int],  # <heuristic_version_id>
                           'RECORD_ALL_HEURISTIC_SIGNATURES': [],
                         }

    SUPPORTED_EVENTS   = { 'EVT_HEURISTIC_CHECKED': [int],          # <heuristic_version_id>
                           'EVT_PUBLIC_EXPERIMENT_DONE': [int],     # <experiment_id>
                           'EVT_PUBLIC_EXPERIMENT_FAILED': [int],   # <experiment_id>
                           'EVT_EXPERIMENT_CANCELLED': [int],       # <experiment_id>
                         }


    #---------------------------------------------------------------------------
    # Called when a new command was received. It allows the task to process it
    # independently of the jobs mechanism.
    #
    # @param    command     The command
    # @return               'False' if the command must be handled by the
    #                       standard jobs mechanism
    #---------------------------------------------------------------------------
    def onCommandReceived(self, command):
        if command.name == 'SCHEDULE_PUBLIC_EXPERIMENTS':
            jobs = self.jobs.getJobs(command=command)
            if len(jobs) == 0:
                return False

            if jobs[0].server_job.status == ServerJob.STATUS_DELAYED:
                jobs[0].timeout = 0

            return True

        elif command.name == 'EVALUATE_ALL_HEURISTICS':
            for heuristic_version in HeuristicVersion.objects.filter(checked=True, status=HeuristicVersion.STATUS_OK, heuristic__simple=False):
                job = self.jobs.addJob(command=Message('SCHEDULE_HEURISTIC_EVALUATION', [heuristic_version.id]))
                self.new_jobs.append(job)
            return True

        elif command.name == 'RECORD_ALL_HEURISTIC_SIGNATURES':
            for heuristic_version in HeuristicVersion.objects.filter(checked=True, status=HeuristicVersion.STATUS_OK, heuristic__simple=False):
                job = self.jobs.addJob(command=Message('SCHEDULE_HEURISTIC_SIGNATURE_RECORDING', [heuristic_version.id]))
                self.new_jobs.append(job)
            return True

        return False


    #---------------------------------------------------------------------------
    # Called when a new event was received
    #
    # @param event  The event
    # @return       None, or a new job (already in the jobs list)
    #---------------------------------------------------------------------------
    def onEventReceived(self, event):
        if event.name == 'EVT_HEURISTIC_CHECKED':
            heuristic_version = HeuristicVersion.objects.get(id=event.parameters[0])
            if heuristic_version.heuristic.simple:
                return None

            job1 = self.jobs.addJob(command=Message('SCHEDULE_HEURISTIC_EVALUATION', event.parameters))
            job2 = self.jobs.addJob(command=Message('SCHEDULE_HEURISTIC_SIGNATURE_RECORDING', event.parameters))
            return [job1, job2]

        if (event.name == 'EVT_PUBLIC_EXPERIMENT_DONE') or (event.name == 'EVT_PUBLIC_EXPERIMENT_FAILED'):
            job = self.jobs.addJob(command=Message('SCHEDULE_PUBLIC_EXPERIMENTS'))
            return [job]

        if event.name == 'EVT_EXPERIMENT_CANCELLED':
            try:
                experiment = Experiment.objects.get(id=event.parameters[0])

                job = None
                if experiment.configuration.experiment_type == Configuration.PUBLIC:
                    job = self.jobs.addJob(command=Message('SCHEDULE_PUBLIC_EXPERIMENTS'))
                elif experiment.configuration.experiment_type == Configuration.EVALUATION:
                    evaluation_results = experiment.evaluation_results
                    heuristic_version = evaluation_results.heuristic_version
                    evaluation_results.delete()

                    if (heuristic_version.evaluation_results.count() == 0) and \
                       (heuristic_version.status == HeuristicVersion.STATUS_OK):
                        job = self.jobs.addJob(command=Message('SCHEDULE_HEURISTIC_EVALUATION', [heuristic_version.id]))
                elif experiment.configuration.experiment_type == Configuration.SIGNATURE:
                    signature = experiment.signature
                    heuristic_version = signature.heuristic_version
                    signature.delete()

                    if heuristic_version.status == HeuristicVersion.STATUS_OK:
                        job = self.jobs.addJob(command=Message('SCHEDULE_HEURISTIC_SIGNATURE_RECORDING', [heuristic_version.id]))

                experiment.configuration.delete()

                if job is None :
                    return None
                else:
                    return [job]
            except:
                return None

        return None


    #---------------------------------------------------------------------------
    # Starts the job-specific processing
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def process(self, job):
        if job.command.name == 'SCHEDULE_PUBLIC_EXPERIMENTS':
            self.schedulePublicExperiments(job)
        elif job.command.name == 'SCHEDULE_HEURISTIC_EVALUATION':
            self.scheduleHeuristicEvaluation(job)
        elif job.command.name == 'SCHEDULE_HEURISTIC_SIGNATURE_RECORDING':
            self.scheduleHeuristicSignatureRecording(job)


    #---------------------------------------------------------------------------
    # Method called at startup. Use it to look in the database if there is some
    # job already waiting. They must be put in the job list.
    #---------------------------------------------------------------------------
    def onStartup(self):
        self.jobs.addJob(command=Message('SCHEDULE_PUBLIC_EXPERIMENTS'))

        for version in HeuristicVersion.objects.filter(evaluated=False, checked=True, status=HeuristicVersion.STATUS_OK, heuristic__simple=False):
            self.jobs.addJob(command=Message('SCHEDULE_HEURISTIC_EVALUATION', [version.id]))

        for version in HeuristicVersion.objects.filter(checked=True, status=HeuristicVersion.STATUS_OK, signature__isnull=True, heuristic__simple=False):
            self.jobs.addJob(command=Message('SCHEDULE_HEURISTIC_SIGNATURE_RECORDING', [version.id]))


    #---------------------------------------------------------------------------
    # Schedule the new needed public experiments
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def schedulePublicExperiments(self, job):

        job.markAsRunning()

        # Retrieve the configuration templates
        for template in Configuration.objects.filter(experiment_type=Configuration.PUBLIC, name__startswith='template/'):

            # Retrieve the list of heuristic versions already used in a public experiment
            # based on this template
            already_used_heuristic_versions = []
            previous = None
            try:
                previous = Configuration.objects.filter(experiment_type=Configuration.PUBLIC,
                                                        name__startswith=template.name.replace('template/', '')).order_by('-experiment__creation_date')[0]

                if previous.experiment.status == Experiment.STATUS_RUNNING:
                    continue

                already_used_heuristic_versions = list(previous.heuristics_set.all())
            except:
                pass

            # Ensure that some new heuristics exist since the last public experiment
            # based on this template
            current_heuristic_versions = map(lambda x: x.latest_public_version,
                                              list(Heuristic.objects.filter(latest_public_version__isnull=False, simple=False)))

            new_heuristic_versions = filter(lambda x: x not in already_used_heuristic_versions, current_heuristic_versions)

            if len(new_heuristic_versions) == 0:
                continue

            # Cancel the previous experiment if needed
            if (previous is not None) and (previous.experiment.status == Experiment.STATUS_SCHEDULED):
                self.channel.sendMessage(Message('CANCEL_EXPERIMENT', [previous.experiment.id]))
                continue

            # Create the configuration
            configuration                 = Configuration()
            configuration.name            = template.name.replace('template/', '') + '/' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            configuration.heuristics      = template.heuristics
            configuration.experiment_type = template.experiment_type
            configuration.task            = template.task
            configuration.save()

            # Add the list of heuristic versions
            for heuristic_version in current_heuristic_versions:
                configuration.heuristics_set.add(heuristic_version)

            # Add the list of instruments
            for instrument in template.instruments_set.all():
                configuration.instruments_set.add(instrument)

            # Save the configuration
            configuration.save()

            # Add the settings
            for setting in template.settings.all():
                configuration.addSetting(setting.name, setting.value)

            # Create the experiment
            experiment               = Experiment()
            experiment.name          = configuration.name
            experiment.configuration = configuration
            experiment.save()

            self.channel.sendMessage(Message('RUN_EXPERIMENT', [experiment.id]))

        job.markAsDone()


    #---------------------------------------------------------------------------
    # Schedule all the experiments needed to evaluate a heuristic version
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def scheduleHeuristicEvaluation(self, job):

        # Retrieve the heuristic version
        try:
            heuristic_version = HeuristicVersion.objects.get(id=job.command.parameters[0])
        except:
            alert = Alert()
            alert.message = 'Unknown heuristic version ID: %d' % job.command.parameters[0]
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            return

        job.markAsRunning()

        # If the heuristic is already evaluated, remove the results from the database
        if heuristic_version.evaluated:
            configurations = map(lambda x: x.experiment.configuration, heuristic_version.evaluation_results.all())

            heuristic_version.evaluation_results.all().delete()
            heuristic_version.evaluated = False
            heuristic_version.rank = None
            heuristic_version.save()

            for configuration in configurations:
                configuration.delete()

        # If the heuristic is currently evaluated, remove the existing results from
        # the database and cancel the running experiments
        elif heuristic_version.evaluation_results.count() > 0:
            for evaluation_results in heuristic_version.evaluation_results.filter(experiment__status=Experiment.STATUS_RUNNING):
                self.channel.sendMessage(Message('CANCEL_EXPERIMENT', [evaluation_results.experiment.id]))

            configurations = map(lambda x: x.experiment.configuration, heuristic_version.evaluation_results.exclude(experiment__status=Experiment.STATUS_RUNNING))
            heuristic_version.evaluation_results.exclude(experiment__status=Experiment.STATUS_RUNNING).delete()

            for configuration in configurations:
                configuration.delete()

            job.markAsDone()
            return

        # Retrieve all the evaluation configurations
        evaluation_configurations = Configuration.objects.filter(experiment_type=Configuration.EVALUATION,
                                                                 name__startswith='template/')
        if evaluation_configurations.count() == 0:
            alert = Alert()
            alert.message = 'No evaluation configuration found'
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            return

        # Schedule the evaluation experiments
        for evaluation_configuration in evaluation_configurations:

            # Create the configuration
            configuration                 = Configuration()
            configuration.name            = evaluation_configuration.name.replace('template/', '%s/' % heuristic_version.fullname())
            configuration.heuristics      = evaluation_configuration.heuristics
            configuration.experiment_type = evaluation_configuration.experiment_type
            configuration.task            = evaluation_configuration.task
            configuration.save()

            # Add the list of heuristic versions
            for version in evaluation_configuration.heuristics_set.all():
                configuration.heuristics_set.add(version)

            if heuristic_version not in evaluation_configuration.heuristics_set.all():
                configuration.heuristics_set.add(heuristic_version)
            else:
                configuration.addSetting('PREDICTOR_SETUP/ADDITIONAL_HEURISTICS', heuristic_version.absolutename())

            # Add the list of instruments
            for instrument in evaluation_configuration.instruments_set.all():
                configuration.instruments_set.add(instrument)

            # Save the configuration
            configuration.save()

            # Add the settings
            for setting in evaluation_configuration.settings.all():
                configuration.addSetting(setting.name, setting.value)

            # Create the experiment
            experiment               = Experiment()
            experiment.name          = configuration.name
            experiment.configuration = configuration
            experiment.save()

            # Create the evaluation results entry
            evaluation_results                   = HeuristicEvaluationResults()
            evaluation_results.heuristic_version = heuristic_version
            evaluation_results.evaluation_config = evaluation_configuration
            evaluation_results.experiment        = experiment
            evaluation_results.save()

            self.channel.sendMessage(Message('RUN_EXPERIMENT', [experiment.id]))

        job.markAsDone()


    #---------------------------------------------------------------------------
    # Schedule the experiment needed to record the signature of a heuristic
    # version
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def scheduleHeuristicSignatureRecording(self, job):

        # Retrieve the heuristic version
        try:
            heuristic_version = HeuristicVersion.objects.get(id=job.command.parameters[0])
        except:
            alert = Alert()
            alert.message = 'Unknown heuristic version ID: %d' % job.command.parameters[0]
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            return

        job.markAsRunning()

        # If the heuristic already has a signature, delete it
        try:
            signature = heuristic_version.signature[0]
        except:
            signature = None

        if signature is not None:
            if signature.experiment.isRunning() or signature.experiment.isScheduled:
                self.channel.sendMessage(Message('CANCEL_EXPERIMENT', [signature.experiment.id]))
                job.markAsDone()
                return

            signature.experiment.configuration.delete()
            signature.delete()

        # Retrieve the recording configuration
        try:
            configuration_template = Configuration.objects.get(experiment_type=Configuration.SIGNATURE,
                                                               name__startswith='template/')
        except:
            alert = Alert()
            alert.message = 'No signature recording configuration found'
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            return

        # Create the configuration
        configuration                 = Configuration()
        configuration.name            = configuration_template.name.replace('template/', '%s/' % heuristic_version.fullname())
        configuration.heuristics      = configuration_template.heuristics
        configuration.experiment_type = configuration_template.experiment_type
        configuration.task            = configuration_template.task
        configuration.save()

        # Add the heuristic version
        configuration.heuristics_set.add(heuristic_version)

        # Save the configuration
        configuration.save()

        # Add the settings
        for setting in configuration_template.settings.all():
            configuration.addSetting(setting.name, setting.value)

        # Create the experiment
        experiment               = Experiment()
        experiment.name          = configuration.name
        experiment.configuration = configuration
        experiment.save()

        # Create the signature
        signature                   = HeuristicSignature()
        signature.heuristic_version = heuristic_version
        signature.experiment        = experiment
        signature.save()

        self.channel.sendMessage(Message('RUN_EXPERIMENT', [experiment.id]))

        job.markAsDone()


def tasks():
    return [ExperimentScheduler]
