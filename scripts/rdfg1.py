#! /usr/bin/env python
"""

Radial distribution  code

 length - Angstroms
 mass   - AMU
 volume - Angstroms^3

    # g_ij(r) = n_j(r_ij)/ (rho_j 4 pi r^2 dr )
    g_ij(r) = n_j(r_ij)/ (rho_j 4/3 pi( r_out^3 - r_in^3)

    rho_j = N_j / V_ave

    g(r) = n(r) /( rho dV )

    n(r) = 1/Ni sum_i^{N_i} sum_j^{N_j} \gamma( r - r_{ij})

    g(r) = 1/( dV Ni )  sum_i^{N_i}    [   sum_j^{N_j} \gamma( r - r_{ij}) / rho_j(i) ]

    Regular density
    g(r) =  1/( dV Ni )  sum_i^{N_i}    [   sum_j^{N_j} \gamma( r - r_{ij}) / (  sum_j^{N_j} \gamma( allowed pair ij )/<V> )  ]
    g(r) =  <V>/( dV Ni )  sum_i^{N_i}    [   sum_j^{N_j} \gamma( r - r_{ij}) /   sum_j^{N_j} \gamma(  pair ij ) ]
    
    True density 
    g(r) =  1/( dV Ni )  sum_i^{N_i}    [   sum_j^{N_j} \gamma( r - r_{ij}) / (  sum_j^{N_j} \gamma( allowed pair ij )/<V> )  ]
    g(r) =  <V>/( dV Ni )  sum_i^{N_i}    [   sum_j^{N_j} \gamma( r - r_{ij}) /   sum_j^{N_j} \gamma( allowed pair ij ) ]


    Nj_i = sum_j^{N_j} \gamma(  pair ij )
    rdf_cnt_p = sum_f^{N_frames}   sum_j^{N_j} \gamma( r - r_{ij})
    sum_j^{N_j} \gamma( r - r_{ij})  = rdf_cnt_p/N_frames
 
"""


__author__ = "Travis W. Kemper"
__version__ = "0.3"
__email__ = "travis.kemper.w@gmail.com"
__status__ = "Beta"


import   os, os.path, sys , copy ,shutil, logging, math, json, csv 
import numpy as np
from datetime import datetime
from optparse import OptionParser

from streamm import *

from MDAnalysis import *
from MDAnalysis.core.distances import * ##distance_array


def reduce_bins(bin_r,bin_r_nn):
    #
    # Reduce bins 
    #
    for bin_index in range( len(bin_r)):
        # Sum rdf_cnt of each bin on each processor 
        cnt = p.allReduceSum(bin_r[bin_index])
        bin_r[bin_index] = cnt 
        cnt_nn = p.allReduceSum(bin_r_nn[bin_index])
        bin_r_nn[bin_index] = cnt_nn
    p.barrier() # Barrier for MPI_COMM_WORLD
    return bin_r,bin_r_nn


def calc_rdf(N_i,N_j,bin_r,bin_r_nn,volumes,bin_size,rdf_tag,options,p):
        '''
        Calculate rdf results
         
        n_ij(r_ij) = bined counts in (r_ij)

        n_j (r_ij) = n_ij(r_ij)/N_i  # Number of nieghbor atoms j 
         
        rho_j = N_j / V_ave   # 1/A^3

        g_ij(r) = n_j(r_ij)/ [rho_j 4/3 pi( r_out^3 - r_in^3)]
        
        g(r) =  <V>/( dV Ni )  sum_i^{N_i}    [   sum_j^{N_j} \gamma( r - r_{ij}) /   sum_j^{N_j} \gamma(  pair ij ) ]

        n_ij = \gamma( r - r_{ij})
         
        dV =  4/3 pi( r_out^3 - r_in^3)
        
        '''
        rank = p.getRank()
        size = p.getCommSize()
        
        n_frames = len(volumes)
        n_bins = len(bin_r)
        total_cnts = np.sum( bin_r )
        total_nn_cnts = np.sum( bin_r_nn )
        box_vol_ave = np.mean(volumes)
        cnt_sum_j = 0.0 
        nn_cnt_sum_j = 0.0

        rdf = []

        time_i = datetime.now()
        dat_lines =    "# Date: %s \n"%(time_i)
        dat_lines +="# Frames: \n"
        dat_lines +="#   Initial  %d \n" %  (options.frame_o)
        dat_lines +="#   Step %d \n" %  (options.frame_step)
        dat_lines +="#   Final  %d  \n" %  (options.frame_step)
        dat_lines +="#   Nproc  %d  \n" %  (size)
        dat_lines +="# Tag %s \n"%(rdf_tag)
        dat_lines +="#   N_i %d \n"%(N_i)
        dat_lines +="#   N_j %d \n"%(N_j)
        dat_lines +="#   Frames %d \n"%(n_frames)
        dat_lines +="#   n_bins %d \n"%(n_bins)
        dat_lines +="#   total_cnts %f \n"%(total_cnts)
        dat_lines +="#   total_nn_cnts %f \n"%(total_nn_cnts)
        dat_lines +="#   box_vol_ave %s \n"%(str(box_vol_ave))
        dat_lines +="#   r  - center position of bin [0] \n"
        dat_lines +="#   g_r_box  - g(r) using average box volume [1] \n"
        dat_lines +="#   g_r_nn_box  - first nearest neighbor g(r) using average box volume [2] \n"
        dat_lines +="#   nb_r  - neighbor count of i at r  [3]\n"
        dat_lines +="#   nb_sum  - sum neighbor count of i < r  [4]\n"
        dat_lines +="#   nn_nb_r  - first nearest neighbor count of i at r  [5]\n"
        dat_lines +="#   nn_nb_sum  - sum first nearest neighbor count of i < r  [6]\n"
        dat_lines +="# r , g_r_box, g_r_nn_box, nb_r ,nb_sum ,nn_nb_r ,nn_nb_sum  \n"        
        for bin_index in range(n_bins):
            r_val = options.bin_size*float(bin_index)
            dr_sq = r_val*r_val
            r_in = r_val - options.bin_size*0.5
            r_out = r_val + options.bin_size*0.5
            dr_vol = 4.0*math.pi/3.0*( r_out**3 - r_in**3 )
            cnt_r_frame = float( bin_r[bin_index] ) /float(n_frames) 
            nn_cnt_r_frame = float( bin_r_nn[bin_index] ) /float(n_frames)
            # n(r)  = 1/N_i  sum_j^{N_j} \gamma( r - r_{ij}) 
            nb_cnt = cnt_r_frame/float( N_i )
            cnt_sum_j += nb_cnt
            nn_nb_cnt = nn_cnt_r_frame/float( N_i )
            nn_cnt_sum_j += nn_nb_cnt
            # g(r) = <V> * n(r) / dV 
            g_r_box = box_vol_ave*nb_cnt/dr_vol/float( N_j )
            g_r_nn_box = box_vol_ave*nn_nb_cnt/dr_vol/float( N_j )
            
            dat_lines += "  %12.4f %12.4f %12.4f %12.4f %12.4f %12.4f %12.4f \n"%(r_val,g_r_box, g_r_nn_box,nb_cnt,cnt_sum_j,nn_nb_cnt,nn_cnt_sum_j)

            rdf.append([r_val,g_r_box, g_r_nn_box,nb_cnt,cnt_sum_j,nn_nb_cnt,nn_cnt_sum_j])

        # Write data file 
        dat_file = rdf_tag + ".dat"
        logger.info("file: output %s %s "%('rdf_dat',dat_file))
        dat_out = open(dat_file,"w") 
        dat_out.write(dat_lines)
        dat_out.close()            

        return rdf
    
def pdf_rdf(rdf_tag,rdf_i):
    '''
    Write pdf of the rdf
    '''
    import matplotlib
    #matplotlib.use('pdf')
    import matplotlib.pyplot as plt
    from matplotlib import gridspec

    n_pannels = 1
    fig, ax = plt.subplots(n_pannels)
    ax.set_ylabel(r'$g(r)$ ',fontsize=fontsz)
    ax.plot(rdf_i[:,0],rdf_i[:,1])
    
    #fig.subplots_adjust(hspace=0)
    #fig.set_size_inches(8.0, 12.0)
    fig.savefig("rdf_%s.pdf"%(rdf_tag),format='pdf')
    plt.close(fig)



def singleframe_gpairs(struc_o,group_id,glist_i,glist_j,pairvalue_ij,bin_size,r_cut,rank):
    '''
    Bin distances between particle pairs
    
    Add size to cutoff
    Assumes cut off is evenly divisable by bin_size 
             |                      |
        -bin_size/2.0   r_cut   +bin_size/2.0 
    '''
    
    r_cut += bin_size/2.0 
    
    N_i = len(glist_i)
    N_j = len(glist_j)
    #    
    groupset_i = struc_o.groupsets[group_id]
    #
    probabilityperpair = 1
    #
    # Calculate rdf relate values
    n_bins = int(r_cut/bin_size) + 1 
    bin_r = np.zeros(n_bins)    
    bin_r_nn = np.zeros(n_bins)    # Nearest neighbor count 
    bin_r_pp = np.zeros(n_bins)    

    volumes  = []
    rdf_frames = 0 


        npos_i = groupset_i.properties['cent_mass']
        npos_j = groupset_i.properties['cent_mass']        
        npos_ij,nd_ij = struc_o.lat.delta_npos(npos_i,npos_j)
        # 
        for ref_i in range(N_i):
            a_i_hasnieghbor = False
            r_ij_nn = r_cut   # Nearest Neighbor distance  
            g_i = glist_i[ref_i]
            for ref_j in range(N_j):
                if(  pairs_ij[ref_i][ref_j] > 0.0 ):
                    dr_ij =  nd_ij[ref_i,ref_j]
                    if(  dr_ij <= r_cut ):
                            # bin distance =
                            bin_index = int( round( dr_ij / bin_size) )
                            #
                            # print " dist / bin / bin_sit", dist[ref_i,ref_j],bin_index,bin_size*float(bin_index)
                            #
                            bin_r[bin_index] += probabilityperpair
                            # Find nearest neighbor distance 
                            a_i_hasnieghbor = True
                            if( dr_ij < r_ij_nn ):
                                r_ij_nn = dr_ij
                                p_ij_nn = pairs_ij[ref_i][ref_j]
                            # 
                            if( close_contacts ):
                                g_j = glist_i[ref_j]
                                dr_pi_pj = groupset_i.dr_particles(g_i,g_j,r_cut)
                                bin_pp_index = int( round( dr_pi_pj / bin_size) )
                                bin_r_pp[bin_pp_index] += probabilityperpair

            # Record nearest neighbor distance 
            if( a_i_hasnieghbor ):
                bin_nn_index = int( round( r_ij_nn /bin_size) )
                bin_r_nn[bin_nn_index] += p_ij_nn  



    return bin_r,bin_r_nn,bin_r_pp,volumes



def distbin_gpairs(struc_o,group_id,glist_i,glist_j,pairvalue_ij,gro_file,dcd_file,f_o,f_step,f_f,readall_f,bin_size,r_cut,rank):
    '''
    Bin distances between particle pairs
    
    Add size to cutoff
    Assumes cut off is evenly divisable by bin_size 
             |                      |
        -bin_size/2.0   r_cut   +bin_size/2.0 
    '''
    
    r_cut += bin_size/2.0 
    
    N_i = len(glist_i)
    N_j = len(glist_j)
    

    groupset_i = struc_o.groupsets[group_id]

    probabilityperpair = 1
    # 
    # Read in trajectory 
    #
    universe =  Universe(gro_file,dcd_file)
    
    if( readall_f ):
        f_f = len(universe.trajectory)
        
    
    # Allocate distance matrix 
    dist_pp = np.zeros((N_i,N_j), dtype=np.float64)
    # Calculate rdf relate values
    n_bins = int(r_cut/bin_size) + 1 
    bin_r = np.zeros(n_bins)    
    bin_r_nn = np.zeros(n_bins)    # Nearest neighbor count 
    volumes  = []
    rdf_frames = 0 
    for ts in universe.trajectory:
        if( f_o <= ts.frame ):
            if( ts.frame <= f_f  ):
                if( ts.frame%f_step == 0 ):
                    rdf_frames += 1
                    logger.info("Calculation %d frame %d/%d on proc %d" % (rdf_frames,ts.frame, f_f,rank))
                    volumes.append(ts.volume)     # correct unitcell volume
                    box = ts.dimensions
                    
                    coor_i = uni_i_p.coordinates()
                    


                    npos_i = groupset_i.properties['cent_mass']
                    npos_j = groupset_i.properties['cent_mass']        
                    npos_ij,nd_ij = struc_o.lat.delta_npos(npos_i,npos_j)
                    
                    # distance_array(coor_i,coor_j, box, result=dist)  
                    for ref_i in range(N_i):
                        a_i_hasnieghbor = False
                        r_ij_nn = r_cut   # Nearest Neighbor distance  
                        for ref_j in range(N_j):
                            # logger.debug(" Checking pair %d - %d "%(ref_i,ref_j))
                            if(  pairvalue_ij[ref_i][ref_j] > 0.0 ):
                                if(  dist[ref_i,ref_j] <= r_cut ):
                                    # bin distance =
                                    bin_index = int( round( dist[ref_i,ref_j] / bin_size) )

                                    # print " dist / bin / bin_sit", dist[ref_i,ref_j],bin_index,bin_size*float(bin_index)

                                    
                                    bin_r[bin_index] += probabilityperpair
                                    # Find nearest neighbor distance 
                                    a_i_hasnieghbor = True
                                    if( dist[ref_i,ref_j] < r_ij_nn ):
                                        r_ij_nn = dist[ref_i,ref_j]
                                        p_ij_nn = pairvalue_ij[ref_i][ref_j]

                        # Record nearest neighbor distance 
                        if( a_i_hasnieghbor ):
                            bin_nn_index = int( round( r_ij_nn /bin_size) )
                            bin_r_nn[bin_nn_index] += p_ij_nn  
    # Free memory
    del universe
    del dist
    
    return bin_r,bin_r_nn,volumes

    
def grdfs(tag,options,p):
    #
    # MPI setup
    #
    rank = p.getRank()
    size = p.getCommSize()
    #
    if( rank == 0 ):
        logging.info('Running on %d procs %s '%(size,datetime.now()))
        logging.info('Reading structure files ')
    #
    logging.debug(" proc %d of %d "%(rank,size))
    if( rank == 0 ):
        logger.info("Reading in structure for %s from %s "%(tag,options.cply))
    #
    # Read cply file 
    #
    strucC = buildingblock.Container()
    strucC.read_cply(options.cply)
    # 
    # Calculate bulk properties 
    # 
    strucC.bonded_nblist.build_nblist(struc_o.particles,struc_o.bonds )
    strucC.calc_mass()
    strucC.calc_volume()
    strucC.calc_density()
    prop_dim = strucC.lat.n_dim
    den_gcm3 = units.convert_AMUA3_gcm3(strucC.density)
    if( rank == 0 ):
        logger.info("Structure %s mass %f volume %f density %f "%(tag,strucC.mass,strucC.volume,den_gcm3))
        logger.info("Breaking molecules into separate simulations")
    if( rank == 0 ):
        logger.info("Selecting groups %s "%(options.group_id))
    # 

    group_i_id = 'mol'
    strucC.group_prop(group_i_id,group_i_id)
    groupset_mol = c.strucC.groupsets[group_i_id]
    groupset_mol.calc_cent_mass()
    groupset_mol.calc_radius()
    groupset_mol.group_pbcs()
    
    # Write .gro file for MDanalysis 
    # 
    gro_file = "%s.gro"%(tag)
    if( rank == 0 ):
        # Write gromacs gro file for MDANALYSIS 
        gromacs_i  = gromacs.GROMACS(tag)
        gromacs_i.add_strucC(strucC)
        gromacs_i.write_gro(gro_file=gro_file)
    p.barrier()
    #
    # Read lists
    #
    if( len(options.list_i) > 0 ):
        lfile = open(options.list_i,'rb')
        t_i = lfile.readlines()
        lfile.close()
        list_i = [int(pkey) for pkey in  t_i]
    else:
        list_i = strucC.particles.keys()
    # 
    #
    # Select considered particles 
    #
    if( rank == 0 ):
        logger.info("Grouping by %s "%(options.group_id))        
    struc_o.group_prop(options.group_id,options.group_id,particles_select=list_i)
    groupset_i = struc_o.groupsets[options.group_id]
    groupset_i.calc_cent_mass()
    groupset_i.calc_radius()        
    #
    # Read lists
    #
    if( len(options.glist_i) > 0 ):
        lfile = open(options.glist_i,'rb')
        t_i = lfile.readlines()
        lfile.close()
        glist_i = [int(pkey) for pkey in  t_i]
    else:
        glist_i = groupset_i.groups.keys()
    # 
    if( len(options.glist_j) > ):
        lfile = open(options.glist_j,'rb')
        t_j = lfile.readlines()
        lfile.close()
        glist_j = [int(pkey) for pkey in  t_j]
    else:
        glist_j = self.groups.keys()
        
        
    sub_cc = find_DAres(calc_j)
    #
    #sub_j =  strucC.pd_df[sub_heavy & D1 ]
    # Get glist and pairs
    #pairvalue_ij = groupset_i.find_pairs(glist_i,list_j,mol_inter=options.mol_inter,mol_intra=options.mol_intra)
    #
    #Calculate rdfs  
    #
    # gr2_rdf = rdf(gr2_tag,gr2_i,gr2_i_p,gr2_j,gr2_pairs,gro_file,options,p)
    #
    logger.info(" Calculating close_contacts %s "%(tag))
    
    # for tag_i,calc_j in proj_j.calculations.iteritems():
    #os.chdir(calc_j.dir['scratch'])
    gdr_ij = dict()
    gdr_ij['g_i'] = []
    gdr_ij['g_j'] = []
    gdr_ij['dcm_ij'] = []
    gdr_ij['dr_pi_pj'] = []
    
    
    pairs_df = pd.read_csv('pairs_residue.csv')


    for (g_i,g_j,dcm_ij) in pairs_df[['g_i','g_j','dcm_ij']].values:
        dr_pi_pj = groupset_i.dr_particles(g_i,g_j,r_cut,sub_cc.index)
        gdr_ij['g_i'].append(g_i)
        gdr_ij['g_j'].append(g_j)
        gdr_ij['dcm_ij'].append(dcm_ij)
        gdr_ij['dr_pi_pj'].append(dr_pi_pj)
    
    calc_j.df_gdr_ij = pd.DataFrame(gdr_ij)
    file_name = "gdr_ij.csv"
    calc_i.df_gdr_ij.to_csv(file_name, sep=',', encoding='utf-8')    
        
    
    #bin_r,bin_r_nn,volumes = distbin_pairs(glist_i,glist_j,pairs_ij,gro_file, options.dcd,options.frame_o,options.frame_step,options.frame_f,options.readall_f,options.bin_size,options.r_cut,rank)
    #bin_r,bin_r_nn,volumes = singleframe_gpairs(struc_o,options.group_id,glist_i,glist_j,pairvalue_ij,options.bin_size,options.r_cut,rank)
    
    p.barrier()
    
            
if __name__=="__main__":
    
    usage = "usage: %prog tag \n"
    parser = OptionParser(usage=usage)
    parser.add_option("--cply", dest="cply", type="string", default="in.cply", help="Input cply file")
    parser.add_option("--list_i", dest="list_i", type="string", default="list_i", help="Input list file")
    parser.add_option("--list_j", dest="list_j", type="string", default="list_j", help="Input list file")
    parser.add_option("--dcd", dest="dcd", type="string", default="prod1_dump.dcd", help="Input dcd file")
    parser.add_option("--mol_inter",dest="mol_inter", default=False,action="store_true", help="Use only inter molecular rdf's ")
    parser.add_option("--mol_intra",dest="mol_intra", default=False,action="store_true", help="Use only intra molecular rdf's")
    parser.add_option("--groups_inter",dest="groups_inter", default=True,action="store_true", help="Use only inter group rdf's")
    parser.add_option("--group_id", dest="group_id", type="string", default="mol", help="Group id ")
    # parser.add_option("--truedensity",dest="truedensity", default=False,action="store_true", help="Use the true density of group j, this makes inter/intra molecular rdfs not components of the total rdf but true independent rdfs")
    
    
    # Frames
    parser.add_option("--frame_o", dest="frame_o", type=int, default=1, help=" Initial frame to read")
    parser.add_option("--frame_f", dest="frame_f", type=int, default=10000, help=" Final frame to read")
    parser.add_option("--frame_step", dest="frame_step", type=int, default=1, help=" Read every nth frame ")
    parser.add_option("--readall_f", dest="readall_f", default=True,action="store_true", help=" Read to end of trajectory file (negates frame_f value)")
    # Bins
    parser.add_option("--r_cut", dest="r_cut", type=float, default=20.0, help=" Cut off radius in angstroms ")
    parser.add_option("--bin_size", dest="bin_size", type=float, default=0.10, help=" Bin size in angstroms")
    # 
    (options, args) = parser.parse_args()
    #
    # Initialize mpi
    #
    p = mpiBase.getMPIObject()


    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    #logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # 
    # logging.basicConfig(level=logging.DEBUG,
    #                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    #                datefmt='%m-%d %H:%M',
    #                filemode='w')
    if( len(args) < 1 ):
        calc_tag = 'rdf'
    else:
        calc_tag =  args[0]
        
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    #
    hdlr = logging.FileHandler('%s.log'%(calc_tag),mode='w')
    hdlr.setLevel(logging.INFO)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    #
    start_time = datetime.now()
    if( p.getRank() == 0 ):
        logger.info('Started %s '%(start_time))
    #
    grdfs(calc_tag,options,p)
    
    finish_time = datetime.now()
    delt_t = finish_time - start_time
    
    if( p.getRank() == 0 ):
        logger.info('Finished %s in %f seconds '%(finish_time,delt_t.seconds))
