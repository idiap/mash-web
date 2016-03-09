#! /usr/bin/env python

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


import xml.dom.minidom
import os


class ImageInfo(object):

    url_prefix = ''

    def __init__(self, name, width, height, scale, training_index, test_index):
        self.name           = name
        self.width          = width
        self.height         = height
        self.scale          = scale
        self.training_index = None
        self.test_index     = None

        if len(training_index) > 0:
            self.training_index = int(training_index)

        if len(test_index) > 0:
            self.test_index = int(test_index)

    def url(self):
        return ImageInfo.url_prefix + self.name


class DataReport(object):

    EXP_TYPE_CLASSIFICATION     = 0
    EXP_TYPE_OBJECT_DETECTION   = 1
    EXP_TYPE_GOALPLANNING       = 2


    def __init__(self):
        self.folder                 = None
        self.images                 = None
        self.experiment_type        = None
        self.global_seed            = None
        self.experiment_settings    = {}
        self.instruments_list       = {}
        self.predictor              = None
        self.predictor_settings     = {}
        self.heuristics_list        = {}
        self.labels_list            = {}

    def parse(self, folder):
        try:
            self.folder = folder

            # Configuration
            document = xml.dom.minidom.parse(os.path.join(self.folder, 'configuration.xml'))

            element = document.getElementsByTagName("experiment")[0]
            self.global_seed = int(element.getAttribute('globalseed'))

            experiment_type = element.getAttribute('type')
            if experiment_type == 'Classification':
                self.experiment_type = DataReport.EXP_TYPE_CLASSIFICATION
            elif experiment_type == 'ObjectDetection':
                self.experiment_type = DataReport.EXP_TYPE_OBJECT_DETECTION
            else:
                self.experiment_type = DataReport.EXP_TYPE_GOALPLANNING

            self.experiment_settings = DataReport._getSettingsList(element)

            elements = document.getElementsByTagName("instrument")
            for element in elements:
                name = element.getAttribute('name')
                settings = DataReport._getSettingsList(element)
                self.instruments_list[name] = settings

            element = document.getElementsByTagName("predictor")[0]
            self.predictor = element.getAttribute('name')
            self.predictor_settings = DataReport._getSettingsList(element)

            elements = document.getElementsByTagName("heuristic")
            for element in elements:
                self.heuristics_list[int(element.getAttribute('index'))] = element.getAttribute('name')

            if (self.experiment_type == DataReport.EXP_TYPE_CLASSIFICATION) or (self.experiment_type == DataReport.EXP_TYPE_OBJECT_DETECTION):
                # Labels
                document = xml.dom.minidom.parse(os.path.join(self.folder, 'labels.xml'))

                elements = document.getElementsByTagName("label")
                for element in elements:
                    self.labels_list[int(element.getAttribute('index'))] = element.getAttribute('name')


                ImageInfo.url_prefix = '/images/databases/%s/' % self.getExperimentSettingDatabaseName()

            return True
        except:
            return False

    def nbInstruments(self):
        return len(self.instruments_list)

    def instruments(self):
        try:
            return self.instruments_list.keys()
        except:
            return None

    def nbHeuristics(self):
        return len(self.heuristics_list)

    def heuristic(self, index):
        try:
            return self.heuristics_list[index]
        except:
            return None

    def nbLabels(self):
        return len(self.labels_list)

    def labelName(self, index):
        try:
            return self.labels_list[index]
        except:
            return None

    def nbImages(self):
        try:
            if self.images is None:
                self._parseImages()

            return len(self.images)
        except:
            return None

    def image(self, index):
        try:
            if self.images is None:
                self._parseImages()

            return self.images[index]
        except:
            return None

    def _parseImages(self):
        self.images = {}

        images_document = xml.dom.minidom.parse(os.path.join(self.folder, 'images.xml'))

        elements = images_document.getElementsByTagName("image")
        for element in elements:
            self.images[int(element.getAttribute('index'))] = ImageInfo(element.getAttribute('name'),
                                                                        int(element.getAttribute('width')),
                                                                        int(element.getAttribute('height')),
                                                                        float(element.getAttribute('scale')),
                                                                        element.getAttribute('training_index'),
                                                                        element.getAttribute('test_index'))

    def data(self, instrument_name):
        try:
            inFile = open(os.path.join(self.folder, '%s.data' % instrument_name), 'rb')
            content = inFile.read()
            inFile.close()
            return content
        except:
            return None

    def predictor_data(self):
        return self.data('predictor')

    def getExperimentSetting(self, setting):
        try:
            values = self.experiment_settings[setting]
            if len(values) == 1:
                return values[0]
            else:
                return values
        except:
            return None

    def getInstrumentSetting(self, instrument, setting):
        try:
            values = self.instruments_list[instrument][setting]
            if len(values) == 1:
                return values[0]
            else:
                return values
        except:
            return None

    def getPredictorSetting(self, setting):
        try:
            values = self.predictor_settings[setting]
            if len(values) == 1:
                return values[0]
            else:
                return values
        except:
            return None

    def getExperimentSettingDatabaseName(self):
        if (self.experiment_type != DataReport.EXP_TYPE_CLASSIFICATION) and (self.experiment_type != DataReport.EXP_TYPE_OBJECT_DETECTION):
            return None

        try:
            return self.experiment_settings['DATABASE_NAME'][0]
        except:
            return None

    def getExperimentSettingLabels(self):
        if (self.experiment_type != DataReport.EXP_TYPE_CLASSIFICATION) and (self.experiment_type != DataReport.EXP_TYPE_OBJECT_DETECTION):
            return None

        try:
            labels = self.experiment_settings['LABELS']
            processed_labels = []
            for label in labels:
                parts = label.split('-')
                if len(parts) == 2:
                    processed_labels.extend(range(int(parts[0]), int(parts[1]) + 1))
                else:
                    processed_labels.append(int(parts[0]))
            return processed_labels
        except:
            return None

    def getExperimentSettingTrainingSamples(self):
        if (self.experiment_type != DataReport.EXP_TYPE_CLASSIFICATION) and (self.experiment_type != DataReport.EXP_TYPE_OBJECT_DETECTION):
            return None

        try:
            return float(self.experiment_settings['TRAINING_SAMPLES'][0])
        except:
            return None

    def getExperimentSettingRoiSize(self):
        try:
            return int(self.experiment_settings['ROI_SIZE'][0])
        except:
            return None

    def getExperimentSettingBackgroundImages(self):
        if (self.experiment_type != DataReport.EXP_TYPE_CLASSIFICATION) and (self.experiment_type != DataReport.EXP_TYPE_OBJECT_DETECTION):
            return None

        try:
            return (self.experiment_settings['BACKGROUND_IMAGES'][0] != 'OFF')
        except:
            return None

    def getExperimentSettingStepX(self):
        if self.experiment_type != DataReport.EXP_TYPE_OBJECT_DETECTION:
            return None

        try:
            return int(self.experiment_settings['STEP_X'][0])
        except:
            return None


    def getExperimentSettingStepY(self):
        if self.experiment_type != DataReport.EXP_TYPE_OBJECT_DETECTION:
            return None

        try:
            return int(self.experiment_settings['STEP_Y'][0])
        except:
            return None


    def getExperimentSettingStepZ(self):
        if self.experiment_type != DataReport.EXP_TYPE_OBJECT_DETECTION:
            return None

        try:
            return float(self.experiment_settings['STEP_Z'][0])
        except:
            return None

    def getExperimentSettingGoalName(self):
        if self.experiment_type != DataReport.EXP_TYPE_GOALPLANNING:
            return None

        try:
            return self.experiment_settings['GOAL_NAME'][0]
        except:
            return None

    def getExperimentSettingEnvironmentName(self):
        if self.experiment_type != DataReport.EXP_TYPE_GOALPLANNING:
            return None

        try:
            return self.experiment_settings['ENVIRONMENT_NAME'][0]
        except:
            return None

    def getExperimentSettingViewsSize(self):
        if self.experiment_type != DataReport.EXP_TYPE_GOALPLANNING:
            return None

        try:
            return int(self.experiment_settings['VIEWS_SIZE'][0])
        except:
            return None

    @staticmethod
    def _getChildrenElements(parent, tagName):
        return filter(lambda x: (x.nodeType == x.ELEMENT_NODE) and (x.tagName == tagName), parent.childNodes)

    @staticmethod
    def _getSettingsList(parent):
        settings = {}

        for child in DataReport._getChildrenElements(parent, 'setting'):
            name = child.getAttribute('name')
            arguments = []

            for argument in DataReport._getChildrenElements(child, 'argument'):
                arguments.append(argument.getAttribute('value'))

            settings[name] = arguments

        return settings
