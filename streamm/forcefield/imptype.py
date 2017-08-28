# coding: utf-8
# Copyright (c) Alliance for Sustainable Energy, LLC
# Distributed under the terms of the Apache License, Version 2.0

from __future__ import division, unicode_literals

__author__ = "Travis W. Kemper, Scott Sides"
__copyright__ = "Copyright 2015, Alliance for Sustainable Energy, LLC"
__version__ = "0.3"
__email__ = "streamm@nrel.gov"
__status__ = "Beta"



class Imptype(object):
    """
    Set of improper dihedral angle parameters
    """

    def __init__(self, fftype1="blank", fftype2="blank", fftype3="blank", fftype4="blank" , type="improper" ):
        """
        Constructor for a angle parameter.
        
        Args:
             fftype1  (str)   Atom type 
             fftype2  (str)   Atom type 
             fftype3  (str)   Atom type 
             fftype4  (str)   Atom type 
             type    (str)   Improper type 
        """

        if isinstance(fftype1, str):
            self.fftype1 = fftype1
        else:
            print "1st arg should be str"
            raise TypeError

        if isinstance(fftype2, str):
            self.fftype2 = fftype2
        else:
            print "2nd arg should be str"
            raise TypeError

        if isinstance(fftype3, str):
            self.fftype3 = fftype3
        else:
            print "3rd arg should be str"
            raise TypeError

        if isinstance(fftype4, str):
            self.fftype4 = fftype4
        else:
            print "4th arg should be str"
            raise TypeError

        if isinstance(type, str):
            self.type = type
        else:
            print "5th arg should be str"
            raise TypeError

        # Set default values for parameters
        self.e0 = 0.0
        self.ke = 1.0
        self.pn = 0.0    # For periodicimproper

        # Lammps and gromacs index
        self.lammps_index = 0 
        self.gromacs_index = 0 

    def __del__(self):
        """
        Destructor, clears object memory
        """
        del self.fftype1
        del self.fftype2 
        del self.fftype3
        del self.fftype4
        del self.ke
        del self.e0
        del self.pn
        del self.lammps_index
        del self.gromacs_index 

        
    def __str__(self):
        """
        'Magic' method for printng contents
        Delegates to __str__ method for contained objects
        """
        strucStr =  " improper  %s - %s - %s - %s type %s "%(self.fftype1,self.fftype2,self.fftype3,self.fftype4,self.type)
        
        if( self.type ==  "improper" ):
            strucStr += "\n  imp e0 = %f ke = %f lammps index %d  gromcas index %d " %(self.e0,self.ke,self.lammps_index ,self.gromacs_index )

        return strucStr        


    def setimp(self, e0, ke):
        """
        set Harmonic parameters

        E = kb ( e_{lijk} - e0 )^2 

        Args:
            e0     (float) 
            kb     (float) force constant    kcal/mol
        """

        if isinstance(e0, float):
            self.e0 = e0
        else:
            print "1st arg should be float"
            raise TypeError

        if isinstance(ke, float):
            self.ke = ke
        else:
            print "2nd arg should be float"
            raise TypeError

