# coding: utf-8
# Copyright (c) Alliance for Sustainable Energy, LLC
# Distributed under the terms of the Apache License, Version 2.0

from __future__ import division, unicode_literals

__author__ = "Travis W. Kemper, Scott Sides"
__copyright__ = "Copyright 2015, Alliance for Sustainable Energy, LLC"
__version__ = "0.3"
__email__ = "streamm@nrel.gov"
__status__ = "Beta"

"""
Wrapper classes for MPI python using the Peregrine module enviroment

The derived classes implement the interface defined in the base class
'ParallelMsgr'. These derived classes currently implement communication using:
boost.mpi, mpi4py and serial

NOTE: continue to end of this documentation to see short tutorial methods on use
"""

import os, sys, math, random, time


class ParallelMsgr(object):
    """
    Base class defining the interface to parallel communication methods
    """

    def __init__(self, rk, sz, verbose=False):
        """
        Constructor

        Args:
            rk: rank of processor
            sz: size of communicator
            verbose: flag for printing output info
        """

        # Flag for debug printing
        self.verbose = verbose
        # Basic comm variables
        self.rank     = rk
        self.commSize = sz

        if (self.verbose and self.rank == 0):
            print " "
            print "Base class ParallelMsgr constructor called"


    def __del__(self):
        """
        Destructor
        """
        if (self.verbose and self.rank == 0):
            print "ParallelMsgr destructor called"
            print " "


    def getRank(self):
        """
        ID of current processor

        Returns:
            integerr rank of current processor
        """

        return self.rank


    def getCommSize(self):
        """
        Number of processors in world communicator
        """

        return self.commSize


    def barrier(self):
        """
        Must be implemented in derived 
        """

        print "Not implemented in base class"
        sys.exit(3)

    def gatherList(self, data, root=0):
        """
        Must be implemented in derived
        """

        print "gatherList not implemented in base class"
        sys.exit(3)


    def reduceSum(self, data, root=0):
        """
        Must be implemented in derived
        """

        print "reduceSum not implemented in base class"
        sys.exit(3)


    def allReduceSum(self, data):
        """
        Must be implemented in derived
        """

        print "allReduceSum not implemented in base class"
        sys.exit(3)


    def tupleOfLists2List(self, tup):
        """
        Take a tuple of lists and convert to single list
        eg ([a,b],[c,d],[e,f],...) -->  [a,b,c,d,e,f]
        """

        bigList = []
        try:
            for i in tup:
                bigList = bigList + i
        except:
            pass

        return bigList


    def splitListOnProcs(self, data):
        """
        Split up global input list equally (as possible) and return the
        'chunk' of list belonging to each processor. Note, no communication
        is performed, input data is known globally.

        Split algorithm will guarantee returning a list that has 'rank'
        number of elements. Not all local lists will in general be the same length.

        NOTE: If len(data) > rank some of the elements of the split list will be of
        zero length, so the local list on some processors can be empty. Calling program
        should account for this.

        Args:
            data: list of data [..]
        Returns:
            list of data for this local processor
        """

        parts = self.commSize             # Number of procesors
        newseq = []                       # New partitioned list

        n = len(data) / parts   # min items per subsequence
        r = len(data) % parts   # remaindered items
        b,e = 0, n + min(1, r) # first split
        for i in range(parts):
            newseq.append(data[b:e])
            r = max(0, r-1)             # use up remainders
            b,e = e, e + n + min(1, r)  # min(1,r) is always 0 or 1
        plist = newseq                  # Make 'parts' number of chunks

        # Error check or return results
        if len(plist) != parts:
            print " " 
            print "Partitioning failed, check data length and #-procs"
            print "   len(plist) = ", len(plist), " on proc ", self.rank
            print "        parts = ", parts, " on proc ", self.rank
            sys.exit(0)
        else:
            return plist[self.rank]


class MsgrBoost(ParallelMsgr):
    """
    Derived class implementing interface in the base class using
    Boost MPI libraries
    """

    def __init__(self, commObj, verbose=False):
        """
        Constructor
        """

        # Use comm object to initialize
        self.commObj = commObj
        self.rank = commObj.rank
        self.size = commObj.size
        self.world = commObj.world

        # Ensuring base class called
        ParallelMsgr.__init__(self, self.rank, self.size, verbose)

        # Flag for debug printing
        self.verbose = verbose
        if (self.verbose and self.rank == 0):
            print "Derived class MsgrBoost constructor called"

        if (self.verbose):
            for proc in range(self.size):
                if proc == self.rank:
                    print "I am process %d of %d." % (self.rank, self.size)
                self.barrier()
            self.barrier()


    def bcast(self, data, root=0):
        """
        Broadcast from root proc to world comm
        """

        gdata = self.commObj.broadcast(self.world, data, root)
        self.barrier()
        return gdata


    def barrier(self):
        """
        Barrier for world comm
        """
        self.world.barrier()


    def gatherList(self, data, root=0):
        """
        Gather data in list from world comm on root proc
        and return as a continuous list
        """

        tupOfLists = self.commObj.gather(self.world, data, root)
        oneList= ParallelMsgr.tupleOfLists2List(self, tupOfLists)
        self.barrier()
        return oneList


    def reduceSum(self, data, root=0):
        """
        Add data elements in localData across processors and put
        result on root proc
        """

        gdata = self.commObj.all_reduce(self.world, data, lambda a,b: a+b, root)
        self.barrier()
        return gdata


    def allReduceSum(self, data):
        """
        Add data elements in localData across processors and put on
        all world procs
        """
        gdata = self.commObj.all_reduce(self.world, data, lambda a,b: a+b)
        self.barrier()
        return gdata



class MsgrMpi4py(ParallelMsgr):
    """
    Derived class implementing interface in the base class using
    Mpi4py libraries
    """

    def __init__(self, commObj, verbose=False):
        """
        Constructor
        """

        # Use comm object to initialize
        self.commObj = commObj
        self.comm = commObj.COMM_WORLD
        self.rank = self.comm.Get_rank()
        self.size = self.comm.Get_size()

        # Ensuring base class called
        ParallelMsgr.__init__(self, self.rank, self.size, verbose)

        # Flag for debug printing
        self.verbose = verbose
        if (self.verbose and self.rank == 0):
            print "Derived class MsgrMPI4PY constructor called"
            
        if (self.verbose):
            for proc in range(self.size):
                if proc == self.rank:
                    print "I am process %d of %d." % (self.rank, self.size)
                self.barrier()
            self.barrier()


    def bcast(self, localData, root=0):
        """
        Broadcast to world communicator
        """

        gdata = self.comm.bcast(localData,root)
        return gdata


    def barrier(self):
        """
        Barrier to world comm
        """
        self.comm.barrier()


    def gatherList(self, localData, root=0):
        """
        Gather data in list from world comm on root proc
        and return as a continuous list
        """
        listOfLists = self.comm.gather(localData, root)
        oneList = ParallelMsgr.tupleOfLists2List(self, listOfLists)
        self.barrier()
        return oneList

    def reduceSum(self, localData, root=0):
        """
        Add data elements in localData across processors and put
        result on root proc
        """
        gdata = self.comm.reduce(localData, self.commObj.SUM, root)
        self.barrier()
        return gdata


    def allReduceSum(self, localData):
        """
        Add data elements in localData across processors and put on
        all world procs
        """
        MPI = self.commObj
        gdata = self.comm.allreduce(localData, MPI.SUM)
        self.barrier()
        return gdata



class MsgrSerial(ParallelMsgr):
    """
    Derived class implementing interface in the base class using
    no MPI (serial) libraries
    """

    def __init__(self, verbose=False):
        """
        Constructor
        """
        self.rank = 0
        self.size = 1

        # Ensuring base class called
        ParallelMsgr.__init__(self, self.rank, self.size, verbose)

        # Flag for debug printing
        self.verbose = verbose
        if (self.verbose and self.rank == 0):
            print "Derived class MsgrSerial constructor called"


    def bcast(self, data, root=0):
        """
        Broadcast from root proc to world comm
        """
        return data


    def barrier(self):
        """
        Barrier for world comm
        """
        return


    def gatherList(self, data, root=0):
        """
        Gather data in list from world comm on root proc
        and return as a continuous list
        """
        return data


    def reduceSum(self, data, root=0):
        """
        Add data elements in localData across processors and put
        result on root proc
        """
        return data


    def allReduceSum(self, data):
        """
        Add data elements in localData across processors and put on
        all world procs
        """
        return data





def getMPIObject(verbose=False, localVerbose=False):
    """
    Driver for comm classes.
    Selects MPI-comm module if found and builds appropriate derived class

    Returns: an mpi object of the appropriate derived class
    """

    mpiObj=None
    try:
        from mpi4py import MPI as mpi
        mpiObj = MsgrMpi4py(mpi, verbose)
        if (mpiObj.getRank()==0 and localVerbose):
            print "Found mpi4py module \n"
        mpiObj.barrier()
    except:
        pass

    if (mpiObj == None):
        try:
            import boost.mpi as mpi
            mpiObj = MsgrBoost(mpi, verbose)
            if (mpiObj.getRank()==0 and localVerbose):
                print "Found boost.mpi module \n"
            mpiObj.barrier()
        except:
            pass

    if ( mpiObj == None):
        mpiObj = MsgrSerial(verbose)
        if( verbose ):
            print "No mpi module found, will use serial. \n"

    return mpiObj


def getMPISerialObject(verbose=True):
    """
    Driver for comm classes.
    Forces serial MPI-comm module

    Returns: an mpi serial object
    """
    mpiObj = MsgrSerial(verbose)
    return mpiObj

