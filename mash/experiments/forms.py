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


"""
Forms and validation code for the experiments

"""

from django import forms
from django.template import defaultfilters
from mash.experiments.models import Experiment, Configuration
from mash.heuristics.models import Heuristic, HeuristicVersion


class NewExperimentForm(forms.Form):

    name                = forms.CharField(max_length=200, label=u'Name', required=False,
                                          help_text=u'The name of the experiment (leave empty for an auto-generated one)')
    predictor           = forms.IntegerField(label=u'Predictor', required=True, widget=forms.HiddenInput, initial=-1,
                                             help_text=u'The predictor to use')
    predictor_settings  = forms.CharField(label=u'Predictor settings', widget=forms.Textarea, required=False,
                                          help_text=u'The predictor-specific settings. One per line.<br />Format: SETTING_NAME [value 1] [value 2] ... [value N]')
    heuristics_type     = forms.ChoiceField(label=u'Heuristic type', initial=Configuration.CUSTOM_HEURISTICS_LIST,
                                            choices=Configuration.HEURISTICS_CHOICES, help_text=u'The heuristics that will be used in the experiment')
    heuristics          = forms.CharField(label=u'Heuristics', required=False, widget=forms.HiddenInput, initial='',
                                          help_text=u'The heuristics that will be used in the experiment')
    show_all_versions   = forms.IntegerField(widget=forms.HiddenInput)


    def clean_predictor_settings(self):
        if not(self.cleaned_data.has_key('predictor_settings')):
            return ''

        lines = self.cleaned_data['predictor_settings'].replace('\r', '').split('\n')
        lines = filter(lambda x: len(x) > 0, lines)

        if len(lines) == 0:
            return ''

        result = ''
        for line in lines:
            parts = line.split(' ')
            parts = filter(lambda x: len(x) > 0, parts)
            
            if len(parts) > 0:
                result += ' '.join(parts) + '\n'
        
        return result


    def clean_heuristics(self):
        if not(self.cleaned_data.has_key('heuristics')) or (len(self.cleaned_data['heuristics']) == 0):
            if self.cleaned_data['heuristics_type'] == Configuration.CUSTOM_HEURISTICS_LIST:
                raise forms.ValidationError(u'You must select some heuristics')
        
        return self.cleaned_data['heuristics']



class NewImageBasedExperimentForm(NewExperimentForm):

    database            = forms.IntegerField(label=u'Database', required=True, widget=forms.HiddenInput, initial=-1,
                                             help_text=u'The image database to use')
    labels              = forms.CharField(label=u'Labels', required=True, widget=forms.HiddenInput, initial='',
                                          help_text=u'The list of labels used in the experiment')
    use_standard_sets   = forms.BooleanField(label=u'Use standard sets', required=False, initial=True,
                                             help_text=u'Indicates if the standard training and test image sets defined by the database must be used')
    training_ratio      = forms.FloatField(label=u'Training ratio', required=False, initial=0.5, max_value=1.0, min_value=0.0,
                                           help_text=u'Ratio of the objects used for training (between 0.0 and 1.0)')

    # Non-fields
    detection = False


    def clean_labels(self):
        if not(self.detection):
            if not(self.cleaned_data.has_key('labels')) or (len(self.cleaned_data['labels']) == 0) or \
               (len(self.cleaned_data['labels'].split(' ')) < 2):
                raise forms.ValidationError(u'You must select two or more labels')
        else:
            if not(self.cleaned_data.has_key('labels')) or (len(self.cleaned_data['labels']) == 0):
                raise forms.ValidationError(u'You must select at least one label')

        return self.cleaned_data['labels']


class NewGoalplanningExperimentForm(NewExperimentForm):

    task_type   = forms.IntegerField(label=u'Task', required=True, widget=forms.HiddenInput, initial=-1,
                                     help_text=u'The type of goal-planning application')
    goal        = forms.IntegerField(label=u'Goal', required=True, widget=forms.HiddenInput, initial=-1,
                                     help_text=u'The goal that must be achieved')
    environment = forms.IntegerField(label=u'Environment', required=True, widget=forms.HiddenInput, initial=-1,
                                     help_text=u'The environment to use')
