#! /usr/bin/env python
"""

Radial distribution  code

 length - Angstroms
 mass   - AMU
 volume - Angstroms^3
"""

# Dr. Travis Kemper
# NREL
# Initial Date 6/30/2014
# travis.kemper@nrel.gov

from itertools import izip

#MDanalysis
try:
    from MDAnalysis import *
    from MDAnalysis.core.distances import * ##distance_array
    #import MDAnalysis.core.units            # for bulk water density
except:
    import sys
    print "MDAnalysis module not build/configured correctly"
    sys.exit(0)

# Scott's new classes
import particles
from particles import Particle
from particles import ParticleContainer
from bonds     import BondContainer
from structureContainer import StructureContainer
from parameters import ParameterContainer

import mpiNREL
import pbcs
import json, math , sys 
import numpy as np
import datetime

import gromacs , lammps


def get_options():
    """
    Set options
    """
    import os, os.path
    from optparse import OptionParser
 
    usage = "usage: %prog [options] \n"
    parser = OptionParser(usage=usage)
    
    parser.add_option("-v","--verbose", dest="verbose", default=False,action="store_true", help="Verbose output ")
    parser.add_option("-p","--ptime", dest="ptime", default=False,action="store_true", help="Print performance information  ")
    parser.add_option("-o","--output_id", dest="output_id", default="rdf",type="string",help=" prefix for output files  ")
    parser.add_option("--print_grps", dest="print_grps",default=False,action="store_true",help=" Print atoms in each group  ")
    #
    # Input files
    #
    parser.add_option("-j","--in_json", dest="in_json", type="string", default="", help="Input json file, which read in first then over writen by subsequent input files")
    parser.add_option("--in_itp", dest="in_itp",  type="string", default="",help="gromacs force field parameter file")
    parser.add_option("--in_top", dest="in_top", type="string", default="", help="Input gromacs topology file (.top) ")
    parser.add_option("--in_gro", dest="in_gro", type="string", default="", help="Input gromacs structure file (.gro) ")
    parser.add_option("--in_data", dest="in_data", type="string", default="", help="Input lammps structure file (.data) ")

    # Trajectory file
    parser.add_option("--in_lammpsxyz", dest="in_lammpsxyz", type="string", default="", help="Input lammps xyz file with atoms listed as atom type numbers")    
    parser.add_option("--in_dcd", dest="in_dcd", type="string", default="", help="Input dcd file with atoms listed as atom type numbers")    
    parser.add_option("--in_xtc", dest="in_xtc", type="string", default="", help="Input xtc file with atoms listed as atom type numbers")  

    parser.add_option("--mol_inter",dest="mol_inter", default=False,action="store_true", help="Use only inter molecular rdf's ")
    parser.add_option("--mol_intra",dest="mol_intra", default=False,action="store_true", help="Use only intra molecular rdf's")
    
    # Bins
    parser.add_option("--r_cut", dest="r_cut", type=float, default=20.0, help=" Cut off radius in angstroms ")
    parser.add_option("--box_cut",dest="box_cut", default=False,action="store_true", help="Set cut off to half the box length")
    parser.add_option("--bin_size", dest="bin_size", type=float, default=0.10, help=" Bin size in angstroms")
    
    # Searchable properties
    # I
    parser.add_option("--id_i", dest="id_i", type="string", default="", help=" select atoms of group i by id number  ")    
    parser.add_option("--symbol_i", dest="symbol_i", type="string", default="", help=" select atoms of group by (atomic) symbol   ")    
    parser.add_option("--type_i", dest="type_i", type="string", default="", help=" select type  ")    
    parser.add_option("--chains_i", dest="chains_i", type="string", default="", help="select atoms of group i by chain number  ")    
    parser.add_option("--ring_i", dest="ring_i", type="string", default="", help="select atoms of group i by particles in a ring   ")    
    parser.add_option("--resname_i", dest="resname_i", type="string", default="", help="select atoms of group i by residue name  ")    
    parser.add_option("--residue_i", dest="residue_i", type="string", default="", help="select atoms of group i by resudue number  ")    
    parser.add_option("--linkid_i", dest="linkid_i", type="string", default="", help="select atoms of group i by  link id ")    
    parser.add_option("--fftype_i", dest="fftype_i", type="string", default="", help="select atoms of group i by force field type  ")
    parser.add_option("--gtype_i", dest="gtype_i", type="string", default="", help="select atoms of group i by gromacs id   ")
    # J
    parser.add_option("--id_j", dest="id_j", type="string", default="", help=" select atoms of group j by id number  ")    
    parser.add_option("--symbol_j", dest="symbol_j", type="string", default="", help=" select atoms of group by (atomic) symbol   ")    
    parser.add_option("--type_j", dest="type_j", type="string", default="", help=" select type  ")    
    parser.add_option("--chains_j", dest="chains_j", type="string", default="", help="select atoms of group j by chain number  ")    
    parser.add_option("--ring_j", dest="ring_j", type="string", default="", help="select atoms of group j by particles in a ring   ")    
    parser.add_option("--resname_j", dest="resname_j", type="string", default="", help="select atoms of group j by residue name  ")    
    parser.add_option("--residue_j", dest="residue_j", type="string", default="", help="select atoms of group j by resudue number  ")    
    parser.add_option("--linkid_j", dest="linkid_j", type="string", default="", help="select atoms of group j by  link id ")    
    parser.add_option("--fftype_j", dest="fftype_j", type="string", default="", help="select atoms of group j by force field type  ")    
    parser.add_option("--gtype_j", dest="gtype_j", type="string", default="", help="select atoms of group j by force field type  ")    
    
    # Frames
    parser.add_option("--frame_o", dest="frame_o", type=int, default=0, help=" Initial frame to read")
    parser.add_option("--frame_f", dest="frame_f", type=int, default=10000, help=" Final frame to read")
    parser.add_option("--frame_step", dest="frame_step", type=int, default=1, help=" Read every nth frame ")
    parser.add_option("--readall_f", dest="readall_f", default=True,action="store_true", help=" Read to end of trajectory file (negates frame_f value)")
        
    (options, args) = parser.parse_args()
        
    return options, args
   
    
def main():
    """
    Calculate radial distribution (RDF) based on specified atom types

    Input:
        - json file ".json" containing all the information for structure
        - frames to average RDF over
            - lammps xyz file ".xyz"
        - calculation specifications 
            - atomic groups to calculate RDF between
            - which frames to use 
    Output:
        - data file ".dat" containing the rdf
        - log file ".log" containing calculation information
            the amount of information in the log file can be increased using the verbose option ( -v ) 
        
    """
    prtCl_time = False
    debug = False 
    #
    # Formated ouput varables
    #
    sperator_line = "\n---------------------------------------------------------------------"

    # Initialize mpi
    p = mpiNREL.getMPIObject()

    # MPI setup
    rank = p.getRank()
    size = p.getCommSize()
 
    options, args = get_options()


    if( rank == 0 ):
        # record initial time 
        t_i = datetime.datetime.now()
        # Open log files 
        log_file = options.output_id + ".log"
        log_out = open(log_file,"w") 


    p.barrier()
    
    #
    #  Initialize blank system 
    # 
    struc_o = StructureContainer()
    param_o = ParameterContainer() 

    if( rank == 0 ):

        log_line = sperator_line
        log_line += "\n  Reading in input files "
        log_line += sperator_line

        log_out.write(log_line)
        print log_line

    #struc_o = file_io.get_strucC( options.in_json, options.in_gro , options.in_top, options.in_data )
    #
    # Read in json file
    #
    if( len(options.in_json) ):
        if( rank == 0 and options.verbose ):
            print  "     - Reading in ",options.in_json
        json_data_i = struc_o.getsys_json(options.in_json)
    #
    # Read gro file 
    #
    if( len(options.in_gro) ):
        if( options.verbose ): print  "     GROMACS .gro file ",options.in_gro
        struc_o = gromacs.read_gro(struc_o,options.in_gro)
    #
    # Read in top file
    #
    if( len(options.in_top) ):
        if( options.verbose ): print  "     GROMACS .top file ",options.in_top
        struc_o,ljmixrule = gromacs.read_top(struc_o,param_o,options.in_top)
    # 
    # Read lammps data file 
    #
    if( len(options.in_data) ):
        if( options.verbose ): print  "     LAMMPS data file ",options.in_data            
        struc_o = lammps.read_lmpdata(struc_o,param_o,options.in_data)


    # 
    # Read in trajectory 
    #
    if( len(options.in_xtc ) and  len(options.in_gro) ):
        if( rank == 0 ):
            if( options.verbose ): print "  Reading  %s and %s "%(options.in_xtc,options.in_gro)
        universe =  Universe(options.in_gro, options.in_xtc)
    elif(len(options.in_gro) ):
        if( rank == 0 ):
            if( options.verbose ): print "  Reading  %s "%(options.in_gro)
        universe =  Universe(options.in_gro)
    elif( len(options.in_dcd ) and  len(options.in_data) ):
        if( rank == 0 ):
            if( options.verbose ): print "  Reading  %s and %s "%(options.in_xtc,options.in_gro)
        universe =  Universe(options.in_dcd, options.in_data)
    elif(len(options.in_gro) ):
        if( rank == 0 ):
            if( options.verbose ): print "  Reading  %s "%(options.in_gro)
        universe =  Universe(options.in_gro)
    else:
        sys.exit("Trajectory read in error ")

    p.barrier()
    
    # Get paticle and bond structures
    ptclC_o = struc_o.ptclC
    bondC_o  = struc_o.bondC
    un =  universe.selectAtoms("resname * ")
    coord = un.coordinates()
    
        
    # Check options
    if( options.mol_inter and options.mol_intra and rank == 0  ):
	print " Options --mol_inter and --mol_intra are mutually exclusive "
	sys.exit("Error is specified options ")
        
    if( options.box_cut ):
        latvec = struc_o.getLatVec()
        options.r_cut = math.floor(latvec[0][0]/2.0)
        
    # Print system properties
    if( rank == 0 ):
        sys_prop = struc_o.printprop()
        print sys_prop
        log_out.write(str(sys_prop))
        
    # Create sub lists for RDF groups i and j
    search_i = particles.create_search(options.id_i,options.type_i,options.symbol_i,options.chains_i,options.ring_i,options.resname_i,options.residue_i,options.linkid_i,options.fftype_i,options.gtype_i)
    if( rank == 0 ):
        if( options.verbose ): print " Searching group i ",search_i
    list_i = ptclC_o.getParticlesWithTags(search_i)
    sum_i = len(list_i)
    if( rank == 0 ):
        if( options.verbose ): print "   patricles group i ",sum_i

    # Relabel segments to correspond to lists i
    for pid_i in list_i:
        #print pid_i,ptclC_o[pid_i].tagsDict["gtype"],ptclC_o[pid_i].position," from u ",universe.atoms[pid_i-1].name , universe.coord[pid_i-1]
        universe.atoms[pid_i-1].resname = "grpi"
        universe.atoms[pid_i-1].resnum = ptclC_o[pid_i].tagsDict["chain"]  # Set resnum to chain number for inter/intra rdf's
    uni_i = universe.selectAtoms(" resname grpi ")
    
    search_j = particles.create_search(options.id_j,options.type_j,options.symbol_j,options.chains_j,options.ring_j,options.resname_j,options.residue_j,options.linkid_j,options.fftype_j,options.gtype_j)
    if( rank == 0 ):
        if( options.verbose ): print " Searching group j ",search_j
    list_j = ptclC_o.getParticlesWithTags(search_j)
    sum_j = len(list_j)
    if( rank == 0 ):
        if( options.verbose ): print "   patricles group j ",sum_j
    
    # Relabel segments to correspond to lists j
    for pid_j in list_j:
        #print pid_j,ptclC_o[pid_j].tagsDict["gtype"]," from u ",universe.atoms[pid_j-1].name
        universe.atoms[pid_j-1].resname = "grpj"
        universe.atoms[pid_j-1].resnum = ptclC_o[pid_j].tagsDict["chain"]  # Set resnum to chain number for inter/intra rdf's
    uni_j = universe.selectAtoms(" resname grpj ")

    n_i = uni_i.numberOfAtoms()
    n_j = uni_j.numberOfAtoms()

    coor_i = uni_i.coordinates()
    coor_j = uni_j.coordinates()

    if( rank == 0 and options.verbose ):
        print " mdanalysis groups "
        print "    uni_i  %d "%n_i

        if( options.print_grps ):
            print "  p_cnt ; number ; name ; type ; resname ; resid ; resnum ; mass ; coord "
            p_i = 0
            for a_i in  uni_i.atoms:
                p_i += 1
                print p_i,a_i.number,a_i.name,a_i.type,a_i.resname,a_i.resid,a_i.resnum,a_i.mass,coord[a_i.number]
        print "    uni_j  %d "%n_j
        if( options.print_grps ):
            p_j = 0
            for a_j in  uni_j.atoms:
                p_j += 1
                print p_j,a_j.number,a_j.name,a_j.type,a_j.resname,a_j.resid,a_j.resnum,a_j.mass,coord[a_j.number]

            
    if( rank == 0 ):
        if( options.verbose ): print " search finished "
    
    if( rank == 0 ):
        if( options.verbose ):
            # log_line += "\n  %d "%()
            log_line  = "\n  Date %s "%(str(t_i))
            log_line += "\n  Number of processors  %d "%(size)
            log_line += "\n  Particles of group i: %d "%(sum_i)
            log_line += sperator_line
            log_line += "\n id# ; type ; ff type ; ring # ; residue name ; residue # ; link id  "
            log_line += sperator_line
            #for p_i, ptcl in ptclC_o(list_i):
            #    log_line += "\n   %d %s %s %s %s %s %s "%(p_i,ptcl.type,ptcl.tagsDict["fftype"],ptcl.tagsDict["ring"],ptcl.tagsDict["resname"],ptcl.tagsDict["residue"],ptcl.tagsDict["linkid"])
            log_line += "\n  Particles of group i: %d "%(sum_j)
            log_line += sperator_line
            log_line += "\n id# ; type ; ff type ; ring # ; residue name ; residue # ; link id  "
            log_line += sperator_line
            #for p_j, ptcl in ptclC_o(list_j):
            #    log_line += "\n   %d %s %s %s %s %s %s "%(p_j,ptcl.type,ptcl.tagsDict["fftype"],ptcl.tagsDict["ring"],ptcl.tagsDict["resname"],ptcl.tagsDict["residue"],ptcl.tagsDict["linkid"])

            log_line += sperator_line
            log_line += "\n Frames "
            log_line += "\n     Initial frame  %d "%(options.frame_o)
            log_line += "\n     Step frame  %d  "%(options.frame_step)
            log_line += "\n     Final frame  %d  "%(options.frame_f)

                
            log_out.write(log_line)
            print log_line
            
	       
    #
    # If multi-core split the number of atoms in the molecule onto each core
    #
    debug = 0 
    if( debug ): print rank, size," splitOnProcs "
    split_list = True
    # Create a list of atomic indices for each processor 
    myChunk_i  = p.splitListOnProcs(list_i)
    debug = 0
    if(debug):                
        print " cpu ",rank ," has atoms ",myChunk_i[0]," - ",myChunk_i[len(myChunk_i)-1],"  \n"
	for atom_i in myChunk_i:
	    print "Processor %d has atom %d "%(rank,atom_i)
	sys.exit(" debug myChunk ")
	
    p.barrier()
         
    # Calculate rdf relate values
    n_bins = int(options.r_cut/options.bin_size)
    dmin = 0.0
    dmax = options.r_cut
    sq_r_cut = options.r_cut**2
    rdf_cnt_ij = np.zeros(n_bins+1)    
    rdf_cnt_pij = np.zeros([sum_i,n_bins+1])    
    volume_i = []
    volume_sum_i = 0.0 
    rdf_frames = 0
    proc_frame = 0

    # set up rdf
    rdf, edges = numpy.histogram([0], bins=n_bins, range=(dmin, dmax))
    rdf *= 0
    rdf = rdf.astype(numpy.float64)  # avoid possible problems with '/' later on



    if( rank == 0 ):
        if( options.verbose ): print "  Reading  %s and %s "%(options.in_xtc,options.in_gro)
        rdft_i = datetime.datetime.now()

    # Allocate distance matrix 
    dist = numpy.zeros((n_i,n_j), dtype=numpy.float64)


    # Create include matrix of pairs to include
    # include_ij = [[None]*n_j]*n_i
    # had to use numpy list since regular list was asigning values include_ij[:][p_j] instead of include_ij[p_i][p_j]
    # not sure why 
    include_ij =  numpy.zeros((n_i,n_j), dtype=numpy.int)

    p_i = -1

    # Relabel segments to correspond to lists i and j
    for a_i in  uni_i.atoms:
        p_i += 1
        p_j = -1
        for a_j in  uni_j.atoms:
            p_j += 1

            #print p_i,p_j
            #print include_ij

            add_ij = 1
            if( a_j.number <= a_i.number ):
                add_ij = 0
            #
            # Check for intra vs. inter molecular
            #
            if( options.mol_inter ):
                if( a_i.resnum  == a_j.resnum ):
                    add_ij = 0
            if( options.mol_intra ):
                if(  a_i.resnum  != a_j.resnum ):
                    add_ij = 0

            include_ij[p_i][p_j] = add_ij

    debug = False 
    if( debug):
        print " len(include_ij) ", len(include_ij)
        print " len(include_ij[0]) ", len(include_ij[0])
        print "include_ij[0][1]",include_ij[0][1]
        print include_ij[n_i-1][n_j-1]

        sys.exit(" include array size 0 ")
        for p_i in range(n_i):
            for p_j in range(n_j):

                print " for pair  ",include_ij[p_i][p_j],p_i,p_j,dist[p_i,p_j] 

        sys.exit(" include array size ")

    volume_sum_i = 0.0
    rdf_frames = 0 
    p_i_nb_cnt = 0 
    # setting the skip for the traj
    # does not seem to work 
    #universe.trajectory.skip = options.frame_step

    for ts in universe.trajectory:
        if( options.frame_o <= ts.frame ):
            if( ts.frame <= options.frame_f  or  options.readall_f  ):
                if( ts.frame%options.frame_step == 0 ):

                    print "Frame %4d with volume %f " % (ts.frame, ts.volume)
                    rdf_frames += 1 
                    volume_sum_i += ts.volume      # correct unitcell volume
                    box = ts.dimensions
                    coor_i = uni_i.coordinates()
                    coor_j = uni_j.coordinates()            
                    distance_array(coor_i,coor_j, box, result=dist)  # use pre-allocated array, box not fully correct!!

                    for p_i in range(n_i):

                        p_i_hasnieghbor = False 
                        for p_j in range(n_j):

                            #if( debug):
                            #    print " checking ",include_ij[p_i][p_j],p_i,p_j,dist[p_i,p_j] 

                            if( include_ij[p_i][p_j] == 1 ):
                                if( dist[p_i,p_j] <= options.r_cut ):
                                    bin_index = int( round( dist[p_i,p_j] / options.bin_size) )
                                    rdf_cnt_ij[bin_index] += 2
                                    rdf_cnt_pij[p_i][bin_index] += 1
                                    rdf_cnt_pij[p_j][bin_index] += 1
                                    p_i_hasnieghbor = True 

                        if( p_i_hasnieghbor ):
                            p_i_nb_cnt += 1
                            
                            
                            
                            #else:
                            #    # Set unincluded pairs to have a seperation beyond the cut off
                            #        dist[p_i,p_j] = options.r_cut + 1.0
                            #        """

                    #new_rdf, edges = numpy.histogram(dist, bins=n_bins, range=(dmin, dmax))
                    #rdf += new_rdf

        #numframes = universe.trajectory.numframes / universe.trajectory.skip

        """
        volume_sum_i /= rdf_frames    # average volume

        # Normalize RDF
        radii = 0.5*(edges[1:] + edges[:-1])
        vol = (4./3.)*numpy.pi*(numpy.power(edges[1:],3)-numpy.power(edges[:-1], 3))
        # normalization to the average density n/volume_sum_i in the simulation
        density = n_i / volume_sum_i
        # This is inaccurate when solutes take up substantial amount
        # of space. In this case you might want to use
        ## import MDAnalysis.core.units
        ## density = MDAnalysis.core.units.convert(1.0, 'water', 'Angstrom^{-3}')
        norm = density * n_i*n_j * rdf_frames
        rdf /= norm * vol

        outfile = './rdf_mda.dat'
        with open(outfile,'w') as output:
            for radius,gofr in izip(radii, rdf):
                output.write("%(radius)8.3f \t %(gofr)8.3f\n" % vars())
            p.barrier() # Barrier for MPI_COMM_WORLD

        """
            
    if( options.verbose and rank == 0 ):
	print "      Wating for all processors to finish  "                                
    p.barrier()			
    if( options.verbose and rank == 0 ):
	print "      Finding averages "
    #
    # Find averages
    #
    debug = 0 
    rdf_cnt = np.zeros(n_bins+1)   
    for bin_index in range( n_bins+1):
	# Sum rdf_cnt of each bin on each processor 
	rdf_cnt[bin_index] = p.allReduceSum(rdf_cnt_ij[bin_index])

        # print " Proc %d rdf_cnt_ij %f sum %f "% (rank,rdf_cnt_ij[bin_index],rdf_cnt[bin_index] )


    

    

    p.barrier() # Barrier for MPI_COMM_WORLD

    
    #
    # Calculate rdf results 
    # 
    total_cnts = np.sum( rdf_cnt )
    volume_sum = volume_sum_i #p.allReduceSum(volume_sum_i)
    box_vol_ave = volume_sum/float(rdf_frames)
    vol_cut = 4.0*math.pi/3.0*options.r_cut**3
    n_shperes = float(sum_i)*float(rdf_frames)
    sphere_den_j = float(total_cnts)/vol_cut/n_shperes/2.0  # N_B A^-3
    box_den_i = float(sum_i )/float(box_vol_ave)
    box_den_j = float(sum_j )/float(box_vol_ave)
    
    if( rank == 0 ):
            
	# Write output 
	#
        dat_lines ="#   Input "
	dat_lines +="\n#    Initial frame %d frame step %d " %  (options.frame_o,options.frame_step)
	dat_lines +="\n#    RDF frames %d  " %  (rdf_frames)
	dat_lines +="\n#    Bin-size %f  " % (options.bin_size)
	dat_lines +="\n#    Cut-off %f  " % (options.r_cut)
	dat_lines +="\n#    Total_cnts %d  " % (total_cnts)
	dat_lines +="\n#    N_i %d " % (sum_i )
	dat_lines +="\n#    N_j %d " % (sum_j )
	dat_lines +="\n#    Box averages " 
	dat_lines +="\n#      Average Box Volume %f " % ( box_vol_ave) 
	dat_lines +="\n#      Box density i %f N A^-3 " % (box_den_i )
	dat_lines +="\n#      Box density j %f N A^-3 " % (box_den_j )
	dat_lines +="\n#    Sphere averages " 
	dat_lines +="\n#      N spheres %d " % (n_shperes )
	dat_lines +="\n#      Sphere volume  %f A^3 " % (vol_cut )
	dat_lines +="\n#      Average Sphere density j  %f N A^3 " % (sphere_den_j )
	dat_lines +="\n#    "
	dat_lines +="\n# r (A) ; g_boxs ; g_sphere ; count(r)/frame  ; count_sum/frame/n_i ;  count_sum/frame/n_j ; count_sum/frame/(n_i+n_j) ;  dr vol ;  dr vol(aprox) ; prob_i(<r) ;prob_j (<r)  ; ave_nn_i (<r)  ; ave_nn_i (<r)"
	dat_lines +="\n#   1        2         3             4                5                      6                      7                        8            9            10           11             12               13  "
        if( options.verbose ):
            print dat_lines
        dat_file = options.output_id + ".dat"
        dat_out = open(dat_file,"w") 
        dat_out.write(dat_lines)
        #
	#                bin_index , r_val , dr_cnt_norm      , dr_vol,  dr_vol_apx,     sphere_g, box_g
	cnt_sum_i = 0.0 
	cnt_sum_j = 0.0 
	cnt_sum_ij = 0.0

        p_hasnn_i = np.zeros(sum_i)    # Has at least 1 NN under distance r
        p_hasnn_j = np.zeros(sum_j)    
        
	for bin_index in range( 1,n_bins):
	    
	    r_val = options.bin_size*float(bin_index)
	    r_in = r_val - options.bin_size*0.5
	    r_out = r_val + options.bin_size*0.5
    
	    dr_cnt = float( rdf_cnt[bin_index] )
	    dr_cnt_norm =     dr_cnt    /float(rdf_frames)
            cnt_sum_i += dr_cnt_norm/float(sum_i)/2.0
            cnt_sum_j += dr_cnt_norm/float(sum_j)/2.0
            cnt_sum_ij += dr_cnt_norm/float(sum_j+sum_i)
	    dr_vol = 4.0*math.pi/3.0*( r_out**3 - r_in**3 )
	    dr_vol_apx = 4.0*math.pi*(  r_val**2 )
	    
	    dr_rho = dr_cnt_norm/dr_vol
	    sphere_g = dr_rho/sphere_den_j/float( sum_i )
	    box_g = dr_rho/box_den_j/float( sum_i )

            # Find probality of a particle have nearest neighbor under a given length
            
            nn_cnt_i = 0
            nn_cnt_j = 0 
            for p_i in range(n_i):
                p_hasnn_i[p_i] += rdf_cnt_pij[p_i][bin_index]
                if( p_hasnn_i[p_i] > 0 ):
                    nn_cnt_i  += 1
                    
            prob_i = float(nn_cnt_i)/float(sum_i)                 
            nn_i = float(np.sum(p_hasnn_i))/float(rdf_frames)/float(sum_i)                 
            for p_j in range(n_j):
                p_hasnn_j[p_j] += rdf_cnt_pij[p_j][bin_index]
                if( p_hasnn_j[p_j] > 0 ):
                    nn_cnt_j  += 1
            prob_j = nn_cnt_j/float(sum_j)                 
            nn_j = float(np.sum(p_hasnn_j))/float(rdf_frames)/float(sum_j)                 


     
	    dat_out.write("\n  %f %f %f %f %f %f %f %f %f  %f %f  %f %f " % (r_val,box_g,sphere_g,dr_cnt_norm,cnt_sum_i,cnt_sum_j,cnt_sum_ij,dr_vol,dr_vol_apx,prob_i,prob_j,nn_i,nn_j) )
	    #dat_out.write("\n  %f %f %f %f %f %f %f %f %f  %f %f  %f %f " % (r_val,box_g,sphere_g,dr_cnt_norm,cnt_sum_i,cnt_sum_j,cnt_sum_ij,dr_vol,dr_vol_apx,prob_i,prob_j,np.sum(p_hasnn_i[p_i]),np.sum(p_hasnn_i[p_i])) )
        
        t_f = datetime.datetime.now()
        dt_sec  = t_f.second - t_i.second
        dt_min  = t_f.minute - t_i.minute
        if ( dt_sec < 0 ): dt_sec = 60.0 - dt_sec
        if ( dt_min < 0 ): dt_min = 60.0 - dt_min
        if ( dt_sec > 60.0 ): dt_sec = dt_sec - 60.0 
        log_line="\n  Finished time  " + str(t_f)
        log_line+="\n  Computation time "+str(dt_min) + " min "+str(dt_sec)+" seconds "
        if( options.verbose ):
            print log_line
        log_out.write(log_line)

	dat_out.close()
	log_out.close()
	    

if __name__=="__main__":
    main()
   