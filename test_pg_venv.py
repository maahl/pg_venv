#! /usr/bin/env python3

import multiprocessing
import os
import shutil
import sys
import unittest
from unittest.mock import patch

from actions import configure, create_virtualenv, get_shell_function, install, list_pg_venv, make, make_check, make_clean, restart, rm_data, rm_virtualenv, server_log, start, stop, workon
from utils import pg_is_running, get_env_var, get_pg_src, get_pg_bin, initdb, get_pg_data, get_pg_venv_dir, execute_cmd


TMP_DIR = os.path.abspath('.test_data')
TMP_PG_VENV = 'tmp_pg_venv'
PERSISTENT_PG_VENV = 'persistent_pg_venv'


class CreateVirtualenvTestCase(unittest.TestCase):
    '''
    Test all the actions required to create a postgres virtualenv

    Note that the tests must be run in order, as they depend on each other.
    '''
    @classmethod
    def setUpClass(cls):
        '''
        Set environment vars necessary for running the tests, and create the
        directory that will contain the test data.
        '''
        if os.path.isdir(TMP_DIR):
            shutil.rmtree(TMP_DIR)
        os.makedirs(TMP_DIR)
        os.environ['PG_VIRTUALENV_HOME'] = TMP_DIR


    @classmethod
    def tearDownClass(cls):
        '''
        Remove test data
        '''
        if pg_is_running(TMP_PG_VENV):
            stop(TMP_PG_VENV)
        shutil.rmtree(TMP_DIR)
        pg_dir = get_env_var('PG_DIR')
        execute_cmd('cd {} && git branch -d {}'.format(pg_dir, TMP_PG_VENV), 'removing temporary branch')

    
    def test_00_create_virtualenv(self):
        return_code = create_virtualenv(pg_venv=TMP_PG_VENV)
        print('create_virtualenv return code: ', return_code)
        self.assertTrue(return_code == 0)


    def test_01_configure(self):
        return_code = configure(pg_venv=PERSISTENT_PG_VENV)

        self.assertTrue(return_code == 0)


    def test_02_rm_data(self):
        with patch('builtins.input', return_value=TMP_PG_VENV) as input: #pylint: disable=unused-variable
            return_code = rm_data(TMP_PG_VENV)

        self.assertTrue(return_code == 0)
        self.assertEquals(len(os.listdir(get_pg_data(TMP_PG_VENV))), 0)


    def test_03_initdb(self):
        return_code = initdb(TMP_PG_VENV)

        self.assertTrue(return_code == 0)

        # check that the data directory exists and contains at least 1 file
        self.assertTrue(os.path.isfile(os.path.join(get_pg_data(TMP_PG_VENV), 'postgresql.conf')))


    def test_04_rm_virtualenv(self):
        # pylint: disable=C0321
        with patch('builtins.input', return_value=TMP_PG_VENV) as input: #pylint: disable=unused-variable
            return_ok = rm_virtualenv(TMP_PG_VENV)

        self.assertTrue(return_ok == 0)
        self.assertFalse(os.path.isdir(get_pg_venv_dir(TMP_PG_VENV)))


class ActionsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['PG_VIRTUALENV_HOME'] = TMP_DIR
        start(PERSISTENT_PG_VENV)

    @classmethod
    def tearDownClass(cls):
        stop(PERSISTENT_PG_VENV)

    def test_01_stop(self):
        return_code = stop(PERSISTENT_PG_VENV)

        self.assertTrue(return_code == 0)
        self.assertFalse(pg_is_running(PERSISTENT_PG_VENV))


    def test_02_start(self):
        return_code = start(PERSISTENT_PG_VENV)

        self.assertTrue(return_code == 0)
        self.assertTrue(pg_is_running(PERSISTENT_PG_VENV))


    def test_03_restart(self):
        return_code = restart(PERSISTENT_PG_VENV)

        self.assertTrue(return_code == 0)
        self.assertTrue(pg_is_running(PERSISTENT_PG_VENV))


if __name__ == '__main__':
    # use -v or --verbose flag to get tested functions' output
    verbose = '--verbose' in sys.argv or '-v' in sys.argv

    runner = unittest.TextTestRunner(buffer=not verbose)

    # run expensive tests only if --all is in the arguments
    if '--all' in sys.argv:
        create_virtualenv_test_suite = unittest.TestSuite()
        create_virtualenv_test_suite.addTest(unittest.makeSuite(CreateVirtualenvTestCase))

        runner.run(create_virtualenv_test_suite)

    # setup necessary env var
    os.environ['PG_VIRTUALENV_HOME'] = TMP_DIR

    # create two identical virtualenvs, in case they don't exist yet
    test_virtualenv_is_present = os.path.isdir(get_pg_data(PERSISTENT_PG_VENV))

    if not test_virtualenv_is_present:
        create_virtualenv(PERSISTENT_PG_VENV)
        stop(PERSISTENT_PG_VENV)

    actions_test_suite = unittest.TestSuite()
    actions_test_suite.addTest(unittest.makeSuite(ActionsTestCase))

    runner.run(actions_test_suite)
