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


from threading import Lock
from datetime import datetime
import time
import os


# Global variables
folder_name_generation_lock = Lock()


#-------------------------------------------------------------------------------
# Generate a unique folder name
#-------------------------------------------------------------------------------
def generateUniqueFolderName():
    folder_name_generation_lock.acquire()

    folder_name = None

    try:
        time.sleep(0.005)   # Garantee that milliseconds are different for each generation
        now = datetime.now()

        folder_name = os.path.join(str(now.year), str(now.month), str(now.day),
                                   str(now.hour), str(now.minute), str(now.second),
                                   str(now.microsecond / 1000))
    finally:
        folder_name_generation_lock.release()

    return folder_name
