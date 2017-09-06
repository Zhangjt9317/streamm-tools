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
Unit tests for the lammps module
'''

import logging
logger = logging.getLogger(__name__)

import unittest
import os
import numpy as np
import random
import numpy.testing.utils as nptu


from streamm.calculations.lammps import LAMMPS
from streamm.buildingblocks.container import Container as BBCont
import streamm.structures.particle as particle

import streamm.forcefields.particletype as particletype
import streamm.forcefields.bondtype as bondtype
import streamm.forcefields.angletype as angletype
import streamm.forcefields.dihtype as dihtype
import streamm.forcefields.imptype as imptype

from streamm.calculations.resource import Resource

import shutil


HOME_DIR = os.getcwd()
RELATIVE_TEST_DIR = os.path.join(os.path.dirname(__file__))
TEST_DIR = os.path.join(HOME_DIR,RELATIVE_TEST_DIR)
TEMPLATE_PATH =  os.path.join(TEST_DIR,'..','..','..','templates')
    

class Test_Thiophene(unittest.TestCase):
    # 
    def setUp(self):
        self.calc_i = LAMMPS('lmp_thiophene')
        

        self.Th = BBCont('thiophene')
        symbols = ['C','C','C','C','S','H','H','H','H']
        positions = [ ]
        positions.append([-1.55498576,-1.91131218,-0.00081000])
        positions.append([-0.17775976,-1.91131218,-0.00081000])
        positions.append([0.34761524,-0.57904218,-0.00081000])
        positions.append([-0.65884476,0.36101082,0.00000000])
        positions.append([-2.16948076,-0.35614618,-0.00000800])
        positions.append([-2.18966076,-2.79526518,-0.00132100])
        positions.append([0.45389024,-2.80145418,-0.00106400])
        positions.append([1.41682424,-0.35961818,-0.00138200])
        positions.append([-0.51943676,1.44024682,0.00064700])
        for i in range(len(symbols)):
            pt_i = particle.Particle(symbol=symbols[i])
            #pt_i.properties = periodictable.element_symbol()
            pos_i = positions[i]
            self.Th.add_partpos(pt_i,pos_i)
            
            
        for pkey,p in self.Th.particles.iteritems():
            print  pkey,p
            if( p.symbol == 'C' ):
                p.ffkey = 'CA'
            elif( p.symbol == 'H' ):
                p.ffkey = 'HA'
            elif( p.symbol == 'S' ):
                p.ffkey = 'S'
                
        self.Th.particles[5].rsite = 'TH'
        self.Th.particles[6].rsite = 'FH'
        self.Th.particles[8].rsite = 'TH'
        self.Th.bonded_nblist = self.Th.guess_nblist(0,radii_buffer=1.25)
        self.Th.find_rsites()
        
        self.calc_i.add_strucC(self.Th)
        
        
        self.calc_i.strucC.lat_cubic(25.0)
        
        self.calc_i.strucC.bonded_bonds()
        self.calc_i.strucC.bonded_angles()
        self.calc_i.strucC.bonded_dih()

    
        
        ptype_i = particletype.Particletype('CA')
        ptype_i.mass = 12.011
        ptype_i.epsilon = 0.07
        ptype_i.sigma = 3.55 
        ptype_i.lammps_index = 1
        self.calc_i.paramC.add_particletype(ptype_i)
        
        
        ptype_i = particletype.Particletype('HA')
        ptype_i.mass = 1.008
        ptype_i.epsilon = 0.03
        ptype_i.sigma = 2.42
        ptype_i.lammps_index = 2
        self.calc_i.paramC.add_particletype(ptype_i)
        

        ptype_i = particletype.Particletype('S')
        ptype_i.mass = 32.06 
        ptype_i.epsilon =0.250
        ptype_i.sigma = 3.55 
        ptype_i.lammps_index = 3
        self.calc_i.paramC.add_particletype(ptype_i)
        
        
                
        btype = "harmonic"
        bondtype_i = bondtype.Bondtype('CA','CA',type=btype)
        bondtype_i.kb = 469.00
        bondtype_i.r0 = 1.4 
        self.calc_i.paramC.add_bondtype(bondtype_i)
        
        bondtype_i = bondtype.Bondtype('CA','HA',type=btype)
        bondtype_i.kb =367.00
        bondtype_i.r0 = 1.08
        self.calc_i.paramC.add_bondtype(bondtype_i)
        
        bondtype_i = bondtype.Bondtype('CA','S',type=btype)
        bondtype_i.kb = 250.00
        bondtype_i.r0 =  1.7600
        self.calc_i.paramC.add_bondtype(bondtype_i)
        
        

        atype = "harmonic"
        angletype_i = angletype.Angletype('CA','CA','CA',type=atype)
        angletype_i.kb =   63.00
        angletype_i.theta0 =  120.0
        self.calc_i.paramC.add_angletype(angletype_i)
        
        

        angletype_i = angletype.Angletype('CA','CA','HA',type=atype)
        angletype_i.kb =   35.0
        angletype_i.theta0 =  120.0
        self.calc_i.paramC.add_angletype(angletype_i)
        
        
        angletype_i = angletype.Angletype('S','CA','HA',type=atype)
        angletype_i.kb =   35.0
        angletype_i.theta0 =  113.4000
        self.calc_i.paramC.add_angletype(angletype_i)
        
        
        angletype_i = angletype.Angletype('S','CA','CA',type=atype)
        angletype_i.kb =   85.0
        angletype_i.theta0 =  119.4000
        self.calc_i.paramC.add_angletype(angletype_i)
        
        angletype_i = angletype.Angletype('CA','S','CA',type=atype)
        angletype_i.kb =  74.0
        angletype_i.theta0 =   97.000
        self.calc_i.paramC.add_angletype(angletype_i)
        
        # 
        dtype = 'rb'
        dihtype_i = dihtype.Dihtype('X','CA','CA','X',type=dtype)
        dihtype_i.k2 = 7.250008
        self.calc_i.paramC.add_dihtype(dihtype_i)
        
        dihtype_i = dihtype.Dihtype('X','CA','S','X',type=dtype)
        dihtype_i.k2 = 7.250008
        self.calc_i.paramC.add_dihtype(dihtype_i)
    
        imptype_i = imptype.Imptype('CA','CA','CA','HA')
        imptype_i.kb =   10.0
        imptype_i.theta0 =  0.000
        self.calc_i.paramC.add_imptype(imptype_i)
        
        self.calc_i.set_ffparam()
        
        self.res_tag = 'local'  # Change this to remote to run the calculations remotely 
        self.res_i = Resource(self.res_tag )
        self.res_i.dir['templates'] = TEMPLATE_PATH
        self.res_i.make_dir()


        self.calc_i.set_resource(self.res_i)
        self.calc_i.make_dir()
        


    def test_writeinput(self):
        
        file_type = 'templates'
        file_key = 'in'
        file_name = "lammps_sp.in"
        from_dirkey = 'templates'
        to_dirkey = 'scratch'
        self.calc_i.cp_file(file_type,file_key,file_name,from_dirkey,to_dirkey)
        
        
        file_type = 'templates'
        file_key = 'run'
        file_name = "lammps.sh"
        from_dirkey = 'templates'
        to_dirkey = 'scratch'
        self.calc_i.cp_file(file_type,file_key,file_name,from_dirkey,to_dirkey)

        os.chdir(self.calc_i.dir['scratch'])
        
        self.calc_i.load_str('templates','in')
        
        self.calc_i.load_str('templates','run')
                
                
        self.calc_i.write_data()
        
        self.calc_i.replacewrite_prop('in','input','in','%s.in'%(self.calc_i.tag))
    
        
    
        self.calc_i.properties['input_in'] = self.calc_i.files['input']['in']
        self.calc_i.replacewrite_prop('run','scripts','run','%s.sh'%(self.calc_i.tag))

        os.chdir(self.calc_i.dir['home'])
        self.calc_i.dump_json()
        
        os.chdir(self.calc_i.dir['scratch'])
        self.calc_i.check()
                
        self.calc_i.strucC.charge = 0.0 
        for p,pt in self.calc_i.strucC.particles.iteritems(): # properties["charge"] 
            self.calc_i.strucC.charge  += pt.charge
            
        self.assertEqual(self.calc_i.strucC.charge,0.0)
        
        os.chdir(self.calc_i.dir['home'])

    def test_writejson(self):
        self.calc_i.dump_json()
        tag_i = self.calc_i.tag
        del self.calc_i
        self.calc_i = LAMMPS(tag_i)
        self.calc_i.load_json()
        # Clean up files 
        os.remove(self.calc_i.files['data']['json'])


    def tearDown(self):
        del self.calc_i         
        del self.Th         

        shutil.rmtree(os.path.join(TEST_DIR, 'materials'))
        shutil.rmtree(os.path.join(TEST_DIR, 'scratch'))
        shutil.rmtree(os.path.join(TEST_DIR, 'scripts'))
        shutil.rmtree(os.path.join(TEST_DIR, 'storage'))



if __name__ == '__main__':
    os.chdir(TEST_DIR)
    unittest.main()    
    os.chdir(HOME_DIR)
        
                