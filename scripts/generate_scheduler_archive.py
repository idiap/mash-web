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


import sys
import os
from mash import Packager


# Constants
DISTRIB_FOLDER  = 'distrib'
ARCHIVE_PREFIX  = 'scheduler'


# Process the command-line arguments
if len(sys.argv) != 2:
    print "Usage: %s <version>" % sys.argv[0]
    print
    sys.exit(-1)


# Go to the working directory
directory = os.path.abspath(os.path.dirname(sys.argv[0]))
os.chdir(os.path.join(directory, '../scheduler'))


# Create the packager
packager = Packager(os.getcwd(), os.path.join(os.getcwd(), '..', DISTRIB_FOLDER), ARCHIVE_PREFIX + '_' + sys.argv[1])


# Copy the needed files
packager.copyTree('implemented_tasks', ['*.pyc'])
packager.copyTree('tasks', ['*.pyc'])
packager.copyTree('utilities', ['*.pyc'])
packager.copyFiles('.', '*.py')

os.chdir(os.path.join(directory, '..'))
packager.src_path = os.getcwd()

packager.copyFile('scripts', 'cleanup_scheduler.sh', 'cleanup.sh')
packager.copyTree('pymash', ['*.pyc'])


# Create the archive
packager.createTarGz()
