import os
import glob
import shutil
import pandas as pd
import importlib
import logging
import subprocess
import drep.argumentParser
import drep.d_cluster

import pytest

import tests.test_utils as test_utils

@pytest.fixture()
def self():
    self = test_utils.load_common_self()
    yield self
    self.teardown()

def test_multiround_primary_clustering_1(self):
    test_dir = self.test_dir

    # Run it under normal conditions
    args = drep.argumentParser.parse_args(['compare', self.wd_loc, '--primary_chunksize', '3', '--multiround_primary_clustering', '-pa', '0.95', '-d', '-g'] + self.genomes)
    kwargs = vars(args)
    drep.d_cluster.controller.d_cluster_wrapper(self.wd_loc, **kwargs)

    # Load test results
    wd = drep.WorkDirectory.WorkDirectory(self.wd_loc)

    # Load solutions
    wdS = drep.WorkDirectory.WorkDirectory(self.s_wd_loc)
    CdbS = wdS.get_db('Cdb').sort_values('genome').reset_index(drop=True)

    # Make sure you didn't pairwise
    Mdb = wd.get_db('Mdb')
    assert len(Mdb) != 25
    assert 'genome_chunk' in list(Mdb.columns)
    assert len(Mdb['genome_chunk'].unique()) == 3

    # Make sure you still got the correct clustering
    Cdb = wd.get_db('Cdb').sort_values('genome').reset_index(drop=True)
    assert test_utils.compare_dfs2(CdbS, Cdb, verbose=True)

    # Make sure it handles plotting gracefully
    drep.d_analyze.mash_dendrogram_from_wd(wd, plot_dir=test_dir)

def test_greedy_secondary_clustering_1(self):
    test_dir = self.test_dir

    # Crash gracefully if the algorithm isn't right
    args = drep.argumentParser.parse_args(
        ['compare', self.wd_loc, '--greedy_secondary_clustering', '-sa', '0.99', '-d', '-g'] + self.genomes)
    kwargs = vars(args)
    try:
        drep.d_cluster.controller.d_cluster_wrapper(self.wd_loc, **kwargs)
        assert False
    except NameError:
        pass

    # Run it under normal conditions
    args = drep.argumentParser.parse_args(['compare', self.wd_loc, '--greedy_secondary_clustering', '--S_algorithm', 'fastANI', '-sa', '0.99', '-d', '-g'] + self.genomes)
    kwargs = vars(args)
    drep.d_cluster.controller.d_cluster_wrapper(self.wd_loc, **kwargs)

    # Load test results
    wd = drep.WorkDirectory.WorkDirectory(self.wd_loc)

    # Load solutions
    wdS = drep.WorkDirectory.WorkDirectory(self.s_wd_loc)
    CdbS = wdS.get_db('Cdb').sort_values('genome').reset_index(drop=True)
    NdbS = wdS.get_db('Ndb')

    # Make sure you didn't pairwise
    Ndb = wd.get_db('Ndb')
    assert len(Ndb) != len(NdbS)

    # Make sure you still got the correct clustering
    Cdb = wd.get_db('Cdb').sort_values('genome').reset_index(drop=True)
    assert 'greedy_representative' in Cdb.columns
    del Cdb['greedy_representative']

    for t in ['cluster_method', 'comparison_algorithm']:
        del Cdb[t]
        del CdbS[t]

    CdbS['secondary_cluster'] = [x.replace('_0', '_1') for x in CdbS['secondary_cluster']]

    assert test_utils.compare_dfs2(CdbS, Cdb, verbose=True)

    # Make sure it handles plotting gracefully
    drep.d_analyze.plot_secondary_dendrograms_from_wd(wd, plot_dir=test_dir)

def test_multiround_primary_clustering_2(self):
    """
    Make sure this works with dereplicate --ignoreGenomeQuality
    """
    test_dir = self.test_dir

    # Run it under normal conditions
    args = drep.argumentParser.parse_args(['dereplicate', self.wd_loc, '--primary_chunksize', '3', '--multiround_primary_clustering', '--ignoreGenomeQuality', '-pa', '0.95', '-d', '-g'] + self.genomes)
    drep.controller.Controller().parseArguments(args)

    # Load test results
    wd = drep.WorkDirectory.WorkDirectory(self.wd_loc)

    # Load solutions
    wdS = drep.WorkDirectory.WorkDirectory(self.s_wd_loc)
    CdbS = wdS.get_db('Cdb').sort_values('genome').reset_index(drop=True)

    # Make sure you didn't pairwise
    Mdb = wd.get_db('Mdb')
    assert len(Mdb) != 25
    assert 'genome_chunk' in list(Mdb.columns)
    assert len(Mdb['genome_chunk'].unique()) == 3

    # Make sure you still got the correct clustering
    Cdb = wd.get_db('Cdb').sort_values('genome').reset_index(drop=True)
    assert test_utils.compare_dfs2(CdbS, Cdb, verbose=True)

    # Make sure it handles plotting gracefully
    drep.d_analyze.mash_dendrogram_from_wd(wd, plot_dir=test_dir)

@pytest.mark.skip(reason="This test doesn't work; you don't know how to have clusterAlg impact the resulting Mdb")
def test_multiround_primary_clustering_3(self):
    """
    Make sure multiround_primary_clustering respects "clusterAlg"
    """
    test_dir = self.test_dir

    # Run it under normal conditions
    args = drep.argumentParser.parse_args(['dereplicate', self.wd_loc, '--clusterAlg', 'single', '--primary_chunksize', '3', '--multiround_primary_clustering', '--ignoreGenomeQuality', '-pa', '0.75', '-d', '-g'] + self.genomes)
    drep.controller.Controller().parseArguments(args)

    # Load test results
    wd = drep.WorkDirectory.WorkDirectory(self.wd_loc)
    Mdb = wd.get_db('Mdb')
    Cdb = wd.get_db('Cdb').sort_values('genome').reset_index(drop=True)
    del Cdb['cluster_method']

    # Run it with a different clusterAlg
    shutil.rmtree(self.working_wd_loc)
    args = drep.argumentParser.parse_args(['dereplicate', self.working_wd_loc, '--clusterAlg', 'complete', '--primary_chunksize', '3', '--multiround_primary_clustering', '--ignoreGenomeQuality', '-pa', '0.75', '-d', '-g'] + self.genomes)
    drep.controller.Controller().parseArguments(args)

    # Load test results
    wd = drep.WorkDirectory.WorkDirectory(self.working_wd_loc)
    Mdb2 = wd.get_db('Mdb')
    Cdb2 = wd.get_db('Cdb').sort_values('genome').reset_index(drop=True)
    del Cdb2['cluster_method']

    # Make sure you get different clustering
    assert not test_utils.compare_dfs2(Cdb, Cdb2, verbose=True)

def test_multiround_primary_clustering_4(self):
    """
    Make sure this works with dereplicate without --ignoreGenomeQuality and with --SkipSecondary
    """
    test_dir = self.test_dir

    # Run it under normal conditions
    args = drep.argumentParser.parse_args(['dereplicate', self.wd_loc, '--primary_chunksize', '3', '--multiround_primary_clustering', '--ignoreGenomeQuality', '--SkipSecondary', '-d', '-g'] + self.genomes)
    drep.controller.Controller().parseArguments(args)

    # Load test results
    wd = drep.WorkDirectory.WorkDirectory(self.wd_loc)

    # Load solutions
    wdS = drep.WorkDirectory.WorkDirectory(self.s_wd_loc)
    CdbS = wdS.get_db('Cdb').sort_values('genome').reset_index(drop=True)

    # Make sure you didn't pairwise
    Mdb = wd.get_db('Mdb')
    assert len(Mdb) != 25
    assert 'genome_chunk' in list(Mdb.columns)
    assert len(Mdb['genome_chunk'].unique()) == 3

    # Make sure you still got the correct clustering
    Cdb = wd.get_db('Cdb').sort_values('genome').reset_index(drop=True)

    # Keep only the relevant columns
    del CdbS['secondary_cluster']
    del CdbS['comparison_algorithm']
    del CdbS['threshold']
    Cdb = Cdb[list(CdbS.columns)]
    #print(CdbS.columns)

    assert test_utils.compare_dfs2(CdbS, Cdb, verbose=True)

    # Make sure it handles plotting gracefully
    drep.d_analyze.mash_dendrogram_from_wd(wd, plot_dir=test_dir)

def test_greedy_secondary_clustering_2(self):
    """
    Make sure this works with dereplicate
    """
    test_dir = self.test_dir

    # Crash gracefully if the algorithm isn't right
    args = drep.argumentParser.parse_args(
        ['dereplicate', self.wd_loc, '--greedy_secondary_clustering', '-sa', '0.99', '--ignoreGenomeQuality', '-d', '-g'] + self.genomes)
    try:
        drep.controller.Controller().parseArguments(args)
        assert False
    except NameError:
        pass

    # Run it under normal conditions
    args = drep.argumentParser.parse_args(['dereplicate', self.wd_loc, '--greedy_secondary_clustering', '--S_algorithm', 'fastANI', '--ignoreGenomeQuality', '-sa', '0.99', '-d'])
    drep.controller.Controller().parseArguments(args)

    # Load test results
    wd = drep.WorkDirectory.WorkDirectory(self.wd_loc)

    # Load solutions
    wdS = drep.WorkDirectory.WorkDirectory(self.s_wd_loc)
    CdbS = wdS.get_db('Cdb').sort_values('genome').reset_index(drop=True)
    NdbS = wdS.get_db('Ndb')
    SdbS = wdS.get_db('Sdb')

    # Make sure you didn't pairwise
    Ndb = wd.get_db('Ndb')
    assert len(Ndb) != len(NdbS)

    # Make sure you incorporated centrality
    Sdb = wd.get_db('Sdb')
    assert not test_utils.compare_dfs2(Sdb, SdbS, verbose=True)

    # Make sure you still got the correct clustering
    Cdb = wd.get_db('Cdb').sort_values('genome').reset_index(drop=True)
    assert 'greedy_representative' in Cdb.columns
    del Cdb['greedy_representative']

    for t in ['cluster_method', 'comparison_algorithm']:
        del Cdb[t]
        del CdbS[t]

    CdbS['secondary_cluster'] = [x.replace('_0', '_1') for x in CdbS['secondary_cluster']]

    assert test_utils.compare_dfs2(CdbS, Cdb, verbose=True)



    # Make sure it handles plotting gracefully
    drep.d_analyze.plot_secondary_dendrograms_from_wd(wd, plot_dir=test_dir)