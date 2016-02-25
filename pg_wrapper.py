#!/usr/bin/env python3

import os
import subprocess
import sys


LOG_PREFIX = 'pg_wrapper: '
USAGE = '''
Usage:
    pg_wrapper.py <action> [args]

Actions:
    configure, c:
        `pg_wrapper.py configure [<additional_args>]`

        <additional_args>: additional options passed to the configure script

        Run `.configure` in postgresql source dir.
        Uses environment variables PG_DIR and PG_CONFIGURE_OPTIONS.

    help, h:
        Display this help text

    make, m:
        `pg_wrapper.py make [<make_args>]`

        <make_args>: arguments that are passed to make (e.g. '-sj 4')

        Run `make` in postgresql source dir
        Uses environment variable PG_DIR

    make_clean, mc:
        Run `make clean` in postgresql source dir
        Uses environment variable PG_DIR

Environment variables:
    PG_CONFIGURE_OPTIONS:
        Options that are passed to the configure script

    PG_DIR:
        Contains path to the postgresql source code
'''


def configure(additional_args=None):
    '''
    Run `./configure` in postgresql dir

    Uses env var PG_DIR for location of postgresql source, and
    PG_CONFIGURE_OPTIONS for options.
    additional_args parameter allows to add more options to configure
    '''
    pg_dir = get_pg_dir()
    pg_configure_options = os.environ.get('PG_CONFIGURE_OPTIONS', '')

    if additional_args is None:
        additional_args = []
    # convert additional_args list to a string
    additional_args = ' '.join(additional_args)

    cmd = 'cd {} && ./configure {} {}'.format(pg_dir, pg_configure_options, additional_args)
    execute_cmd(cmd)


def execute_action(action, action_args):
    '''
    Execute the function corresponding to an action
    This action can also be an alias
    '''
    # if action is an existing action name, execute the corresponding function
    if action in ACTIONS.keys():
        if action_args:
            try:
                ACTIONS[action](action_args)
            except TypeError:
                log('some arguments were not understood', 'error')
                usage()
                exit(2)
        else:
            ACTIONS[action]()

    # if action is an existing alias, then execute the function corresponding to
    # the action
    elif action in ALIASES.keys():
        action = ALIASES[action]
        execute_action(action, action_args)

    # if action isn't recognized, display help and exit
    else:
        log('unrecognized action {}'.format(action), 'error')
        usage()
        exit(-1)


def execute_cmd(cmd):
    '''
    Execute a shell command, binding stdin and stdout to this process' stdin
    and stdout
    '''
    log('executing `{}`'.format(cmd))
    process = subprocess.Popen(cmd, shell=True)
    process.communicate()

    if process.returncode == 0:
        log('command succesfully executed', 'success')
    else:
        log('command failed', 'error')
        log('command used: {}'.format(cmd), 'error')


def get_pg_dir():
    '''
    Get value of the environment variable PG_DIR, and exit if not set
    '''
    try:
        pg_dir = os.environ['PG_DIR']
    except KeyError:
        log('please set environment variable PG_DIR to point to your '
            'postgresql source dir.', 'error')
        exit(1)

    return pg_dir


def log(message, message_type='log'):
    '''
    Print a message to stdout
    message_type changes the color in which the message is displayed
    Possible message_type values: log, error, success
    '''
    if message_type == 'log':
        # don't change color
        pass
    elif message_type == 'error':
        message = '\033[0;31m' + message + '\033[0;m'
    elif message_type == 'success':
        message = '\033[0;32m' + message + '\033[0;m'

    print(LOG_PREFIX + message)


def make(make_args=None):
    '''
    Run make in the postgresql source dir

    Uses env var PG_DIR
    <make_args> options that are passed to make
    '''
    pg_dir = get_pg_dir()

    if make_args is None:
        make_args = []
    # convert mae_args list into a string
    make_args = ' '.join(make_args)

    cmd = 'cd {} && make {}'.format(pg_dir, make_args)
    execute_cmd(cmd)


def make_clean():
    '''
    Run make clean in the postgresql source dir

    Uses env var PG_DIR
    '''
    pg_dir = get_pg_dir()
    cmd = 'cd {} && make clean'.format(pg_dir)
    execute_cmd(cmd)


def usage():
    print(USAGE)


ACTIONS = {
    'configure': configure,
    'help': usage,
    'make': make,
    'make_clean': make_clean,
}

ALIASES = {
    'c': 'configure',
    'h': 'help',
    'm': 'make',
    'mc': 'make_clean',
}


if __name__ == '__main__':
    args = sys.argv
    if len(args) < 2:
        usage()
        exit()

    action = args[1]
    action_args = args[2:] if len(args) > 2 else None
    execute_action(action, action_args)
