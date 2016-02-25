#!/usr/bin/env python3

import os
import subprocess
import sys


LOG_PREFIX = 'pg_wrapper: '
USAGE = '''
Usage:
    pg.py <action> [args]

Actions:
    help, h:
        Display this help text
    configure, c:
        Run `.configure` in postgresql source dir Set PG_DIR environment
        variable to the location of postgresql source
        dir.
        Set PG_CONFIGURE_OPTIONS for options to be used by the configure script.
'''


def configure(additional_args=None):
    '''
    Run `./configure` in postgresql dir

    Uses env var PG_DIR for location of postgresql source, and
    PG_CONFIGURE_OPTIONS for options.
    additional_args parameter allows to add more options to configure
    '''
    try:
        pg_dir = os.environ['PG_DIR']
    except KeyError:
        print('Please set environment variable PG_DIR to point to your '
              'postgresql source dir.')

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
            ACTIONS[action](action_args)
        else:
            ACTIONS[action]()

    # if action is an existing alias, then execute the function corresponding to
    # the action
    elif action in ALIASES.keys():
        action = ALIASES[action]
        execute_action(action, action_args)

    # if action isn't recognized, display help and exit
    else:
        print('Unrecognized action {}'.format(action))
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


def usage():
    print(USAGE)


ACTIONS = {
    'configure': configure,
    'help': usage,
}

ALIASES = {
    'c': 'configure',
    'h': 'help',
}


if __name__ == '__main__':
    args = sys.argv
    if len(args) < 2:
        usage()
        exit()

    action = args[1]
    action_args = args[2:] if len(args) > 2 else None
    execute_action(action, action_args)
