#!/usr/bin/env python3

import os
import subprocess
import sys


LOG_PREFIX = 'pg: '
USAGE = '''
Usage:
    pg <action> [args]

Actions:
    configure, c:
        pg configure [<additional_args>]

        <additional_args>: additional options passed to the configure script

        Run `./configure` in postgresql source dir.
        If PG_CONFIGURE_OPTIONS doesn't contain '--prefix' option, postgresql
        install path will be set to "$PG_INSTALL_DIR/postgresql-$PG_VERSION".

        Uses environment variables PG_DIR, PG_CONFIGURE_OPTIONS, PG_INSTALL_DIR
        and PG_VERSION.

    help, h:
        Display this help text

    make, m:
        pg make [<make_args>]

        <make_args>: arguments that are passed to make (e.g. '-sj 4')

        Run `make` in postgresql source dir
        Uses environment variable PG_DIR

    make_clean, mc:
        Run `make clean` in postgresql source dir
        Uses environment variable PG_DIR

    workon, w:
        pg workon <pg_version>

        <pg_version>: a string to identify the current postgresql build

        Set PATH to use PG_INSTALL_DIR/bin, set PG_VERSION, PGPORT, PGDATA,
        and display <pg_version> in the prompt (PS1). The output of this
        action is made to be sourced by bash (because it changes the
        environment). See action 'get-shell-function' to ease that.

Environment variables:
    PG_CONFIGURE_OPTIONS:
        Options that are passed to the configure script
        If it contains '--prefix', PG_VERSION will have no effect during action
        'configure'

    PG_DIR:
        Contains path to the postgresql source code

    PG_INSTALL_DIR:
        Postgresql builds will be installed in this directory.
        Each build will be installed in $PG_INSTALL_DIR/postgresql-$PG_VERSION.
        Needs to be an absolute path.
        Not used if option '--prefix' is passed to 'configure' action.

    PG_VERSION:
        Version of postgresql we are currently working on.
        Do not change this manually, use the 'workon' action.
        Changes the install path (option '--prefix' in `configure`), the
        search path for executables (PATH) and the data path (PGDATA)
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

    # if prefix is not set yet, set it to go in PG_INSTALL_DIR
    if '--prefix' not in pg_configure_options:
        pg_version = get_pg_version()
        pg_install_dir = get_pg_install_dir()
        print(pg_version)
        print(pg_install_dir)
        pg_configure_options += ' --prefix {}'.format(os.path.join(pg_install_dir, 'postgresql-' + pg_version))

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


def get_pg_install_dir():
    '''
    Get value of the environment variable PG_INSTALL_DIR, and exit if not set
    '''
    try:
        pg_install_dir = os.environ['PG_INSTALL_DIR']
    except KeyError:
        log('please set environment variable PG_INSTALL_DIR, which should '
            'contain the directory where postgresql builds will be installed.', 'error')
        exit(1)

    return pg_install_dir


def get_pg_path(pg_version):
    '''
    Return the path where a pg_version has been/will be installed
    '''
    pg_install_dir = get_pg_install_dir()
    return os.path.join(pg_install_dir, 'postgresql-{}'.format(pg_version), 'bin')


def get_pg_version():
    '''
    Return the current PG_VERSION
    '''
    try:
        pg_version = os.environ['PG_VERSION']
    except KeyError:
        log('PG_VERSION is not set. Please run `pg workon <pg_version>` and try again.', 'error')
        exit(1)

    return pg_version


def install():
    '''
    Run make install in postgresql source dir
    '''
    pg_dir = get_pg_dir()
    cmd = 'cd {} && make install'.format(pg_dir)
    execute_cmd(cmd)


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
    # convert make_args list into a string
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


def workon(args):
    '''
    Print commands to set PG_VERSION, PATH.
    The result of this command is made to be sourced by the shell.
    Uses PG_INSTALL_DIR
    '''
    # we only expect one argument
    if len(args) > 1:
        raise TypeError
    pg_version = args[0]

    previous_pg_version  = os.environ.get('PG_VERSION', None)
    pg_install_dir = get_pg_install_dir()

    path = os.environ['PATH'].split(':')
    # remove previous version from PATH
    if previous_pg_version is not None:
        previous_pg_path = get_pg_path(previous_pg_version)
        path = [p for p in path if p != previous_pg_path]

    # update path for current pg_version
    pg_path = get_pg_path(pg_version)
    path.insert(0, pg_path)
    cmd = 'export PATH={}'.format(':'.join(path))
    print(cmd)

    # update PS1 variable to display current pg_version, and remove previous
    # version
    # can't use .format() here for some obscure reason because of that
    # characters mess
    cmd = r'export PS1="[pg-' + pg_version + r']${PS1#\[pg-*\]}"'
    print(cmd)

    # set PG_VERSION variable
    cmd = 'export PG_VERSION={}'.format(pg_version)
    print(cmd)


ACTIONS = {
    'configure': configure,
    'help': usage,
    'install': install,
    'make': make,
    'make_clean': make_clean,
    'workon': workon,
}

ALIASES = {
    'c': 'configure',
    'h': 'help',
    'i': 'install',
    'm': 'make',
    'mc': 'make_clean',
    'w': 'workon',
}


if __name__ == '__main__':
    args = sys.argv
    if len(args) < 2:
        usage()
        exit()

    action = args[1]
    action_args = args[2:] if len(args) > 2 else None
    execute_action(action, action_args)
