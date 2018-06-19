#!/usr/bin/env python3

import argparse
import os
import sys

from actions import ACTIONS
from utils import get_env_var


USAGE = '''
This is a wrapper script for various PostgreSQL common actions.

Usage:
    pg create_virtualenv <pg_venv>
    pg workon <pg_venv>
    pg <action> [args]

Actions:
    configure:
        pg configure [<additional_args>]

        <additional_args>: additional options passed to the configure script

        Run `./configure` in postgresql source dir.
        Postgresql's install path will be set to
        "$PG_DIR/$PG_VENV". If you want to store a specific
        pg_venv at another place, you can symlink this location to the new one.

        Uses environment variables PG_DIR, PG_CONFIGURE_OPTIONS, and PG_VENV.

    create_virtualenv:
        Create a new pg_venv, by copying the postgres' source tree, compiling
        it, installing it, running initdb, starting the server and creating a
        db using createdb.

    get_shell_function:
        Return the function pg() that's used as a wrapper around this script
        (necessary for the actions whose output need to be sourced, such as
        action workon). The output of this action itself is to be sourced.

        Line to put in your .bashrc:
            `source <(/absolute/path/to/pg_wrapper.py get_shell_function)`

    help, h:
        Display this help text

    install:
        Run `make install` in postgresql source dir

        Uses environment variable PG_DIR

    log, l:
        pg log [<pg_venv>]

        <pg_venv>: for which instance to show the log

        Show the server log, using `tail -f`.

    make:
        pg make [<make_args>]

        <make_args>: arguments that are passed to make (e.g. '-sj 4')

        Run `make` in postgresql source dir
        Uses environment variable PG_DIR

    make_check:
        Run `make check` in postgresql source dir.
        Uses environment variable PG_DIR

    make_clean:
        Run `make clean` in postgresql source dir
        Uses environment variable PG_DIR

    restart:
        Similar to running `pg stop && pg start`

    rm_data:
        Removes the data directory for the current pg

    start:
        pg start [<pg_venv>]

        <pg_venv>: which instance to start

        Start a postgresql instance from pg_venv. If <pg_venv> is not specified,
        start the current one (defined by PG_VENV).
        Uses environment variables PG_VENV

    stop:
        pg stop [<pg_venv>]

        <pg_venv>: which instance to stop

        stop a postgresql instance. If <pg_venv> is not specified, stop the
        current one (defined by PG_VENV)
        Uses environment variables PG_VENV

    workon, w:
        pg workon <pg_venv>

        <pg_venv>: a string to identify the current postgresql build

        Set PATH to use PG_DIR/bin, set PG_VENV, PGPORT, PGDATA,
        LD_LIBRARY_PATH, and display <pg_venv> in the prompt (PS1). The
        output of this action is made to be sourced by bash (because it changes
        the environment). See action 'get-shell-function' to ease that.

Environment variables:
    PG_CONFIGURE_OPTIONS:
        Options that are passed to the configure script
        If it contains '--prefix', PG_VENV will have no effect during action
        'configure'

    PG_DIR:
        Contains path to the postgresql source code

    PG_VIRTUALENV_HOME:
        Contains the data for a pg_venv, including a copy of the source code
        that was used to generate the binaries, the binaries themselves, and
        the data dir.

    PG_VENV:
        Version of postgresql we are currently working on.
        Do not change this manually, use the 'workon' action.
        Changes the install path (option '--prefix' in `configure`), the
        search path for executables (PATH) and the data path (PGDATA)
'''


def execute_action(action, action_args):
    '''
    Execute the function corresponding to an action
    This action can also be an alias
    '''
    try:
        ACTIONS[action].execute(action_args)
    except TypeError as e:
        log('some arguments were not understood', 'error')
        log('error message: {}'.format(e))
        exit(2)


def available_pg_venvs():
    return os.listdir(get_env_var('PG_VIRTUALENV_HOME'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action', metavar='<action>')
    subparsers.required = True

    # create a subparser for each action
    action_parsers = {}
    for _, action in ACTIONS.items():
        action_parsers[action.name] = subparsers.add_parser(
            action.name,
            help=action.short_desc,
            aliases = [action.alias] if action.alias else [],
        )
        action_parsers[action.name].set_defaults(func=getattr(action, 'execute'))

    # define mandatory pg_venv argument for workon action
    action_parsers['workon'].add_argument(
        'pg_venv',
        choices=available_pg_venvs(),
        help='Existing pg_venv',
        metavar='<pg_venv>'
    )

    #define mandatory pg_venv argument for create_virtualenv action
    action_parsers['create_virtualenv'].add_argument(
        'pg_venv',
        help='New pg_venv',
        metavar='<pg_venv>'
    )

    # define optional pg_venv argument for actions that need it
    for action in ['log', 'restart', 'rm_data', 'rm_virtualenv', 'start', 'stop']:
        action_parsers[action].add_argument(
            'pg_venv',
            nargs='?',
            choices=available_pg_venvs(),
            const=get_env_var('PG_VENV', error_on_fail=False),
            help='Existing pg_venv',
            metavar='<pg_venv>',
        )

    # define additional_options argument for actions that need it
    for action in ['configure', 'make']:
        action_parsers[action].add_argument(
            'additional_args',
            nargs='*',
            help='Additional options to pass to the underlying command',
            metavar='<additional_args>',
        )

    args = parser.parse_args()
    action = args.func
    action_args = vars(args)

    # remove arguments that are not used by the action functions
    del action_args['func']
    del action_args['action']

    action(action_args)
