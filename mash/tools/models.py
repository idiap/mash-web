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


from django.db import models
from django.conf import settings
from mash.heuristics.models import HeuristicVersion
from classifiers.models import Classifier
from goalplanners.models import Goalplanner
from instruments.models import Instrument
from mash.experiments.models import Experiment
from mash.experiments.models import Configuration
import re


class PluginErrorReport(models.Model):

    ERROR_CRASH      = 'C'
    ERROR_TIMEOUT    = 'T'
    ERROR_OTHER      = 'E'

    ERROR_TYPES = (
        (ERROR_CRASH,   'Crash'),
        (ERROR_TIMEOUT, 'Timeout'),
        (ERROR_OTHER,   'Other'),
    )

    heuristic_version   = models.ForeignKey(HeuristicVersion, related_name='error_reports', null=True, blank=True)
    classifier          = models.ForeignKey(Classifier, related_name='error_reports', null=True, blank=True)
    goalplanner         = models.ForeignKey(Goalplanner, related_name='error_reports', null=True, blank=True)
    instrument          = models.ForeignKey(Instrument, related_name='error_reports', null=True, blank=True)
    experiment          = models.ForeignKey(Experiment, related_name='error_reports', null=True, blank=True)
    error_type          = models.CharField(max_length=1, choices=ERROR_TYPES)
    description         = models.TextField(blank=True)
    context             = models.TextField(blank=True)
    stacktrace          = models.TextField(blank=True)

    
    def __unicode__(self):
        text = self.title()
        
        if self.experiment is not None:
            text += " in experiment '%s'" % self.experiment.fullname()
        
        return text
    

    def title(self):
        if self.heuristic_version is not None:
            return "Error report for heuristic '%s'" % self.heuristic_version.fullname()
        elif self.classifier is not None:
            return "Error report for classifier '%s'" % self.classifier.fullname()
        elif self.goalplanner is not None:
            return "Error report for goal-planner '%s'" % self.goalplanner.fullname()
        elif self.instrument is not None:
            return "Error report for instrument '%s'" % self.instrument.fullname()

        return "Error report #%d" % self.id


    def problemDescription(self):
        if self.error_type == PluginErrorReport.ERROR_CRASH:
            if self.heuristic_version is not None:
                return 'The heuristic crashed!'
            elif self.classifier is not None:
                return 'The classifier crashed!'
            elif self.goalplanner is not None:
                return 'The goal-planner crashed!'
            elif self.instrument is not None:
                return 'The instrument crashed!'
            else:
                return 'A crash happened!'
        
        elif self.error_type == PluginErrorReport.ERROR_TIMEOUT:
            return 'The heuristic took too much computation time!'

        else:
            return self.description


    def is_crash(self):
        return (self.error_type == PluginErrorReport.ERROR_CRASH)


    def is_timeout(self):
        return (self.error_type == PluginErrorReport.ERROR_TIMEOUT)


    def splitStacktrace(self):
        if len(self.stacktrace) == 0:
            return []

        stacktrace = self.stacktrace.replace(u'\r\n', u'\n')

        parts = []

        regex = re.compile(u'^#', flags=re.MULTILINE | re.UNICODE)
        frames = map(lambda x: '#' + x, filter(lambda x: len(x) > 0, regex.split(stacktrace)))

        regex_first_line = re.compile(u'^(.+)$', flags=re.MULTILINE | re.UNICODE)
        regex_line_number = re.compile(u':(\d+)$', flags=re.UNICODE)
        for frame in frames:
            if frame.endswith('\n'):
                frame = frame[0:-1]

            match = regex_first_line.search(frame)

            frame_header = match.group(1)
            code = frame[match.end() + 1:]

            line_number = regex_line_number.search(frame_header).group(1)

            parts.append(('frame', frame_header))

            regex_error_line = re.compile(u'^%s\s' % line_number, flags=re.MULTILINE | re.UNICODE)
            match = regex_error_line.search(code)

            if match:
                if match.start() > 0:
                    parts.append(('code', '  ' + '\n  '.join(code[0:match.start() - 1].split(u'\n'))))

                match2 = regex_first_line.search(code[match.start():])
                parts.append(('error', '  ' + match2.group(1)))

                last_part = '  ' + '\n  '.join(code[match.start() + match2.end() + 1:].split(u'\n'))

                if len(last_part) > 0:
                    parts.append(('code', last_part))
            else:
                parts.append(('code', code))

        return parts


    def send_mail(self):

        # Check that the error is something we want to notify by e-mail
        if self.error_type == PluginErrorReport.ERROR_OTHER:
            return False

        # Retrieve the person to notify, and the name and type of the plugin
        if self.heuristic_version is not None:
            author = self.heuristic_version.heuristic.author
            plugin_name = self.heuristic_version.shortname()
            plugin_type = 'heuristic'
        elif self.classifier is not None:
            author = self.classifier.author
            plugin_name = self.classifier.name
            plugin_type = 'classifier'
        elif self.goalplanner is not None:
            author = self.goalplanner.author
            plugin_name = self.goalplanner.name
            plugin_type = 'goal-planner'
        elif self.instrument is not None:
            author = self.instrument.author
            plugin_name = self.instrument.name
            plugin_type = 'instrument'
        else:
            return False

        # Compose the mail
        mail_subject = None
        mail_content = ''

        if self.error_type == PluginErrorReport.ERROR_CRASH:
            mail_subject = "Your %s '%s' crashed" % (plugin_type, plugin_name)
        elif self.error_type == PluginErrorReport.ERROR_TIMEOUT:
            mail_subject = "Your %s '%s' took too much time" % (plugin_type, plugin_name)


        if self.heuristic_version is not None:
            mail_content += """You can view this error report online on the page of the heuristic: %s/heuristics/v%d/,
or on your profile page: %s/accounts/profile/


Due to this error, the heuristic will not be useable anymore!

Please fix the problem, and upload a new version of this heuristic.


""" % (settings.SECURED_WEBSITE_URL_DOMAIN, self.heuristic_version.id, settings.SECURED_WEBSITE_URL_DOMAIN)
        else:
            mail_content += """You can view this error report online on your profile page: %s/accounts/profile/


Due to this error, this %s will not be useable anymore!

Please fix the problem, push a new version of this %s in the corresponding GIT repository and notify the administrators about it.

""" % (settings.SECURED_WEBSITE_URL_DOMAIN, plugin_type, plugin_type)


        if self.experiment is not None:
            experiment_link = None
            experiment_text = None

            if (self.experiment.configuration.experiment_type == Configuration.PUBLIC) or \
               (self.experiment.configuration.experiment_type == Configuration.CONTEST_BASE) or \
               (self.experiment.configuration.experiment_type == Configuration.CONTEST_ENTRY):
                experiment_link = '/experiments/%d/' % self.experiment.id
            elif self.experiment.configuration.experiment_type == Configuration.CONSORTIUM:
                if (author.get_profile() is not None) and author.get_profile().project_member: 
                    experiment_link = '/experiments/%d/' % self.experiment.id
                else:
                    experiment_text = 'This error happened during an experiment scheduled by the consortium'
            elif self.experiment.configuration.experiment_type == Configuration.PRIVATE:
                if (author == self.experiment.user) or author.is_superuser:
                    experiment_link = '/experiments/%d/' % self.experiment.id
                else:
                    experiment_text = 'This error happened during a private experiment'
            elif self.experiment.configuration.experiment_type == Configuration.EVALUATION:
                experiment_text = 'This error happened during the evaluation of an heuristic'

            if experiment_link is not None:
                mail_content += """Experiment
----------

This error happened during the experiment '%s' (%s)


""" % (self.experiment.name, settings.SECURED_WEBSITE_URL_DOMAIN + experiment_link)
            else:
                mail_content += """Experiment
----------

%s


""" % experiment_text


        mail_content += """PROBLEM DESCRIPTION
-------------------

%s


""" % self.problemDescription()


        if self.context is not None:
            mail_content += """CONTEXT
-------

%s


""" % self.context


        if self.stacktrace is not None:
            mail_content += """STACKTRACE
----------

%s


""" % self.stacktrace


        # Send the mail
        try:
            send_mail('[MASH ALERT] %s' % mail_subject, mail_content, settings.DEFAULT_FROM_EMAIL, [author.email])
            send_mail('[MASH ALERT COPY] %s' % mail_subject, mail_content, settings.DEFAULT_FROM_EMAIL, [ admin[1] for admin in settings.ADMINS ])
        except:
            pass

        return True
