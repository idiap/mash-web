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
from heuristics.models import HeuristicVersion
from heuristics.models import HeuristicEvaluationResults
from experiments.models import Experiment
from experiments.models import Configuration
from contests.models import ContestEntry
from pymash.messages import Message
from django.db.models import Q
import math


def compare_evaluation_results(x, y):
    if x[1] < y[1]:
        return -1
    elif x[1] > y[1]:
        return 1
    else:
        if x[2] < y[2]:
            return -1
        elif x[2] > y[2]:
            return 1
        else:
            return  0


class RankingHelper:

    def __init__(self, heuristic_version, modifiable=False):
        self.heuristic_version = heuristic_version
        self.score             = 0.0
        self.error_rate        = 0.0
        self.modifiable        = modifiable

    def setup(self, evaluation_config):
        self.error_rate = self.heuristic_version.evaluation_results.get(evaluation_config=evaluation_config).mean_test_error()

    def updateScore(self, score):
        self.score += score


#-------------------------------------------------------------------------------
# This task computes the ranking of the heuristic versions
#-------------------------------------------------------------------------------
class HeuristicRanker(Task):

    SUPPORTED_COMMANDS = { 'RANK_EVALUATED_HEURISTICS': [],
                           'RANK_HEURISTIC_VERSION': [int],     # <heuristic_version_id>
                           'RANK_CONTEST_ENTRIES': [int],       # <contest_id>
                         }

    SUPPORTED_EVENTS   = { 'EVT_HEURISTIC_EVALUATED': [int],    # <heuristic_version_id>
                         }


    #---------------------------------------------------------------------------
    # Starts the job-specific processing
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def process(self, job):
        if job.command.name == 'RANK_EVALUATED_HEURISTICS':
            self.rankEvaluatedHeuristics(job)
        elif job.command.name == 'RANK_HEURISTIC_VERSION':
            self.rankHeuristicVersion(job)
        elif job.command.name == 'RANK_CONTEST_ENTRIES':
            self.rankContestEntries(job)


    #---------------------------------------------------------------------------
    # Called when a new event was received
    #
    # @param event  The event
    # @return       None, or a new job (already in the jobs list)
    #---------------------------------------------------------------------------
    def onEventReceived(self, event):
        if event.name == 'EVT_HEURISTIC_EVALUATED':
            job = self.jobs.addJob(command=Message('RANK_HEURISTIC_VERSION', event.parameters))
            return [job]

        return None


    #---------------------------------------------------------------------------
    # Compute the ranking of all the evaluated heuristics
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def rankEvaluatedHeuristics(self, job):

        job.markAsRunning()

        # Reset all the ranks
        for evaluation_results in HeuristicEvaluationResults.objects.all():
            evaluation_results.rank = None
            evaluation_results.save()
            evaluation_results.heuristic_version.rank = None
            evaluation_results.heuristic_version.save()

        # Retrieve all the evaluation configurations
        evaluation_configurations = Configuration.objects.filter(experiment_type=Configuration.EVALUATION,
                                                                 name__startswith='template/')

        # Retrieve all the public heuristic versions completely evaluated
        public_heuristic_versions = filter(lambda x: x.heuristic.latest_public_version.id == x.id,
                                           HeuristicVersion.objects.filter(public=True, evaluated=True))

        # Compute the ranking for each configuration of the public heuristic versions
        for configuration in evaluation_configurations:

            configuration_evaluation_results = []
            for heuristic_version in public_heuristic_versions:
                configuration_evaluation_results.extend(map(lambda x: (x, x.mean_test_error(), x.mean_train_error()),
                                                            heuristic_version.evaluation_results.filter(evaluation_config=configuration)))

            configuration_evaluation_results.sort(cmp=compare_evaluation_results)

            for index, evaluation_results in enumerate(map(lambda x: x[0], configuration_evaluation_results)):
                evaluation_results.rank = index + 1
                evaluation_results.save()

        # Compute the global ranking of the public heuristic versions
        to_rank = map(lambda x: RankingHelper(x, True), public_heuristic_versions)
        self._computeGlobalRanking(to_rank, evaluation_configurations)

        # Compute the ranking for each configuration of the remaining heuristic versions
        for configuration in evaluation_configurations:
            evaluation_results = HeuristicEvaluationResults.objects.filter(
                                                            experiment__status=Experiment.STATUS_DONE,
                                                            evaluation_config=configuration,
                                                            rank__isnull=True)

            ranked_evaluation_results = map(lambda x: (x, x.mean_test_error(), x.mean_train_error()),
                                            filter(lambda x: x.heuristic_version.heuristic.latest_public_version.id == x.heuristic_version.id,
                                                   HeuristicEvaluationResults.objects.filter(
                                                            experiment__status=Experiment.STATUS_DONE,
                                                            evaluation_config=configuration,
                                                            rank__isnull=False,
                                                            heuristic_version__public=True).order_by('rank')))

            for current_evaluation_results in evaluation_results:
                mean_test_error = current_evaluation_results.mean_test_error()
                mean_train_error = current_evaluation_results.mean_train_error()

                current_evaluation_results.rank = self._rankElement(mean_test_error, mean_train_error,
                                                                    ranked_evaluation_results)
                current_evaluation_results.save()

        # Compute the global ranking of the remaining heuristic versions
        heuristic_versions = HeuristicVersion.objects.filter(rank__isnull=True, evaluated=True)
        for heuristic_version in heuristic_versions:
            to_rank = map(lambda x: RankingHelper(x, False), public_heuristic_versions)
            to_rank.append(RankingHelper(heuristic_version, True))
            self._computeGlobalRanking(to_rank, evaluation_configurations)

        job.markAsDone()


    #---------------------------------------------------------------------------
    # Compute the ranking of a specific heuristic version
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def rankHeuristicVersion(self, job):

        # Retrieve the heuristic version
        try:
            heuristic_version = HeuristicVersion.objects.get(id=job.command.parameters[0])
        except:
            alert = Alert()
            alert.message = 'Unknown heuristic version ID: %d\n' % job.command.parameters[0]
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            return

        # Determine if the heuristic is fully evaluated or not
        heuristic_version.evaluated = (heuristic_version.evaluation_results.filter(experiment__status=Experiment.STATUS_DONE).count() == heuristic_version.evaluation_results.count())
        heuristic_version.save()

        # First check if we should not recompute all the rankings instead
        if heuristic_version.public:
            self.rankEvaluatedHeuristics(job)
            return

        job.markAsRunning()

        # Retrieve all the complete evaluation results not ranked yet
        evaluation_results_to_rank = heuristic_version.evaluation_results.filter(
                                            experiment__status=Experiment.STATUS_DONE,
                                            rank__isnull=True)

        for evaluation_results in evaluation_results_to_rank:
            ranked_evaluation_results = map(lambda x: (x, x.mean_test_error(), x.mean_train_error()),
                                            filter(lambda x: x.heuristic_version.heuristic.latest_public_version.id == x.heuristic_version.id,
                                                   HeuristicEvaluationResults.objects.filter(
                                                            experiment__status=Experiment.STATUS_DONE,
                                                            evaluation_config=evaluation_results.evaluation_config,
                                                            rank__isnull=False,
                                                            heuristic_version__public=True).order_by('rank')))

            evaluation_results.rank = self._rankElement(evaluation_results.mean_test_error(),
                                                        evaluation_results.mean_train_error(),
                                                        ranked_evaluation_results)
            evaluation_results.save()

        # Compute the global ranking if possible
        if heuristic_version.evaluated:
            to_rank = map(lambda x: RankingHelper(x, False),
                          filter(lambda x: x.heuristic.latest_public_version.id == x.id,
                                 HeuristicVersion.objects.filter(rank__isnull=False, public=True)))

            evaluated_heuristic_version = RankingHelper(heuristic_version, True)
            to_rank.append(evaluated_heuristic_version)

            self._computeGlobalRanking(to_rank, map(lambda x: x.evaluation_config, heuristic_version.evaluation_results.iterator()))

        job.markAsDone()


    #---------------------------------------------------------------------------
    # Compute the ranking of the entries of a contest
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def rankContestEntries(self, job):

        def rank(project_member):
            # Retrieve all the contest entries where the experiment is done
            entries = ContestEntry.objects.filter(contest__id=job.command.parameters[0]).filter(
                                                    Q(experiment__status=Experiment.STATUS_DONE) |
                                                    Q(experiment__status=Experiment.STATUS_DONE_WITH_ERRORS))

	    entries = filter(lambda x: x.heuristic_version.heuristic.author.get_profile().project_member == project_member, entries)

            # Reset all the ranks
            for entry in entries:
                entry.rank = None
                entry.save()

            # Compute the global ranking
            entries_to_rank = map(self._contestEntryToTuple, entries)
            entries_to_rank.sort(cmp=compare_evaluation_results)

            for index, entry in enumerate(map(lambda x: x[0], entries_to_rank)):
                entry.rank = index + 1
                entry.save()

        job.markAsRunning()

        rank(True)
        rank(False)

        job.markAsDone()


    def _computeGlobalRanking(self, to_rank, evaluation_configurations):
        if len(to_rank) == 0:
            return

        for evaluation_config in evaluation_configurations:

            [ x.setup(evaluation_config) for x in to_rank ]

            l = map(lambda x: x.error_rate, to_rank)

            errors_sum = sum(l)
            errors_squared_sum = reduce(lambda x, y: x + y**2, l, 0.0)

            mean = errors_sum / len(l)
            variance = (errors_squared_sum - errors_sum * mean) / (len(l) - 1)
            standard_deviation = math.sqrt(variance)

            [ x.updateScore((-x.error_rate + mean) / standard_deviation) for x in to_rank ]

        to_rank.sort(lambda x, y: cmp(y.score, x.score))

        for (index, x) in enumerate(to_rank):
            if x.modifiable:
                x.heuristic_version.rank = index + 1
                x.heuristic_version.save()


    def _rankElement(self, mean_test_error, mean_train_error, ranked_list):
        for current_ranked in ranked_list:
            if (mean_test_error < current_ranked[1]) or \
               (not(mean_test_error > current_ranked[1]) and (mean_train_error < current_ranked[2])):
                return current_ranked[0].rank

        return len(ranked_list) + 1


    def _contestEntryToTuple(self, contest_entry):
        return (contest_entry, contest_entry.experiment.classification_results.test_error,
                contest_entry.experiment.classification_results.train_error)



def tasks():
    return [HeuristicRanker]
