# coding: utf-8
# Copyright (c) Alliance for Sustainable Energy, LLC
# Distributed under the terms of the Apache License, Version 2.0

from __future__ import division, unicode_literals

__author__ = "Travis W. Kemper, Scott Sides"
__copyright__ = "Copyright 2015, Alliance for Sustainable Energy, LLC"
__version__ = "0.3"
__email__ = "streamm@nrel.gov"
__status__ = "Beta"

'''
Unit tests for the bonds module
'''


import logging
logger = logging.getLogger(__name__)

import unittest
import os

import streamm.structures.angle as angle


HOME_DIR = os.getcwd()
RELATIVE_TEST_DIR = os.path.join(os.path.dirname(__file__))
TEST_DIR = os.path.join(HOME_DIR,RELATIVE_TEST_DIR)

class TestAngle(unittest.TestCase):
    def setUp(self):
        self.angle_i = angle.Angle(2,0,1)
        
    def test_str(self):
        angle_str = ' 2 - 0 - 1'
        self.assertEqual(str(self.angle_i),angle_str)

    def tearDown(self):
        del self.angle_i 
        self.angle_i = None

    
if __name__ == '__main__':
    os.chdir(TEST_DIR)
    unittest.main()    
    os.chdir(HOME_DIR)
        
                
