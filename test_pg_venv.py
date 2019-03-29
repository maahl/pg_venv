#! /usr/bin/env python3

import os
import shutil
import unittest
from unittest.mock import patch

from actions import *
from pg_venv import *
from utils import *


TMP_DIR = os.path.abspath('.test_data')
TMP_PG_VENV = 'tmp_pg_venv'
PERSISTENT_PG_VENV = 'persistent_pg_venv'
PERSISTENT_PG_VENV_2 = 'persistent_pg_venv_2'


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


    def test_00_fetch_pg_source(self):
        return_code = fetch_pg_source(TMP_PG_VENV)

        # check that the commands were ran successfully
        self.assertTrue(return_code)

        # check that at least 1 file is actually there
        self.assertTrue(os.path.isfile(os.path.join(get_pg_src(TMP_PG_VENV), 'README')))


    def test_01_configure(self):
        return_code = configure(pg_venv=TMP_PG_VENV)

        self.assertTrue(return_code)


    def test_02_make(self):
        return_code = make(additional_args=['-j {}'.format(multiprocessing.cpu_count())], pg_venv=TMP_PG_VENV)

        self.assertTrue(return_code)

        # check that at least 1 binary was generated
        self.assertTrue(os.path.isfile(os.path.join(get_pg_src(TMP_PG_VENV), 'src', 'bin', 'pg_config', 'pg_config')))


    def test_03_make_check(self):
        return_code = make_check(TMP_PG_VENV)


    def test_04_install(self):
        return_code = install(TMP_PG_VENV)

        self.assertTrue(return_code)

        # check that at least 1 binary is available
        self.assertTrue(os.path.isfile(os.path.join(get_pg_bin(TMP_PG_VENV), 'pg_config')))


    def test_05_initdb(self):
        return_code = initdb(TMP_PG_VENV)

        self.assertTrue(return_code)

        # check that the data directory exists and contains at least 1 file
        self.assertTrue(os.path.isfile(os.path.join(get_pg_data(TMP_PG_VENV), 'postgresql.conf')))


    def test_06_start(self):
        return_code = start(TMP_PG_VENV)

        self.assertTrue(return_code)
        self.assertTrue(pg_is_running(TMP_PG_VENV))


    def test_07_stop(self):
        return_code = stop(TMP_PG_VENV)

        self.assertTrue(return_code)
        self.assertFalse(pg_is_running(TMP_PG_VENV))


    def test_08_rm_data(self):
        with patch('builtins.input', return_value=TMP_PG_VENV) as input:
            return_code = rm_data(TMP_PG_VENV)

        self.assertTrue(return_code)
        self.assertEquals(len(os.listdir(get_pg_data(TMP_PG_VENV))), 0)


    def test_09_create_virtualenv(self):
        return_code = create_virtualenv(TMP_PG_VENV)

        self.assertTrue(return_code)
        self.assertTrue(pg_is_running(TMP_PG_VENV))


    def test_10_rm_virtualenv(self):
        with patch('builtins.input', return_value=TMP_PG_VENV) as input:
            return_code = rm_virtualenv(TMP_PG_VENV)

        self.assertTrue(return_code)
        self.assertFalse(os.path.isdir(get_pg_venv_dir(TMP_PG_VENV)))


class ActionsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['PG_VIRTUALENV_HOME'] = TMP_DIR
        start(PERSISTENT_PG_VENV)
        start(PERSISTENT_PG_VENV_2)

    @classmethod
    def tearDownClass(cls):
        stop(PERSISTENT_PG_VENV)
        stop(PERSISTENT_PG_VENV_2)


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
    test_virtualenvs_are_present = os.path.isdir(get_pg_data(PERSISTENT_PG_VENV)) \
        and os.path.isdir(get_pg_data(PERSISTENT_PG_VENV_2))

    if not test_virtualenvs_are_present:
        create_virtualenv(PERSISTENT_PG_VENV)
        stop(PERSISTENT_PG_VENV)

        # copy the first one into the second one to save time
        cmd = 'cp -r {} {}'.format(get_pg_venv_dir(PERSISTENT_PG_VENV), get_pg_venv_dir(PERSISTENT_PG_VENV_2))
        execute_cmd(cmd, 'Copying virtualenv')

    actions_test_suite = unittest.TestSuite()
    actions_test_suite.addTest(unittest.makeSuite(ActionsTestCase))

    runner.run(actions_test_suite)
