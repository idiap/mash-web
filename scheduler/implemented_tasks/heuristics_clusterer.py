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
from pymash import Client
from pymash import Message
from django.conf import settings
from django.template import defaultfilters
from django.core.files import locks
from servers.models import Server
from servers.models import Alert
from heuristics.models import HeuristicVersion
from heuristics.models import HeuristicSignature
from experiments.models import Experiment
from clustering.models import Algorithm, SignatureStatus
import os
import tarfile


#-------------------------------------------------------------------------------
# This task performs clustering of the heuristics
#-------------------------------------------------------------------------------
class HeuristicsClusterer(Task):

    SUPPORTED_COMMANDS = { 'CLUSTER_HEURISTICS': [str] }
    SUPPORTED_EVENTS   = { 'EVT_HEURISTIC_SIGNATURE_RECORDED': [int] }


    #---------------------------------------------------------------------------
    # Called when a new command was received. It allows the task to process it
    # independently of the jobs mechanism.
    #
    # @param    command     The command
    # @return               'False' if the command must be handled by the
    #                       standard jobs mechanism
    #---------------------------------------------------------------------------
    def onCommandReceived(self, command):
        return self.jobs.hasJob(command)


    #---------------------------------------------------------------------------
    # Called when a new event was received
    #
    # @param event  The event
    # @return       None, or a new job (already in the jobs list)
    #---------------------------------------------------------------------------
    def onEventReceived(self, event):
        if self.jobs.count() > 0:
            return None

        if event.name == 'EVT_HEURISTIC_SIGNATURE_RECORDED':
            jobs = []

            algorithms = Algorithm.objects.all()
            for algorithm in algorithms:
                jobs.append(self.jobs.addJob(command=Message('CLUSTER_HEURISTICS', [algorithm.name])))

            return jobs

        return None


    #---------------------------------------------------------------------------
    # Starts the job-specific processing
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def process(self, job):

        job.markAsRunning()

        try:
            algorithm = Algorithm.objects.get(name=job.command.parameters[0])

            signatures = HeuristicSignature.objects.filter(experiment__status=Experiment.STATUS_DONE)

            missing_status = filter(lambda x: x.status.filter(algorithm=algorithm).count() == 0, signatures)

            for missing in missing_status:
                status = SignatureStatus()
                status.algorithm = algorithm
                status.signature = missing
                status.processed = False
                status.save()
        except:
            pass

        # Retrieve the heuristic signatures not already processed
        signatures_status = SignatureStatus.objects.filter(signature__experiment__status=Experiment.STATUS_DONE,
                                                           algorithm__name=job.command.parameters[0], processed=False)
        
        if signatures_status.count() == 0:
            job.markAsDone()
            return

        # Search a free Clustering Server
        job.outStream.write("Searching a free Clustering Server with the algorithm '%s'...\n" % job.command.parameters[0])
        
        servers = Server.objects.filter(server_type=Server.CLUSTERING_SERVER, clustering_algorithm__name=job.command.parameters[0])
        for server in filter(lambda x: x.current_job() is None, servers):
            job.outStream.write("    Contacting '%s:%d'...\n" % (server.address, server.port))

            job.client = Client(outStream = job.outStream)
            if job.client.connect(server.address, server.port):
                job.client.sendCommand('STATUS')
                response = job.client.waitResponse()
                if response.name == 'READY':
                    job.outStream.write("    Clustering Server found\n")
                    job.markAsRunning(server=server)
                    break
            
            job.client.close()
            del job.client
            job.client = None

        if job.client is None:
            job.outStream.write("Failed to find a free Clustering Server\n")
            job.markAsDelayed(60)
            return
        
        # Tell the server about the signatures
        job.signatures_status = signatures_status
        job.sent_signatures = []
        self.sendNextSignature(job)


    #---------------------------------------------------------------------------
    # Send the next signature to the Server
    #---------------------------------------------------------------------------
    def sendNextSignature(self, job):
        
        if len(job.sent_signatures) > 0:
            response = job.client.waitResponse()
            if response.name != 'OK':
                alert = Alert()
                alert.message = 'Failed to send a signature'
                alert.details = "Signature: %s\nResponse: %s" % (job.sent_signatures[-1].signature.heuristic_version.absolutename(),
                                                                 response.toString())
                job.outStream.write("ERROR - %s\n" % alert.message)
                job.outStream.write("        %s\n" % alert.details)

                job.server_job.logs = getServerLogs(job.client)
                job.server_job.save()

                job.markAsFailed(alert=alert)
                return

        # Send the next signature
        signatures_status = job.signatures_status[0]
        job.signatures_status = job.signatures_status[1:]
        job.sent_signatures.append(signatures_status)
        job.outStream.write("Send the signature of heuristic '%s'...\n" % signatures_status.signature.heuristic_version.absolutename())

        try:
            tar = tarfile.open(os.path.join(settings.DATA_REPORTS_ROOT, signatures_status.signature.experiment.data_report.filename), 'r:gz')
            signature_file = tar.extractfile('predictor.data')
            content = signature_file.read()
            signature_file.close()
            tar.close()
        except:
            alert = Alert()
            alert.message = "Failed to extract the signature of '%s'" % signatures_status.signature.heuristic_version.absolutename()
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            return


        if not(job.client.sendCommand(Message('ADD_SIGNATURE', [defaultfilters.slugify(signatures_status.signature.heuristic_version.absolutename()), len(content)]))):
            alert = Alert()
            alert.message = "Failed to tell the server about the signature of '%s'" % signatures_status.signature.heuristic_version.absolutename()
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        if not(job.client.sendData(content)):
            alert = Alert()
            alert.message = "Failed to send the signature of '%s' to the server" % signatures_status.signature.heuristic_version.absolutename()
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        if len(job.signatures_status) > 0:
            job.operation = HeuristicsClusterer.sendNextSignature
        else:
            job.operation = HeuristicsClusterer.performClustering


    #---------------------------------------------------------------------------
    # Perform the clustering
    #---------------------------------------------------------------------------
    def performClustering(self, job):
        response = job.client.waitResponse()
        if response.name != 'OK':
            alert = Alert()
            alert.message = 'Failed to send a signature'
            alert.details = "Signature: %s\nResponse: %s" % (job.sent_signatures[-1].signature.heuristic_version.absolutename(),
                                                             response.toString())
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.outStream.write("        %s\n" % alert.details)

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        job.outStream.write("All signatures correctly sent\n")

        # Perform the clustering
        if not(job.client.sendCommand(Message('CLUSTER'))):
            alert = Alert()
            alert.message = "Failed to tell the server to perform the clustering"
            job.outStream.write("ERROR - %s\n" % alert.message)

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        job.operation = HeuristicsClusterer.processClusteringResults


    #---------------------------------------------------------------------------
    # Process the results of the clustering
    #---------------------------------------------------------------------------
    def processClusteringResults(self, job):
        response = job.client.waitResponse()
        if response.name != 'RESULTS':
            alert = Alert()
            alert.message = 'Failed to perform the clustering'
            alert.details = "Response: %s" % response.toString()
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.outStream.write("        %s\n" % alert.details)

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        job.outStream.write("Clustering done, retrieving the results...\n")

        filesize = int(response.parameters[0])
        content = job.client.waitData(filesize)
        if content is None:
            alert = Alert()
            alert.message = 'Failed to retrieve the results of the clustering'
            alert.details = "Response: %s" % response.toString()
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.outStream.write("        %s\n" % alert.details)

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        job.client.sendCommand('DONE')
        job.client.close()
        del job.client
        job.client = None

        # Mark the signatures as processed
        for signature in job.sent_signatures:
            signature.processed = True
            signature.save()

        # Save the results of the clustering
        if not(os.path.exists(os.path.join(settings.SNIPPETS_ROOT, 'clustering'))):
            os.makedirs(os.path.join(settings.SNIPPETS_ROOT, 'clustering'))

        filename = '%s.dat.tmp' % job.command.parameters[0]

        f = open(os.path.join(settings.SNIPPETS_ROOT, 'clustering', filename), 'w')
        f.write(content)
        f.close()
        
        # Lock the snippets folder
        filename = os.path.join(settings.SNIPPETS_ROOT, 'snippets.lock')
        lock_file = open(filename, 'wb')
        try:
            os.chmod(filename, 0766)
        except:
            pass
        locks.lock(lock_file, locks.LOCK_EX)
        
        # Update the clustering results file used by the website
        os.rename(os.path.join(settings.SNIPPETS_ROOT, 'clustering', filename),
                  os.path.join(settings.SNIPPETS_ROOT, 'clustering', filename[:-4]))
        
        # Unlock the snippets folder
        locks.unlock(lock_file)
        
        # Mark the job as done
        job.markAsDone()

        # Test if another clustering must start
        signatures_status = SignatureStatus.objects.filter(signature__experiment__status=Experiment.STATUS_DONE,
                                                           algorithm__name=job.command.parameters[0], processed=False)
        if signatures_status.count() > 0:
            self.channel.sendMessage(Message('CLUSTER_HEURISTICS', job.command.parameters))
        
        # Send an event about the end of the clustering
        self.channel.sendMessage(Message('EVT_HEURISTICS_CLUSTERING_DONE', job.command.parameters))


    #---------------------------------------------------------------------------
    # Method called at startup. Use it to look in the database if there is some
    # job already waiting. They must be put in the job list.
    #---------------------------------------------------------------------------
    def onStartup(self):
        algorithms = Algorithm.objects.all()
        for algorithm in algorithms:
            signatures = HeuristicSignature.objects.filter(experiment__status=Experiment.STATUS_DONE)

            signatures_status = SignatureStatus.objects.filter(signature__experiment__status=Experiment.STATUS_DONE,
                                                               algorithm__name=algorithm.name, processed=True)

            if signatures.count() > signatures_status.count():
                self.jobs.addJob(command=Message('CLUSTER_HEURISTICS', [algorithm.name]))


def tasks():
    return [HeuristicsClusterer]
