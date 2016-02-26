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

    get_shell_function:
        Return the function pg() that's used as a wrapper around this script
        (necessary for the actions whose output need to be sourced, such as
        action workon). The output of this action itself is to be sourced.

        Line to put in your .bashrc:
            `source <(/absolute/path/to/pg_wrapper.py get_shell_function)`

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
        LD_LIBRARY_PATH, and display <pg_version> in the prompt (PS1). The
        output of this action is made to be sourced by bash (because it changes
        the environment). See action 'get-shell-function' to ease that.

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
        raise Exception('please set environment variable PG_DIR to point to your '
                        'postgresql source dir.')

    return pg_dir


def get_pg_install_dir():
    '''
    Get value of the environment variable PG_INSTALL_DIR, and exit if not set
    '''
    try:
        pg_install_dir = os.environ['PG_INSTALL_DIR']
    except KeyError:
        raise Exception('please set environment variable PG_INSTALL_DIR, which '
                        'should contain the directory where postgresql builds '
                        'will be installed.')

    return pg_install_dir


def get_pg_bin(pg_version):
    '''
    Return the path where a pg_version has been/will be installed
    '''
    pg_install_dir = get_pg_install_dir()
    return os.path.join(pg_install_dir, 'postgresql-{}'.format(pg_version), 'bin')


def get_pg_lib(pg_version):
    '''
    Return the path where a pg_version's libs have been/will be installed
    '''
    pg_install_dir = get_pg_install_dir()
    return os.path.join(pg_install_dir, 'postgresql-{}'.format(pg_version), 'lib')


def get_pg_version():
    '''
    Return the current PG_VERSION
    '''
    try:
        pg_version = os.environ['PG_VERSION']
    except KeyError:
        raise Exception('PG_VERSION is not set. Please run `pg workon '
                        '<pg_version>` and try again.', 'error')

    return pg_version


def get_shell_function():
    '''
    Return the text for the function pg(), used as a wrapper around this
    script.
    All the actions whose output need to be sourced should go in the if clause
    of the pg function, except this one (otherwise we would get into a
    never-ending loop).
    '''
    sourced_actions = ['w', 'workon']
    script_path = sys.argv[0] # this should be an absolute path
    output = '# Put the following line in your .bashrc, and make sure it uses an absolute path:\n'
    output += '# source <({} get_shell_function)\n'.format(script_path)

    prefix = '' # manage indentation

    output += prefix + 'function pg {\n'
    prefix += '    '

    if_clause = 'if [[ -n $1 && ('

    # first action handled separately
    if_clause += '$1 = {}'.format(sourced_actions[0])

    # other actions
    for action in sourced_actions[1:]:
        if_clause += ' || $1 = {}'.format(action)
    if_clause += ') ]]; then\n'

    output += prefix + if_clause
    prefix += '    '

    output += prefix + 'source <({} $@ || echo "echo $($_)")\n'.format(script_path)

    prefix = prefix[:-4]
    output += prefix + 'else\n'
    prefix += '    '

    output += prefix + '{} $@\n'.format(script_path)

    prefix = prefix[:-4]
    output += prefix + 'fi\n'

    prefix = prefix[:-4]
    output += '}'

    print(output)


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
    Print commands to set PG_VERSION, PATH, PGDATA, LD_LIBRARY_PATH.
    The result of this command is made to be sourced by the shell.
    Uses PG_INSTALL_DIR
    '''
    # we only expect one argument
    if len(args) > 1:
        raise TypeError
    pg_version = args[0]

    try:
        previous_pg_version  = os.environ.get('PG_VERSION', None)
        pg_install_dir = get_pg_install_dir()

        path = os.environ['PATH'].split(':')
        # remove previous version from PATH
        if previous_pg_version is not None:
            previous_pg_path = get_pg_bin(previous_pg_version)
            path = [p for p in path if p != previous_pg_path]

        # update path for current pg_version
        pg_bin_path = get_pg_bin(pg_version)
        path.insert(0, pg_bin_path)
        output = 'export PATH={}\n'.format(':'.join(path))

        ld_library_path = os.environ.get('LD_LIBRARY_PATH', '').split(':')
        # remove previous version from LD_LIBRARY_PATH
        if previous_pg_version is not None:
            previous_pg_lib_path = get_pg_lib(previous_pg_version)
            ld_library_path = [p for p in ld_library_path if p != previous_pg_lib_path]

        # update LD_LIBRARY_PATH for current pg_version
        pg_lib_path = get_pg_lib(pg_version)
        ld_library_path.insert(0, pg_lib_path)
        output += 'export LD_LIBRARY_PATH={}\n'.format(':'.join(ld_library_path))


        # update PS1 variable to display current pg_version, and remove previous
        # version
        # Can't use .format() here for some obscure reason because of that
        # characters mess
        output += r'export PS1="[pg-' + pg_version + r']${PS1#\[pg-*\]}"' + '\n'

        # set PG_VERSION variable
        output += 'export PG_VERSION={}\n'.format(pg_version)

        # set PGDATA variable
        pg_data = get_pg_data_dir(pg_version)
        output += 'export PGDATA={}\n'.format(pg_data)
    except Exception as e:
        output = 'echo -e "\033[0;31m{}\033[0;m"'.format(e)

    print(output)


ACTIONS = {
    'configure': configure,
    'get_shell_function': get_shell_function,
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
