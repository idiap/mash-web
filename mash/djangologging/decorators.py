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


from djangologging import SUPPRESS_OUTPUT_ATTR


def suppress_logging_output(func=None):
    """
    Decorates a view to prevent any log messages generated by it (or anything 
    it calls) from being outputted to the browser.
    """  
    def decorated(*args, **kwargs):
        response = func(*args, **kwargs)
        setattr(response, SUPPRESS_OUTPUT_ATTR, True)
        return response
    return decorated

def supress_logging_output(func=None):
    import warnings
    warnings.warn('supress_logging_output is deprecated and will be removed soon; use the correctly spelled version instead: suppress_logging_output.')
    return suppress_logging_output(func)