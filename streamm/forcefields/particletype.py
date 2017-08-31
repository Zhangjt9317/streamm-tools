# coding: utf-8
# Copyright (c) Alliance for Sustainable Energy, LLC
# Distributed under the terms of the Apache License, Version 2.0

from __future__ import division, unicode_literals

__author__ = "Travis W. Kemper, Scott Sides"
__copyright__ = "Copyright 2015, Alliance for Sustainable Energy, LLC"
__version__ = "0.3"
__email__ = "streamm@nrel.gov"
__status__ = "Beta"

# NoteTK  This should be in structure.particles 

class Particletype(object):
    '''
    Particle represented by a Force-field
    '''
    def __init__(self,type='X'):
        """
        Constructor for a Force-field particle. 
        """
        self.type = str(type) 
        self.epsilon = 1.0
        self.sigma = 2.0 
        self.lammps_index = None
        self.gromacs_index = None 
    
    def __del__(self):
        """
        Destructor, clears structure memory and calls held container destructors
        """
        del self.type
        del self.epsilon
        del self.sigma 
        del self.lammps_index
        del self.gromacs_index
        
    def __str__(self):
        """
        'Magic' method for printng contents of container
        """
        return " {} epsilon:{} sigma:{}".format(self.type,self.epsilon,self.sigma)