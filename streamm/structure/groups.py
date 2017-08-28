#! /usr/bin/env python
"""
This module defines the classes relating to groups of atoms within a container
"""

__author__ = "Travis W. Kemper"
__version__ = "0.3"
__email__ = "travis.kemper.w@gmail.com"
__status__ = "Beta"


class Member(object):
    """
    Sets of particles within a structureContainer 
    """

    def __init__(self,strucC,verbose=False):
        """
        Constructor
        """
        # Set pointer for easy reference 
        self.strucC = strucC
        self.n_dim = strucC.lat.n_dim
        #self.pid_list  = []
        self.tag = 'blank'
        self.mol = 0
        self.residue = 0
        self.resname = 'RES'
        # 
        self.pkeys  = []
        self.gkey = int(0)                   # group number/key
        self.bonded_nblist = NBlist()        # Creates nblist object for  bonded particles
        self.nonbonded_nblist = NBlist()     # Creates nblist object for nonbonded particles
        # 
        # Group properties
        # 
        self.cent_mass = np.zeros( self.n_dim)
        self.total_mass = 0.0  # NoteTK this should be .mass
        self.radius = 0.0
        self.r_gy_sq = 0.0
        self.Q_mn = np.zeros([self.n_dim,self.n_dim])
        self.Rgy_eignval = np.zeros( self.n_dim)
        self.A_sphere_num = 0.0
        self.A_sphere_dem = 0.0
        self.A_sphere = 0.0
        self.dl_sq = 0.0 #  np.zeros( self.n_dim)
        
    def __del__(self):
        """
        Destructor for Group object
        """
        del self.tag
        del self.mol
        del self.residue
        del self.resname
        # 
        del self.n_dim 
        del self.pkeys
        del self.gkey
        del self.bonded_nblist
        del self.nonbonded_nblist
        del self.cent_mass
        del self.total_mass
        del self.radius
        del self.r_gy_sq
        del self.Q_mn
        del self.Rgy_eignval
        del self.A_sphere_num
        del self.A_sphere_dem
        del self.A_sphere
        del self.dl_sq


    def write_xyz(self, xyz_file=''):
        '''
        Write a structure  to an xyz file

        Args:
            xyz_file    (str) xyz file tag
            
        Reutrns:
            null
            
        '''
        if( len(xyz_file) == 0 ):
            xyz_file = "%s.xyz"%(self.tag)

        F = open(xyz_file,"w")

        # Loop over structures
        F.write(" %d \n" % len(self.pkeys) )
        F.write("group  %s \n"%(self.tag))
        for pkey_i in self.pkeys:
            particle_i = self.strucC.particles[pkey_i]
            pos_i = self.strucC.positions[pkey_i]
            F.write( " %5s %16.8f %16.8f %16.8f \n"  % (particle_i.tag ,float(pos_i[0]), float(pos_i[1]),float(pos_i[2]) ) )
        F.close()

        return

  
    def centerofmass(self ):
        """
        Calculate the center of mass

        Center of mass of the molecule
        
        math:: r_{cmas} = \frac(\sum_i r_i*mass_i)(\sum_i mass_i) 

        where math::`r_i` is the position of particle math::`i` and math::`mass_i` is it's mass 

        """
        #
        # Intialize center of mass list 
        self.cent_mass = np.zeros( self.n_dim)
        self.total_mass = 0.0
        #
        for pkey_i in self.pkeys:
            particle_i = self.strucC.particles[pkey_i]
            r_i = self.strucC.positions[pkey_i]
            mass_i = particle_i.mass
            self.total_mass += mass_i
            for dim in range(self.n_dim):
                self.cent_mass[dim] += mass_i*r_i[dim]
        # Normalize
        for dim in range(self.n_dim):
            self.cent_mass[dim] = self.cent_mass[dim]/self.total_mass
        #
        return

    def calc_radius(self):
        """
        Calculate the maximum radius

        and


        Radius of math::`gyration^2` (r_gy_sq)

        r_gy_sq = \frac(\sum_i  (r_i - r_cmas )^2)( \sum_i)
                     


        Gyration tensor

        Q(m,n) = \frac( \sum_i  (r_i_m - r_cmas_m ) (r_i_n - r_cmas_n ) )( \sum_i )

        where m amd n are component of the r vector

        https://arxiv.org/pdf/1009.4358.pdf
        
        """
        # Initialize sums 
        self.radius = 0.0
        self.r_gy_sq = 0.0
        self.Q_mn = np.zeros([self.n_dim,self.n_dim])
        
        
        for pkey_i in self.pkeys:
            particle_i = self.strucC.particles[pkey_i]
            r_i = self.strucC.positions[pkey_i]
            dr_cmass = self.strucC.lat.deltasq_pos_c(r_i,self.cent_mass)
            dot_dr_ij = dr_cmass.dot(dr_cmass)
            if( dot_dr_ij > self.radius  ):
                self.radius = dot_dr_ij
            # \sum_i  (r_i_n - r_cmas_n ) (r_i_m - r_cmas_m )
            for d_m in range(self.n_dim):
                for d_n in range(self.n_dim):
                    self.Q_mn[d_m,d_n] += dr_cmass[d_m]*dr_cmass[d_n]
        # Normalize
        self.radius = np.sqrt(self.radius)
        for d_m in range(self.n_dim):
            for d_n in range(self.n_dim):
                self.Q_mn[d_m,d_n]  = self.Q_mn[d_m,d_n]  /float( len(self.pkeys))
                
        for d_m in range(self.n_dim):
             self.r_gy_sq += self.Q_mn[d_m,d_m]
        return

    def calc_asphericity(self):
        """
        Calculate the eigen values of the Gyration tensor and the Asphericity

         Soft Matter, 2013, 9, 3976-3984
         
         
         A_sphere = \frac{ (\lambda_1 - \lambda_3)^2 + (\lambda_2 - \lambda_3)^2 - (\lambda_1 - \lambda_2)^2 }{ (\lambda_1 + \lambda_2+ \lambda_3)^2  }
         
        """

        eign_raw = np.linalg.eigvals(self.Q_mn)
        # Sort eignvalues 
        eign_raw.sort()
        Rgy_eignval = [x for x in reversed(eign_raw)]
        num = (Rgy_eignval[0] - Rgy_eignval[2])**2 + (Rgy_eignval[1] - Rgy_eignval[2])**2 + (Rgy_eignval[0] - Rgy_eignval[1])**2
        dem = (Rgy_eignval[0] + Rgy_eignval[1] + Rgy_eignval[2])**2
        # 
        # Add properties to property dictionary
        # 
        self.Rgy_eignval = Rgy_eignval
        self.A_sphere_num = num
        self.A_sphere_dem = dem
        if( dem != 0.0 ):
            self.A_sphere = num/(2.0*dem)
        else:
            self.A_sphere = 0.0 

    def calc_dl(self ):
        """
        Calculate the maximum end to end distance 

        """

        # Intialize center of mass list 
        self.dl_sq = 0.0 #  np.zeros( self.n_dim)
        
        for pkey_i in self.pkeys:
            particle_i = self.strucC.particles[pkey_i]
            r_i = self.strucC.positions[pkey_i]
            for pkey_j in self.pkeys:
                particle_j = self.strucC.particles[pkey_j]
                r_j = self.strucC.positions[pkey_j]
                dr_ij = self.strucC.lat.deltasq_pos_c(r_i,r_j)
                dot_dr_ij = dr_ij.dot(dr_ij)
                if( dot_dr_ij > self.dl_sq ): self.dl_sq = dot_dr_ij
                          
        

    def hterm_group(self,debug=False):
        """
        Hydrogen terminate group  

        (j)    (l)
            \  /
            (i)    - 109.5 deg
            /  \
          (k)   (m)
          
        Hydrogens will be added to sp3 carbons in a tetrahedral configuration

            ^         (l)
            |        /  |
       A    |   C  /    | 
            |    /      |
            |  /        |
            (i) -------->  
                B

        If atom i is bonded to two other atoms j and k
        r_ij = position_i - position_j
        r_ik = position_i - position_k
            A = r_ij x r_ik
            B = r_ij + r_ik

        For the angle (l)(i)(m) to be 109.5

        |A| = sin(  109.5/2 ) |C|
        |B| = cos(  109.5/2 ) |C|

        By scaling A and B they can be added to get the bonds between i and l and m

        r_il = A + B
        r_im = -A + B

        """


        latticevec = self.strucC.lat._matrix


        hb_length = 1.09
        hb_angle =  109.5
        
        # tetrahedral angle cos and sin components 
        tet_angle = np.deg2rad(hb_angle )
        tet_sin = np.sin(tet_angle) * hb_length
        tet_cos = np.cos(tet_angle) * hb_length

        
        tetrahedral_angle = np.deg2rad(hb_angle/2.0 )
        scale_vcross = np.sin(tetrahedral_angle) * hb_length
        scale_vadd = np.cos(tetrahedral_angle) * hb_length

        pt_H = Atom('H')
        pt_H.properties = periodictable.element_number(1)
        pt_H.properties["fftype"] = "HC"
        pt_H.properties["resname"] = "TERM"
        pt_H.properties["mol"] = self.properties["mol"] 
        pt_H.properties["residue"] = self.properties["residue"] 

        original_ref_mod = []
        sub_ref_mod = []
        pid_i_mod = 0

        Htermed = self.strucC.getSubStructure(self.pkeys,tag='%s_hterm'%(self.tag))

        for pkey_i in Htermed.particles.keys():
            NNAB_i = Htermed.bonded_nblist.calc_nnab(pkey_i)  # Group neighbors
            pkey_o = self.pkeys[pkey_i]
            NNAB_o = self.strucC.bonded_nblist.calc_nnab(pkey_o)# Structure container neighbors 
            if( NNAB_o != NNAB_i):
                # If there has been neighbors removed terminate 
                dB = NNAB_o - NNAB_i
                particle_i = Htermed.particles[pkey_i]
                r_i = Htermed.positions[pkey_i]
                r_ij_array = []
                for pkey_j in Htermed.bonded_nblist.getnbs(pkey_i):
                    r_j =  Htermed.positions[pkey_j]
                    r_ij = Htermed.lat.deltasq_pos(r_i,r_j)
                    r_ij_array.append(r_ij)

                    # print r_i,r_j,r_ij
                
                if( len(r_ij_array) != NNAB_i ):
                    error_line = " len(r_ij_array) {} != NNAB_i {} in groups.hterm() ".format(len(r_ij_array),NNAB_i)
                    sys.exit(error_line)
                    
                print ">hterm_group",NNAB_o,dB 
                
                if( NNAB_o == 3 and dB == 1 ):
                    logger.debug("Adding hterm_conjugated sp2")
                    pos_j = hterm_Csp2(hb_length,r_i,r_ij_array)
                    pt_H.properties["fftype"] = "HA"
                    Htermed.add_partpos(pt_H,pos_j,deepcopy = True)
                    p_j = Htermed.n_particles -1

                    Bond_iH = Bond(pkey_i,p_j)
                    Htermed.add_bond(Bond_iH)

                elif( NNAB_o == 4 and dB == 1 ):
                    
                    logger.debug("Adding hterm_sp3 ")
                    pos_j = hterm_Csp3(hb_length,r_i,r_ij_array)
                    pt_H.properties["fftype"] = "HC"
                    Htermed.add_partpos(pt_H,pos_j,deepcopy = True)
                    p_j = Htermed.n_particles -1 
                    Bond_iH = Bond(pkey_i,p_j)
                    Htermed.add_bond(Bond_iH)

                elif( NNAB_o == 3 and dB == 2 ):

                    logger.debug("Adding 3 H to hterm_sp3 ")
                    '''
                    Choose vector cros_ik normal to plane of i,j and one nieghbor of j 
                    
                    
                    
                         cros_ik    H0
                          |        / 
                          |       /
                          j ---- i 
                        / 
                       / 
                    jk
                    
                    Scale vectore cros_ik by sin(109.5)
                    

                             H1
                            /  
                           /    
                    j----i  ----  dr_CC_s                        
                    
                    
                    
                    add to vector dr_CC between i-j scaled by cos(109.5) 
                    to get a vector hbond_0 which has an angle jiH0 of 109.5  
                    '''
                    pkey_j = Htermed.bonded_nblist.getnbs(pkey_i)[0]
                    r_j =  Htermed.positions[pkey_j]
                    for pkey_jk in Htermed.bonded_nblist.getnbs(pkey_j):
                        if( pkey_jk != pkey_i ):
                            r_jk =  Htermed.positions[pkey_jk]
                    dr_CC = r_ij_array[0]
                    dr_CC_n = dr_CC/np.linalg.norm(dr_CC)
                    dr_CC_s = dr_CC_n*tet_cos

                    dr_jk = Htermed.lat.deltasq_pos(r_j,r_jk)                    
                    cros_ik = np.cross(dr_CC,dr_jk)
                    cros_ik_n = cros_ik/np.linalg.norm(cros_ik)
                    cros_ik_s = cros_ik/np.linalg.norm(cros_ik)*tet_sin

                    hbond_0 = cros_ik_s    + dr_CC_s
                    hpos_0 = r_i + hbond_0
                    
                    r_i0 = Htermed.lat.deltasq_pos(r_i,hpos_0)
                    
                    '''
                                 H1
                    theta=109.5 /   
                               /    
                        j----i ---- H0
                               \
                                \  
                                 \
                                  H2
                                  
                    so dr_CC_s is the same as H0 

                        H0(cros_ik_n)
                        | 
                        |    theta2 = 120.0
                        |
                        i  -------cros_jk
                       /  \
                      /    \
                     /      \
                    H2       H1 
                    
                    H1 is at  2pi/3 from cros_ik_n and cros_jk
                    H2 is at -2pi/3 from cros_ik_n and cros_jk

                    and cros_ijk_n is again scaled by sin(109.5)
                    
                    '''

                    cros_jk = np.cross(dr_CC,r_i0)
                    cros_jk_n = cros_jk/np.linalg.norm(cros_jk)
                    phi = 2.0*np.pi/3.0
                    cros_ijk = cros_jk_n*np.sin(phi) + cros_ik_n*np.cos(phi)
                    cros_ijk_n = cros_ijk/np.linalg.norm(cros_ijk)
                    cros_ijk_s = cros_ijk_n*tet_sin
                    hbond_1 = cros_ijk_s + dr_CC_s

                    cros_ijk = -1.0*cros_jk_n*np.sin(phi) + cros_ik_n*np.cos(phi)
                    cros_ijk_n = cros_ijk/np.linalg.norm(cros_ijk)
                    cros_ijk_s = cros_ijk_n*tet_sin
                    hbond_2 = cros_ijk_s + dr_CC_s

                    hpos_1 = r_i + hbond_1
                    hpos_2 = r_i + hbond_2

                    pt_H.properties["fftype"] = "HC"
                    Htermed.add_partpos(pt_H,hpos_0,deepcopy = True)
                    p_h0 = Htermed.n_particles -1 
                    Bond_iH = Bond(pkey_i,p_h0)
                    Htermed.add_bond(Bond_iH)
                    #  Add (j)-(i)-H angle
                    a_i = Angle( pkey_j ,pkey_i, p_h0 )            
                    Htermed.add_angle(a_i)
                    
                    pt_H.properties["fftype"] = "HC"
                    Htermed.add_partpos(pt_H,hpos_1,deepcopy = True)
                    p_h1 = Htermed.n_particles -1 
                    Bond_iH = Bond(pkey_i,p_h1)
                    Htermed.add_bond(Bond_iH)
                    #  Add (j)-(i)-H angle
                    a_i = Angle( pkey_j ,pkey_i, p_h1 )            
                    Htermed.add_angle(a_i)

                    #  Add H0-(i)-H1 angle
                    a_i = Angle( p_h0 ,pkey_i,p_h1 )            
                    Htermed.add_angle(a_i)
                    

                    pt_H.properties["fftype"] = "HC"
                    Htermed.add_partpos(pt_H,hpos_2,deepcopy = True)
                    p_h2 = Htermed.n_particles -1 
                    Bond_iH = Bond(pkey_i,p_h2)
                    Htermed.add_bond(Bond_iH)
                    #  Add (j)-(i)-H angle
                    a_i = Angle( pkey_j ,pkey_i, p_h2 )            
                    Htermed.add_angle(a_i)
                    
                    #  Add H0-(i)-H2 angle
                    a_i = Angle( p_h0 ,pkey_i,p_h2 )            
                    Htermed.add_angle(a_i)
                    
                    #  Add H1-(i)-H2 angle
                    a_i = Angle( p_h1 ,pkey_i,p_h2 )            
                    Htermed.add_angle(a_i)
                    
                    #original_ref_mod.append(-1)
                    #pid_i_mod += 1 
                    #sub_ref_mod.append(pid_i_mod)


                                        
                else:
                    error_line =  " Nubmer of missing atoms %d has yet to be accounted for in groups.hterm \n"%(dB)
                    error_line +=  " {} -> {}".format(NNAB_o,NNAB_i)
                    Htermed.write_xyz("hterm_failed.xyz")
                    logger.warning(error_line)
                    sys.exit(error_line)
                # Redo neighbor list
                Htermed.bonded_nblist.build_nblist(Htermed.particles,Htermed.bonds )
            
        return Htermed #original_ref_mod,sub_ref_mod 


class Group(object):
    """
    Set of groups within a structureContainer
    """
    def __init__(self,tag,strucC):
        """
        Constructor
        """
        # Set pointer for easy reference
        self.strucC = strucC
        # 
        self.tag = tag 
        self.members = dict()
        self.group_nblist = NBlist()        # Creates nblist object for other groups
        self.keys = []
        self.tags = []
        self.uniqueids = dict()
        #gkey = 0
        self.cent_mass = []
        self.dl_sq = []
        self.radius = []
        self.r_gy_sq = []
        self.Q_mn = []
        self.Rgy_eignval = []
        self.A_sphere = []
        self.A_sphere_num = []
        self.A_sphere_dem = []
        # 
        self.dr_pi_pj = [] 
        
    def __del__(self):
        """
        Destructor
        """
        del self.tag 
        del self.members
        del self.group_nblist
        del self.properties
        del self.keys
        del self.tags
        del self.uniqueids
        # 
        del self.cent_mass
        del self.dl_sq
        del self.radius
        del self.r_gy_sq
        del self.Q_mn
        del self.Rgy_eignval
        del self.A_sphere       
        del self.A_sphere_num
        del self.A_sphere_dem
        del self.dr_pi_pj
        
    def group_prop(self,prop,tag,particles_select=[]):
        """
        Create groups of mols or residues

        Args:
            prop  (str) property key
            tag (str) key for Groups object in groups dict
            particles_select  (list) list of particle keys to be included in groups
                                     defaults to all particles.keys if none are specified
        Returns:
            None 
        """
        supported_group_props = ['mol','residue']
        if( prop not in supported_group_props):
            logger.warning(" Unsupported property selection for groups %s "%( prop))
            sys.exit(2)        

        if( len(particles_select) == 0 ):
            particles_select = self.strucC.particles.keys()
        # 
        self.strucC.maxtags()
        self.strucC.mol_mult()
        #
        # Group particles 
        #
        for pkey_i, particle_i  in self.strucC.particles.iteritems():
            if( pkey_i in particles_select ):
                # If in selected set of particles 
                uniqueid_i = pkey_i
                if( prop == "mol" ): 
                    uniqueid_i =  int(particle_i.mol )
                elif( prop == "residue" ): 
                    uniqueid_i =  int( particle_i.mol*self.strucC.mol_multiplier + particle_i.residue )
                    
                if( uniqueid_i not in group_uniqueid.keys() ):
                    gkey = len(self.members)
                    group_uniqueid[uniqueid_i] = gkey
                    member_i = Member(self.strucC)
                    member_i.gkey = gkey
                    member_i.tag = "%s_%s"%(tag,gkey)
                    member_i.mol  = particle_i.mol 
                    member_i.residue = particle_i.residue 
                    member_i.resname = particle_i.resname 
                    self.members[gkey] = member_i
                    # 
                    self.keys.append(member_i.gkey)
                    self.tags.append(member_i.tag)
                else:
                    gkey = group_uniqueid[uniqueid_i]
                    member_i =  self.members[gkey]
                member_i.pkeys.append(pkey_i)
                
        # Store set of groups in dict
        self.strucC.groupsets[self.tag] = self
        
        return  

        
    def calc_cent_mass(self):
        '''
        Calculate center of mass of groups and store them in list
        '''
        self.cent_mass = []
        for gkey,member_i in self.members.iteritems():
            member_i.centerofmass()
            self.cent_mass.append(member_i.cent_mass)

    def calc_dl(self):
        '''
        Calculate the maximum end to end distance of each group 
        '''
        self.dl_sq = []
        for gkey,member_i in self.members.iteritems():
            member_i.calc_dl()
            self.dl_sq.append(member_i.dl_sq)

    def calc_radius(self):
        '''
        Calculate radius of groups and store them in list
        '''
        self.radius = []
        self.r_gy_sq = []
        self.Q_mn = []
        self.Rgy_eignval = []
        self.A_sphere = []
        self.A_sphere_num = []
        self.A_sphere_dem = []
        for gkey,member_i in self.members.iteritems():
            member_i.calc_radius()
            member_i.calc_asphericity()
            self.radius.append(member_i.radius)
            self.r_gy_sq.append(member_i.r_gy_sq)
            self.Q_mn.append(member_i.Q_mn)
            self.Rgy_eignval.append(member_i.Rgy_eignval)
            self.A_sphere.append(member_i.A_sphere)
            self.A_sphere_num.append(member_i.A_sphere_num)
            self.A_sphere_dem.append(member_i.A_sphere_dem)

    def calc_dl(self):
        '''
        Calculate radius of groups and store them in list
        '''
        self.radius = []
        for gkey,member_i in self.members.iteritems():
            member_i.calc_radius()
            self.radius.append(member_i.radius)
            
    def write_cm_xyz(self,group_file=""):
        '''
        Write center of mass of each group into an xyz file
        '''
        if( len(group_file) == 0 ):
            group_file = "%s_cm.xyz"%(self.tag)
        group_out = open(group_file,"w")
        group_line = " %d \n"%(len(self.members.keys()))
        group_line += " \n"
        group_out.write(group_line)        
        for gkey,member_i in self.members.iteritems():
            cent_mass_i = member_i.cent_mass
            group_line = " Ar   {} {} {}  \n".format(cent_mass_i[0],cent_mass_i[1],cent_mass_i[2])
            group_out.write(group_line)
        group_out.close()

    def write_xyzs(self):
        '''
        Write group coordinates into an xyz file
        '''
        for gkey,member_i in self.members.iteritems():
            member_i.write_xyz()

    def group_pbcs(self):
        """
        Apply PBC's to create whole groups 

        Assumes group length is shorter than box length

        """
        for gkey,member_i in self.members.iteritems():
            # Make sure group has particles 
            if( len( member_i.pkeys ) > 0 ):
                # Get position of first particle in molecule
                pid_o  = member_i.pkeys[0]
                r_o = self.strucC.positions[pid_o]
                # 
                part_shifted = [False]*strucC.n_particles 
                # 
                r_mol_mass = np.zeros(strucC.lat.n_dim)
                shift = np.zeros(strucC.lat.n_dim)
                total_mass = 0.0 
                #
                # shift all atoms to be conected 
                #
                for pid_i in sorted(member_i.pkeys):
                    particle_i = strucC.particles[pid_i]
                    a_mass_i = particle_i.mass
                    r_i = strucC.positions[pid_i]
                    r_io = strucC.lat.deltasq_pos(r_i,r_o)
                    # sum center of mass
                    total_mass += a_mass_i
                    
                    shifted = False 
                    for dim in range(strucC.lat.n_dim):
                        shift_dim = round( r_io[dim]/  strucC.lat._matrix[dim][dim] )
                        r_i[dim] = r_i[dim]  + strucC.lat._matrix[dim][dim] * shift_dim
                        if( shift_dim != 0 ):
                            shifted = True 
                        r_mol_mass[dim] = r_mol_mass[dim]  + a_mass_i*r_i[dim] 

                    member_i.strucC.positions[pid_i] = r_i
                    r_o = r_i
                    pid_o = pid_i

                # Shift molecular center of mass into box 
                for dim in range(strucC.lat.n_dim):
                    cent_mass_i = r_mol_mass[dim] /total_mass
                    shift[dim] = strucC.lat._matrix[dim][dim] * round( cent_mass_i /  strucC.lat._matrix[dim][dim] )


                for pid_i in sorted(member_i.pkeys):
                    r_i = strucC.positions[pid_i]
                    for dim in range(strucC.lat.n_dim):
                        r_i[dim] = r_i[dim] - shift[dim] 


    def find_pairs(self,list_i,list_j,mol_inter=False,mol_intra=False):
        '''
        Find pairs based on criteria
        
        Args:
            list_i (list) list of particle index
            list_j (list) list of particle index
            mol_inter (Boolean) include inter-molecular connections
            mol_intra (Boolean) include intra-molecular connections 
        '''
        # 
        N_i = len(list_i)
        N_j = len(list_j)
        #  
        if( N_i == 0 or N_j == 0 ):
            logger.warning(" Empty list passed to structure.find_pairs ")
            return 
        # 
        # probabilityperpair = 1.0     # Probability per pair i-j 
        # 
        logger.info("Finding %d x %d  pairs  "%(N_i,N_j))
        # 
        pairvalue_ij =  np.zeros((N_i,N_j), dtype=np.float64)   # value assigned to each pair 
        #  
        for indx_i in range(N_i):
            g_i = list_i[indx_i]
            for indx_j in range(N_j):
                g_j = list_j[indx_j]
                if( g_i != g_j ):
                    pairvalue_ij[indx_i][indx_j] = 1.0
                    if( mol_inter and self.members[g_i].properties["mol"] == self.members[g_j].properties["mol"] ):
                        pairvalue_ij[indx_i][indx_j] = 0.0
                    elif( mol_intra and self.members[g_i].properties["mol"] != self.members[g_j].properties["mol"] ):
                        pairvalue_ij[indx_i][indx_j] = 0.0
                    logger.debug(" keyi %d keyj %d has probility value of %f "%(g_i,g_j,pairvalue_ij[indx_i][indx_j]))
                        
        return pairvalue_ij
        
        
    def dr_particles(self,g_i,g_j,r_cut,sub_list):
        '''
        Find a list of the distances between particles of two group members 
        '''
        
        self.dr_pi_pj = [] 
        
        member_i = self.members[g_i]
        member_j = self.members[g_j]
        #npart_pos_i = []
        for pkey_i in member_i.pkeys:
            if( pkey_i in sub_list ):
                pos_i = member_i.strucC.positions[pkey_i]
                for pkey_j in member_j.pkeys:
                    if( pkey_j in sub_list ):
                        pos_j = member_i.strucC.positions[pkey_j]
                        dr_ij,mag_dr_ij = member_i.strucC.lat.delta_pos_c(pos_i,pos_j)
                        dr_pi_pj.append(mag_dr_ij)
                        
        return mag_dr_ij
        

    def dump_json(self):
        '''
        Write group coordinates into an json file
        '''
        json_data = dict()
                
        for gkey,member_i in self.members.iteritems():
            json_data[gkey] = member_i.pkeys

        f = open("groupset_%s.json"%(self.tag), 'w')
        json.dump(json_data,f, indent=2)
        f.close()
               