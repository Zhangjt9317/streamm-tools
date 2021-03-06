# coding: utf-8
# Copyright (c) Alliance for Sustainable Energy, LLC
# Distributed under the terms of the Apache License, Version 2.0

from __future__ import division, unicode_literals

__author__ = "Travis W. Kemper, Ph.D."
__copyright__ = "Copyright 2015, Alliance for Sustainable Energy, LLC"
__version__ = "0.3.4"
__email__ = "organicelectronics@nrel.gov"
__status__ = "Beta"


'''
Unit tests for the particles module
'''

import logging
logger = logging.getLogger(__name__)

import unittest
import os

import streamm.forcefields.angletype as angletype
            

from streamm_testutil import *



class Testangletype(unittest.TestCase):
    @setUp_streamm 
    def setUp(self):
        self.angletype_i = angletype.Angletype("HC","CH","S")
        self.angletype_i.theta0 = 120.0
        self.angletype_i.kb = 4.56

    def test_anglestr(self):
        angle_str = ' angle  HC - CH - S type harmonic \n  harmonic theta_0 = 120.000000 K = 4.560000 lammps index 0  gromacs index 0  '
        self.assertEqual(str(self.angletype_i),angle_str)
        

    def test_save(self):
        json_data = self.angletype_i.export_json()
        del self.angletype_i
        self.angletype_i = angletype.Angletype("X","X","X")
        self.angletype_i.import_json(json_data)
        
        self.assertEqual(self.angletype_i.fftype1,'HC')
        self.assertEqual(self.angletype_i.fftype2,'CH')
        self.assertEqual(self.angletype_i.fftype3,'S')
        self.assertEqual(self.angletype_i.type,'harmonic')
        self.assertEqual(self.angletype_i.theta0,120.0)
        self.assertEqual(self.angletype_i.kb,4.56)
        
                
    @tearDown_streamm 
    def tearDown(self):
        del self.angletype_i 
        self.angletype_i = None

    
if __name__ == '__main__':

    unittest.main()    

        
                
