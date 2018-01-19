#!/usr/bin/env python3

import os
import subprocess
import sys


LOG_PREFIX = 'pg: '
USAGE = '''
This is a wrapper script for various PostgreSQL common actions.

Usage:
    pg <action> [args]

Actions:
    check, ck:
        Run `make check` in postgresql source dir.
        Uses environment variable PG_DIR

    configure, c:
        pg configure [<additional_args>]

        <additional_args>: additional options passed to the configure script

        Run `./configure` in postgresql source dir.
        Postgresql's install path will be set to
        "$PG_INSTALL_DIR/postgresql-$PG_VENV". If you want to store a specific
        pg_venv at another place, you can symlink this location to the new one.

        Uses environment variables PG_DIR, PG_CONFIGURE_OPTIONS, PG_INSTALL_DIR
        and PG_VENV.

    get_shell_function:
        Return the function pg() that's used as a wrapper around this script
        (necessary for the actions whose output need to be sourced, such as
        action workon). The output of this action itself is to be sourced.

        Line to put in your .bashrc:
            `source <(/absolute/path/to/pg_wrapper.py get_shell_function)`

    help, h:
        Display this help text

    install, i:
        Run `make install` in postgresql source dir

        Uses environment variable PG_DIR

    log, l:
        pg log [<pg_venv>]

        <pg_venv>: for which instance to show the log

        Show the server log, using `tail -f`.

        Uses environment variable PG_DATA_DIR

    make, m:
        pg make [<make_args>]

        <make_args>: arguments that are passed to make (e.g. '-sj 4')

        Run `make` in postgresql source dir
        Uses environment variable PG_DIR

    make_clean, mc:
        Run `make clean` in postgresql source dir
        Uses environment variable PG_DIR

    restart:
        Similar to running `pg stop && pg start`

    rmdata:
        Removes the data directory for the current pg
        Uses environment variable PG_DATA_DIR

    start:
        pg start [<pg_venv>]

        <pg_venv>: which instance to start

        Start a postgresql instance from pg_venv. If <pg_venv> is not specified,
        start the current one (defined by PG_VENV).
        Uses environment variables PG_VENV and PG_INSTALL_DIR

    stop:
        pg stop [<pg_venv>]

        <pg_venv>: which instance to stop

        stop a postgresql instance. If <pg_venv> is not specified, stop the
        current one (defined by PG_VENV)
        Uses environment variables PG_VENV and PG_INSTALL_DIR

    workon, w:
        pg workon <pg_venv>

        <pg_venv>: a string to identify the current postgresql build

        Set PATH to use PG_INSTALL_DIR/bin, set PG_VENV, PGPORT, PGDATA,
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

    PG_DATA_DIR:
        Postgresql instances data will be stored in this directory.
        Each instance will have its data in $PG_DATA_DIR/postgresql-<pg_venv>

    PG_INSTALL_DIR:
        Postgresql builds will be installed in this directory.
        Each build will be installed in $PG_INSTALL_DIR/postgresql-$PG_VENV.
        Needs to be an absolute path.

    PG_VENV:
        Version of postgresql we are currently working on.
        Do not change this manually, use the 'workon' action.
        Changes the install path (option '--prefix' in `configure`), the
        search path for executables (PATH) and the data path (PGDATA)
'''


def check():
    '''
    Run make check in the postgresql source dir

    Uses env var PG_DIR
    '''
    pg_dir = get_env_var('PG_DIR')
    cmd = 'cd {} && make check'.format(pg_dir)
    execute_cmd(cmd)


def check_configure_venv():
    '''
    Check that the paths that were given to the configure action correspond to
    the current pg_venv

    This is useful for preventing a "make install" that would override files
    that belong to other pg_venv.
    Returns True if the configure options correspond to the current pg_venv,
    false otherwise.
    '''
    pg_dir = get_env_var('PG_DIR')
    pg_bin = get_pg_bin(get_env_var('PG_VENV'))

    # check what the configuration is in the postgresql source dir
    try:
        with open(os.path.join(pg_dir, 'src', 'port', 'pg_config_paths.h'), 'r') as f:
            if pg_bin not in f.readline():
                log('Postgresql is configured for another pg_venv. You need to re-run configure first.', 'error')
                exit(-1)
    except FileNotFoundError:
        pass


def configure(additional_args=None):
    '''
    Run `./configure` in postgresql dir

    Uses env var PG_DIR for location of postgresql source, and
    PG_CONFIGURE_OPTIONS for options.
    additional_args parameter allows to add more options to configure
    '''
    pg_dir = get_env_var('PG_DIR')
    pg_configure_options = os.environ.get('PG_CONFIGURE_OPTIONS', '')

    # if prefix is set in PG_CONFIGURE_OPTIONS, ignore it and display a warning
    warning_prefix_ignored = '--prefix' in pg_configure_options

    pg_venv = get_env_var('PG_VENV')
    pg_install_dir = get_env_var('PG_INSTALL_DIR')
    pg_configure_options += ' --prefix {}'.format(os.path.join(pg_install_dir, 'postgresql-' + pg_venv))

    if additional_args is None:
        additional_args = []
    # convert additional_args list to a string
    additional_args = ' '.join(additional_args)

    cmd = 'cd {} && ./configure {} {}'.format(pg_dir, pg_configure_options, additional_args)
    execute_cmd(cmd)

    # display warning if necessary
    if warning_prefix_ignored:
        log('PG_CONFIGURE_OPTIONS contained option --prefix, but this has been '
            'ignored.', 'warning')


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
        log('command successfully executed', 'success')
    else:
        log('command failed', 'error')
        log('command used: {}'.format(cmd), 'error')


def get_env_var(env_var):
    '''
    Return the value of an environment variable
    '''
    try:
        return os.environ[env_var]
    except KeyError:
        # handle PG_VENV differently, as it mustn't be set by the user directly
        if env_var == 'PG_VENV':
            log('PG_VENV not set. Please run `pg workon <pg_venv>` first', 'error')

        else:
            log('Please set environment variable {}. See help for '
                'detail (pg help).'.format(env_var), 'error')

        exit(-1)


def get_pg_data_dir(pg_venv):
    '''
    Compute PGDATA for a pg_venv
    '''
    pg_data_dir = get_env_var('PG_DATA_DIR')
    return os.path.join(pg_data_dir, 'postgresql-{}'.format(pg_venv))


def get_pg_bin(pg_venv):
    '''
    Compute the path where a pg_venv has been/will be installed
    '''
    pg_install_dir = get_env_var('PG_INSTALL_DIR')
    return os.path.join(pg_install_dir, 'postgresql-{}'.format(pg_venv), 'bin')


def get_pg_lib(pg_venv):
    '''
    Compute the path where a pg_venv's libs have been/will be installed
    '''
    pg_install_dir = get_env_var('PG_INSTALL_DIR')
    return os.path.join(pg_install_dir, 'postgresql-{}'.format(pg_venv), 'lib')


def get_pg_log(pg_venv):
    '''
    Compute the path where a pg_venv's logs will be stored
    '''
    pg_data_dir = get_env_var('PG_DATA_DIR')
    return os.path.join(pg_data_dir, 'postgresql-{}'.format(pg_venv) + '.log')


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
    pg_dir = get_env_var('PG_DIR')
    check_configure_venv()
    cmd = 'cd {} && make install && cd contrib && make install'.format(pg_dir)
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
    elif message_type == 'warning':
        message = '\033[0;33m' + message + '\033[0;m'

    print(LOG_PREFIX + message)


def make(make_args=None):
    '''
    Run make in the postgresql source dir

    Uses env var PG_DIR
    <make_args> options that are passed to make
    '''
    pg_dir = get_env_var('PG_DIR')
    check_configure_venv()

    if make_args is None:
        make_args = []
    # convert make_args list into a string
    make_args = ' '.join(make_args)

    cmd = 'cd {} && make -s {} && cd contrib && make -s {}'.format(pg_dir, make_args, make_args)
    execute_cmd(cmd)


def make_clean():
    '''
    Run make clean in the postgresql source dir

    Uses env var PG_DIR
    '''
    pg_dir = get_env_var('PG_DIR')
    cmd = 'cd {} && make clean'.format(pg_dir)
    execute_cmd(cmd)


def restart():
    '''
    Runs actions stop and start
    '''
    stop()
    start()


def rmdata(args=None):
    '''
    Removes the data directory for the specified pg_venv.
    If a pg_venv is not provided, remove the data directory for the current one.

    Uses env var PG_DATA_DIR
    '''
    if args is None:
        pg_venv = get_env_var('PG_VENV')
    else:
        # only one argument is allowed
        if len(args) > 1:
            raise TypeError

        pg_venv = args[0]

    pg_data_dir = get_pg_data_dir(pg_venv)

    # ask for a confirmation to remove the data
    log(
        'You are about to delete all the data for the {} pg_venv, located in {}. '
        'Please type its name to confirm:'.format(
            'specified' if args else 'current',
            pg_data_dir
        ),
        message_type='warning'
    )
    data_delete_confirmation = input()

    if data_delete_confirmation != pg_venv:
        log("The data won't be deleted.", message_type='error')
    else:
        cmd = 'rm -r {}/*'.format(pg_data_dir)
        execute_cmd(cmd)


def server_log(args=None):
    '''
    Display the server log
    If a pg_venv name is not provided, show the log for the current one.
    '''
    if args is None:
        pg_venv = get_env_var('PG_VENV')
    else:
        # only one argument is allowed
        if len(args) > 1:
            raise TypeError

        pg_venv = args[0]

    # show the log
    cmd = 'tail -f {}'.format(get_pg_log(pg_venv))
    execute_cmd(cmd)

def start(args=None):
    '''
    Start a postgresql instance
    If a pg_venv name is not provided, start the current one.
    '''
    if args is None:
        pg_venv = get_env_var('PG_VENV')
    else:
        # only one argument is allowed
        if len(args) > 1:
            raise TypeError

        pg_venv = args[0]

    # start postgresql
    cmd = '{} start -D {} -l {}'.format(
        os.path.join(get_pg_bin(pg_venv), 'pg_ctl'),
        get_pg_data_dir(pg_venv),
        get_pg_log(pg_venv)
    )
    execute_cmd(cmd)


def stop(args=None):
    '''
    Stop a postgresql instance
    If a pg_venv name is not provided, stop the current one.
    '''
    if args is None:
        pg_venv = get_env_var('PG_VENV')
        pg_ctl = os.path.join(get_pg_bin(pg_venv), 'pg_ctl')
        cmd = '{} stop'.format(pg_ctl)
    else:
        # only one argument is allowed
        if len(args) > 1:
            raise TypeError

        pg_venv = args[0]
        pg_ctl = os.path.join(get_pg_bin(pg_venv), 'pg_ctl')

        # if version is given as a parameter, pass the data dir as parameter to
        # pg_ctl
        pg_data_dir = get_pg_data_dir(pg_venv)
        cmd = '{} stop -D {}'.format(pg_ctl, pg_data_dir)

    # stop postgresql
    execute_cmd(cmd)


def usage():
    print(USAGE)


def workon(args=None):
    '''
    Print commands to set PG_VENV, PATH, PGDATA, LD_LIBRARY_PATH, PGPORT.
    The result of this command is made to be sourced by the shell.
    Uses PG_INSTALL_DIR

    There is a default value for args even though the parameter is mandatory,
    because we want to exit gracefully (since the output of this function is
    sourced).
    '''
    try:
        # we only expect one argument
        if args is None:
            raise TypeError("Missing argument pg_venv. See 'pg help' for details")
        if len(args) > 1:
            raise TypeError("Too many arguments. See 'pg help' for details")
        pg_venv = args[0]

        previous_pg_venv  = os.environ.get('PG_VENV', None)
        pg_install_dir = get_env_var('PG_INSTALL_DIR')

        path = os.environ['PATH'].split(':')
        # remove previous version from PATH
        if previous_pg_venv is not None:
            previous_pg_path = get_pg_bin(previous_pg_venv)
            path = [p for p in path if p != previous_pg_path]

        # update path for current pg_venv
        pg_bin_path = get_pg_bin(pg_venv)
        path.insert(0, pg_bin_path)
        output = 'export PATH={}\n'.format(':'.join(path))

        ld_library_path = os.environ.get('LD_LIBRARY_PATH', '').split(':')
        # remove previous version from LD_LIBRARY_PATH
        if previous_pg_venv is not None:
            previous_pg_lib_path = get_pg_lib(previous_pg_venv)
            ld_library_path = [p for p in ld_library_path if p != previous_pg_lib_path]

        # update LD_LIBRARY_PATH for current pg_venv
        pg_lib_path = get_pg_lib(pg_venv)
        ld_library_path.insert(0, pg_lib_path)
        output += 'export LD_LIBRARY_PATH={}\n'.format(':'.join(ld_library_path))

        # set PGPORT variable
        # port is determined from the venv name, 1024 <= port <= 65535
        # collisions are possible and not handled
        pg_port = int(''.join(format(ord(l), 'b') for l in pg_venv), base=2) % (65535 - 1024) + 1024
        output += 'export PGPORT={}\n'.format(pg_port)

        # update PS1 variable to display current pg_venv and PGPORT, and remove
        # previous version
        # Can't use .format() here for some obscure reason
        # because of that characters mess
        output += r'export PS1="[pg:' + pg_venv + ':' + str(pg_port) + r']${PS1#\[pg:*\]}"' + '\n'

        # set PG_VENV variable
        output += 'export PG_VENV={}\n'.format(pg_venv)

        # set PGDATA variable
        pg_data = get_pg_data_dir(pg_venv)
        output += 'export PGDATA={}\n'.format(pg_data)

    except Exception as e:
        output = 'echo -e "\033[0;31m{}\033[0;m"'.format(e)

    print(output)


ACTIONS = {
    'check': check,
    'configure': configure,
    'get_shell_function': get_shell_function,
    'help': usage,
    'install': install,
    'log': server_log,
    'make': make,
    'make_clean': make_clean,
    'rmdata': rmdata,
    'restart': restart,
    'start': start,
    'stop': stop,
    'workon': workon,
}

ALIASES = {
    'c': 'configure',
    'ck': 'check',
    'h': 'help',
    'i': 'install',
    'l': 'log',
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
