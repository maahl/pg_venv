#! /usr/bin/env python3

import os
import shutil
import unittest
from unittest.mock import patch
from pg_wrapper import *


TMP_DIR = os.path.abspath('test_data')
PG_VENV = 'test_pg_venv'


def setUpModule():
    '''
    Set environment vars necessary for running the tests, and create the
    directory that will contain the test data.
    '''
    os.makedirs(TMP_DIR)
    os.environ['PG_VIRTUALENV_HOME'] = TMP_DIR


def tearDownModule():
    '''
    Remove test data
    '''
    stop([PG_VENV])
    shutil.rmtree(TMP_DIR)


class CreateVirtualenvTestCase(unittest.TestCase):
    '''
    Test all the actions required to create a postgres virtualenv

    Note that the tests must be run in order, as they depend on each other.
    '''
    def test_00_retrieve_postgres_source(self):
        return_code = retrieve_postgres_source(PG_VENV)

        # check that the commands were ran successfully
        self.assertTrue(return_code)

        # check that at least 1 file is actually there
        self.assertTrue(os.path.isfile(os.path.join(get_pg_src(PG_VENV), 'README')))


    def test_01_configure(self):
        return_code = configure(pg_venv=PG_VENV)

        self.assertTrue(return_code)


    def test_02_make(self):
        return_code = make(make_args=['-j {}'.format(psutil.cpu_count())], pg_venv=PG_VENV)

        self.assertTrue(return_code)

        # check that at least 1 binary was generated
        self.assertTrue(os.path.isfile(os.path.join(get_pg_src(PG_VENV), 'src', 'bin', 'pg_config', 'pg_config')))


    def test_03_make_check(self):
        return_code = make_check(PG_VENV)


    def test_04_install(self):
        return_code = install(PG_VENV)

        self.assertTrue(return_code)

        # check that at least 1 binary is available
        self.assertTrue(os.path.isfile(os.path.join(get_pg_bin(PG_VENV), 'pg_config')))


    def test_05_initdb(self):
        return_code = initdb(PG_VENV)

        self.assertTrue(return_code)

        # check that the data directory exists and contains at least 1 file
        self.assertTrue(os.path.isfile(os.path.join(get_pg_data(PG_VENV), 'postgresql.conf')))


    def test_06_start(self):
        return_code = start([PG_VENV])

        self.assertTrue(return_code)
        self.assertTrue(pg_is_running(PG_VENV))


    def test_07_stop(self):
        return_code = stop([PG_VENV])

        self.assertTrue(return_code)
        self.assertFalse(pg_is_running(PG_VENV))


    def test_08_rm_data(self):
        with patch('builtins.input', return_value=PG_VENV) as input:
            return_code = rm_data([PG_VENV])

        self.assertTrue(return_code)
        self.assertEquals(len(os.listdir(get_pg_data(PG_VENV))), 0)


    def test_09_create_virtualenv(self):
        return_code = create_virtualenv([PG_VENV])

        self.assertTrue(return_code)
        self.assertTrue(pg_is_running(PG_VENV))


    def test_10_rm_virtualenv(self):
        with patch('builtins.input', return_value=PG_VENV) as input:
            return_code = rm_virtualenv([PG_VENV])

        self.assertTrue(return_code)
        self.assertFalse(os.path.isdir(get_pg_venv_dir(PG_VENV)))


if __name__ == '__main__':
    # use -v or --verbose flag to get tested functions' output
    verbose = '--verbose' in sys.argv or '-v' in sys.argv

    runner = unittest.TextTestRunner(buffer=not verbose)
    # run expensive tests only if --all is in the arguments
    if '--all' in sys.argv:
        create_virtualenv_test_suite = unittest.TestSuite()
        create_virtualenv_test_suite.addTest(unittest.makeSuite(CreateVirtualenvTestCase))

        runner.run(create_virtualenv_test_suite)
