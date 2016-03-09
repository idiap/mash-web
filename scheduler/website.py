# First thing to do: setup the same Django environment than the website, so
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


 we can reuse the existing DB models
from django.core.management import setup_environ
import sys
import os


root_path = os.path.dirname(os.path.abspath(__file__))

if not(os.path.exists(os.path.join(root_path, 'mash/settings.py'))):
    print "Failed to find the 'settings.py' file of the website, please create a " \
          "symbolic link to the 'mash' folder of the website in the Scheduler folder"
    sys.exit(1)

pos = 0
ref_path = os.path.dirname(root_path)
for path in sys.path:
    if path.startswith(ref_path):
        pos += 1
    else:
        break

sys.path.insert(pos, os.path.join(root_path, 'mash/'))
import settings
    
setup_environ(settings)


# If we can't find pymash in the Scheduler folder, try in the parent one
if not(os.path.exists(os.path.join(root_path, 'pymash/'))):
    if not(os.path.exists(os.path.join(root_path, os.path.pardir, 'pymash/'))):
        print "Failed to find pymash, please create a " \
              "symbolic link to the 'pymash' folder in the Scheduler folder"
        sys.exit(1)
    else:
        sys.path.insert(pos + 1, os.path.abspath(os.path.join(root_path, os.path.pardir)))

import pymash
