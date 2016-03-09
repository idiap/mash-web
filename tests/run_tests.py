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
import unittest
import traceback

MASH_TEST_MODE = 'ON'

os.environ['MASH_TEST_MODE'] = MASH_TEST_MODE

sys.path.insert(1, os.path.join(os.path.abspath(os.path.pardir), 'scheduler'))
import website

# print sys.path

path_prefix = os.getcwd()

error_reported = False


# Search for all the test cases
test_cases = []
for root, dirs, files in os.walk(os.getcwd()):
    test_files = filter(lambda x: x.startswith('test_') and x.endswith('.py'), files)

    dirs_to_ignore = filter(lambda x: not(x.startswith('tests_')), dirs)
    for dir_to_ignore in dirs_to_ignore:
        dirs.remove(dir_to_ignore)

    for test_file in test_files:
        try:
            name = os.path.join(root[len(path_prefix)+1:], test_file[:-3]).replace('/', '.')
            
            module = __import__(name)

            parts = name.split('.')
            for part in parts[1:]:
                module = module.__getattribute__(part)
            
            test_cases.extend(module.tests())
        except Exception, e:
            if not(error_reported):
                print
                print '************* SETUP ****************'
                print
                error_reported = True
            
            print 'ERROR: ' + str(e)
            print traceback.format_exc()


suite = unittest.TestSuite()
for test_case in test_cases:
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(test_case))

if error_reported:
    print
    print '************* RUNNING THE TESTS ****************'
    print


# Run the tests
unittest.TextTestRunner(verbosity=2).run(suite)