#!/usr/bin/env python3

import os
import psutil
import subprocess
import sys


LOG_PREFIX = 'pg: '
USAGE = '''
This is a wrapper script for various PostgreSQL common actions.

Usage:
    pg create_virtualenv <pg_venv>
    pg workon <pg_venv>
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

    install, i:
        Run `make install` in postgresql source dir

        Uses environment variable PG_DIR

    log, l:
        pg log [<pg_venv>]

        <pg_venv>: for which instance to show the log

        Show the server log, using `tail -f`.

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


def check():
    '''
    Run make check in the postgresql source dir

    Uses env var PG_DIR
    '''
    pg_venv = get_env_var('PG_VENV')
    pg_src_dir = get_pg_src(pg_venv)
    cmd = 'cd {} && make -s check'.format(pg_src_dir)
    execute_cmd(cmd, 'Running make check', process_output=False)


def configure(additional_args=None, pg_venv=None, verbose=True, exit_on_fail=False):
    '''
    Run `./configure` in postgresql dir

    Uses env var PG_DIR for location of postgresql source, and
    PG_CONFIGURE_OPTIONS for options.
    additional_args parameter allows to add more options to configure
    '''
    if not pg_venv:
        pg_venv = get_env_var('PG_VENV')
    pg_src_dir = get_pg_src(pg_venv)
    pg_configure_options = os.environ.get('PG_CONFIGURE_OPTIONS', '')

    # if prefix is set in PG_CONFIGURE_OPTIONS, ignore it and display a warning
    warning_prefix_ignored = '--prefix' in pg_configure_options

    pg_configure_options += ' --prefix {}'.format(get_pg_venv_dir(pg_venv))

    if additional_args is None:
        additional_args = []
    # convert additional_args list to a string
    additional_args = ' '.join(additional_args)

    cmd = 'cd {} && ./configure --quiet {} {}'.format(pg_src_dir, pg_configure_options, additional_args)
    execute_cmd(cmd, 'Running configure script', verbose=verbose, exit_on_fail=exit_on_fail)

    # display warning if necessary
    if warning_prefix_ignored:
        log('PG_CONFIGURE_OPTIONS contained option --prefix, but this has been '
            'ignored.', 'warning')


def create_virtualenv(args=None):
    '''
    Create a new venv, by copying the source tree, configuring, compiling,
    installing, initializing the cluster, creating a db and starting the
    server.
    '''
    if args is None:
        pg_venv = get_env_var('PG_VENV')
    else:
        # only one argument is allowed
        if len(args) > 1:
            raise TypeError

        pg_venv = args[0]

    retrieve_postgres_source(pg_venv)

    configure(pg_venv=pg_venv, exit_on_fail=True)
    make(make_args=['-j {}'.format(psutil.cpu_count())], pg_venv=pg_venv, exit_on_fail=True)
    install(pg_venv=pg_venv, exit_on_fail=True)

    pg_bin = get_pg_bin(pg_venv)

    cmd = os.path.join(pg_bin, 'initdb -D {}'.format(get_pg_data(pg_venv)))
    execute_cmd(cmd, 'Initializing database', process_output=False, exit_on_fail=True)

    start([pg_venv], exit_on_fail=True)

    cmd = os.path.join(pg_bin, 'createdb -p {}'.format(get_pg_port(pg_venv)))
    execute_cmd(cmd, 'Creating a database', exit_on_fail=True)

    log('pg_virtualenv {} created. Run `pg workon {}` to use it.'.format(pg_venv, pg_venv), 'success')


def rm_virtualenv(args=None):
    '''
    Remove everything about a virtualenv
    '''
    if args is None:
        pg_venv = get_env_var('PG_VENV')
    else:
        # only one argument is allowed
        if len(args) > 1:
            raise TypeError

        pg_venv = args[0]

    if not virtualenv_exists(pg_venv):
        log('This virtualenv does not exist.', 'error')
        return

    pg_venv_dir = get_pg_venv_dir(pg_venv)

    # ask for a confirmation to remove the data
    log(
        'You are about to delete all the data for the {} pg_venv, located in {}. '
        'Please type its name to confirm:'.format(
            'specified' if args else 'current',
            pg_venv_dir
        ),
        message_type='warning'
    )
    data_delete_confirmation = input()

    if data_delete_confirmation != pg_venv:
        log("The data won't be deleted.", message_type='error')
    else:
        if pg_is_running(pg_venv):
            stop([pg_venv])
        cmd = 'rm -r {}'.format(pg_venv_dir)
        execute_cmd(cmd, 'Removing virtualenv {}'.format(pg_venv))


def virtualenv_exists(pg_venv):
    return os.path.isdir(get_pg_venv_dir(pg_venv))


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
            except TypeError as e:
                log('some arguments were not understood', 'error')
                log('error message: {}'.format(e))
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


def execute_cmd(cmd, cmd_description='', verbose=True, verbose_cmd=False, exit_on_fail=False, process_output=True):
    '''
    Execute a shell command, binding stdin and stdout to this process' stdin
    and stdout.
    The cmd_description will be displayed, along with OK or failed depending
    on the return code of the process, if verbose is True.
    The command to be executed will be printed if verbose_cmd is True.
    The process' output will be displayed if process_output is True, or if the
    process returns a non-zero code.
    '''
    if verbose_cmd:
        log('executing `{}`'.format(cmd))

    if verbose:
        log(cmd_description + '... ', end='')

    if not process_output:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        process = subprocess.Popen(cmd, shell=True)
    out, err = process.communicate()

    # display the process output if it returned non-zero, even if process output
    # is disabled.
    if process.returncode != 0 and process_output == False:
        print() # new line
        print(err.decode('utf-8'))

    if verbose:
        if process.returncode == 0:
            log('OK', 'success', prefix=False)
        else:
            log('failed', 'error')
            log('command used: {}'.format(cmd), 'error', prefix=False)

    if exit_on_fail and process.returncode != 0:
        exit(-1)

    return process.returncode


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


def get_pg_venv_dir(pg_venv):
    '''
    Return the directory containing a pg_venv
    '''
    pg_venv_home = get_env_var('PG_VIRTUALENV_HOME')
    return os.path.join(pg_venv_home, pg_venv)


def get_pg_src(pg_venv):
    '''
    Compute PGDATA for a pg_venv
    '''
    return os.path.join(get_pg_venv_dir(pg_venv), 'src')


def get_pg_data(pg_venv):
    '''
    Compute PGDATA for a pg_venv
    '''
    return os.path.join(get_pg_venv_dir(pg_venv), 'data')


def get_pg_bin(pg_venv):
    '''
    Compute the path where a pg_venv has been/will be installed
    '''
    return os.path.join(get_pg_venv_dir(pg_venv), 'bin')


def get_pg_lib(pg_venv):
    '''
    Compute the path where a pg_venv's libs have been/will be installed
    '''
    return os.path.join(get_pg_venv_dir(pg_venv), 'lib')


def get_pg_log(pg_venv):
    '''
    Compute the path where a pg_venv's logs will be stored
    '''
    return os.path.join(get_pg_venv_dir(pg_venv), '{}.log'.format(pg_venv))


def get_pg_port(pg_venv):
    '''
    Compute the port postgres will listen to, depending on its virtualenv name
    '''
    # convert the virtualenv name into an int
    pg_port = int(''.join(format(ord(l), 'b') for l in pg_venv), base=2)

    # make sure 1024 <= pg_port < 65535
    pg_port = pg_port % (65535 - 1024) + 1024

    return pg_port


def retrieve_postgres_source(pg_venv=None):
    '''
    Copy the source code of postgres (location described in an env var) into
    the src dir of the pg_venv
    '''
    if pg_venv is None:
        pg_venv = get_env_var('PG_VENV')

    pg_dir = get_env_var('PG_DIR')

    # create the necessary directories
    cmd = 'mkdir -p "{}"'.format(get_pg_src(pg_venv))
    execute_cmd(cmd, 'Creating directories', exit_on_fail=True)

    # copy the source tree
    current_commit = subprocess.check_output('cd {} && git describe --tags'.format(pg_dir), shell=True).strip().decode('utf-8')
    cmd = 'cd {} && git archive --format=tar HEAD | (cd {} && tar xf -)'.format(pg_dir, get_pg_src(pg_venv))
    execute_cmd(cmd, "Copying PostgreSQL's source tree, commit {}".format(current_commit), exit_on_fail=True)



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


def install(pg_venv=None, verbose=True, exit_on_fail=False):
    '''
    Run make install in postgresql source dir
    '''
    if not pg_venv:
        pg_venv = get_env_var('PG_VENV')
    pg_src_dir = get_pg_src(pg_venv)
    cmd = 'cd {} && make -s install && cd contrib && make -s install'.format(pg_src_dir)
    execute_cmd(cmd, 'Installing PostgreSQL', verbose, process_output=False, exit_on_fail=exit_on_fail)


def colorize(message, message_type='log'):
    '''
    Add color code to a string
    '''
    if message_type == 'log':
        # don't change color
        pass
    elif message_type == 'error':
        # red
        message = '\033[0;31m' + message + '\033[0;m'
    elif message_type == 'success':
        # green
        message = '\033[0;32m' + message + '\033[0;m'
    elif message_type == 'warning':
        # yellow
        message = '\033[0;33m' + message + '\033[0;m'

    return message


def log(message, message_type='log', end='\n', prefix=True):
    '''
    Print a message to stdout
    message_type changes the color in which the message is displayed
    Possible message_type values: log, error, success
    '''
    print((LOG_PREFIX if prefix else '') + colorize(message, message_type), end=end, flush=True)



def make(make_args=None, pg_venv=None, verbose=True, exit_on_fail=False):
    '''
    Run make in the postgresql source dir

    Uses env var PG_DIR
    <make_args> options that are passed to make
    '''
    if not pg_venv:
        pg_venv = get_env_var('PG_VENV')
    pg_src_dir = get_pg_src(pg_venv)

    if make_args is None:
        make_args = []
    # convert make_args list into a string
    make_args = ' '.join(make_args)

    cmd = 'cd {} && make -s {} && cd contrib && make -s {}'.format(pg_src_dir, make_args, make_args)
    execute_cmd(cmd, 'Compiling PostgreSQL', verbose, exit_on_fail=exit_on_fail, process_output=False)


def make_clean():
    '''
    Run make clean in the postgresql source dir

    Uses env var PG_DIR
    '''
    pg_venv = get_env_var('PG_VENV')
    pg_src_dir = get_pg_src(pg_venv)
    cmd = 'cd {} && make -s clean'.format(pg_src_dir)
    execute_cmd(cmd, 'Running make clean')


def restart():
    '''
    Runs actions stop and start
    '''
    if pg_is_running():
        stop()
    start()


def pg_is_running(pg_venv=None):
    '''
    Check if postgres is running
    '''
    if not pg_venv:
        pg_venv = get_env_var('PG_VENV')

    pg_ctl = os.path.join(get_pg_bin(pg_venv), 'pg_ctl')

    cmd = '{} status -D {}'.format(pg_ctl, get_pg_data(pg_venv))
    return_code = execute_cmd(cmd, verbose=False, process_output=False)

    return return_code == 0


def rmdata(args=None):
    '''
    Removes the data directory for the specified pg_venv.
    If a pg_venv is not provided, remove the data directory for the current one.
    '''
    if args is None:
        pg_venv = get_env_var('PG_VENV')
    else:
        # only one argument is allowed
        if len(args) > 1:
            raise TypeError

        pg_venv = args[0]

    pg_data_dir = get_pg_data(pg_venv)

    # ask for a confirmation to remove the data
    log(
        'You are about to delete all the data in your database, located in {}. '
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
        if pg_is_running(pg_venv):
            stop()
        cmd = 'rm -r {}/*'.format(pg_data_dir)
        execute_cmd(cmd, 'Removing all the data')


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
    execute_cmd(cmd, 'Displaying server log')

def start(args=None, exit_on_fail=False):
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
    cmd = '{} start -D {} -l {} --core-files --wait -o "-p {}"'.format(
        os.path.join(get_pg_bin(pg_venv), 'pg_ctl'),
        get_pg_data(pg_venv),
        get_pg_log(pg_venv),
        get_pg_port(pg_venv)
    )
    execute_cmd(cmd, 'Starting PostgreSQL', process_output=False, exit_on_fail=exit_on_fail)


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

        # if venv is given as a parameter, pass the data dir as parameter to
        # pg_ctl
        pg_data_dir = get_pg_data(pg_venv)
        cmd = '{} stop -D {}'.format(pg_ctl, pg_data_dir)

    # stop postgresql
    execute_cmd(cmd, 'Stopping PostgreSQL', process_output=False)


def usage():
    print(USAGE)


def workon(args=None):
    '''
    Print commands to set PG_VENV, PATH, PGDATA, LD_LIBRARY_PATH, PGPORT.
    The result of this command is made to be sourced by the shell.

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

        # raise an exception if the desired virtualenv does not exist
        if not virtualenv_exists(pg_venv):
            raise Exception('pg virtualenv {} does not exist. Use `pg create_virtualenv {}` to create it.'.format(pg_venv, pg_venv))

        previous_pg_venv  = os.environ.get('PG_VENV', None)

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
        pg_port = get_pg_port(pg_venv)
        output += 'export PGPORT={}\n'.format(pg_port)

        # update PS1 variable to display current pg_venv and PGPORT, and remove
        # previous version
        # Can't use .format() here for some obscure reason
        # because of that characters mess
        output += r'export PS1="[pg:' + pg_venv + ':' + str(pg_port) + r']${PS1#\[pg:*\]}"' + '\n'

        # set PG_VENV variable
        output += 'export PG_VENV={}\n'.format(pg_venv)

        # set PGDATA variable
        pg_data = get_pg_data(pg_venv)
        output += 'export PGDATA={}\n'.format(pg_data)

    except Exception as e:
        output = 'echo -e "\033[0;31m{}\033[0;m"'.format(e)

    print(output)


ACTIONS = {
    'check': check,
    'configure': configure,
    'create_virtualenv': create_virtualenv,
    'get_shell_function': get_shell_function,
    'help': usage,
    'install': install,
    'log': server_log,
    'make': make,
    'make_clean': make_clean,
    'rmdata': rmdata,
    'restart': restart,
    'rm_virtualenv': rm_virtualenv,
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
