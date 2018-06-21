import multiprocessing
import sys

from utils import *


class Action():
    def __init__(self, name, function, short_desc, desc='', args={}, alias=None):
        # name of the action, used in the CLI to invoke it
        self.name = name

        # function that will be called when this action is invoked
        self.function = function

        self.short_desc = short_desc
        self.desc = desc

        # list of arguments expected by the action
        self.args = args

        # alias that can also be used in the CLI to invoke the action
        self.alias = alias


    def execute(self, kwargs):
        self.function(**kwargs)


def configure(additional_args=None, pg_venv=None, verbose=True, exit_on_fail=False):
    '''
    Run `./configure` in pg_venv's copy of postgresql's source

    additional_args parameter allows to add more options to configure

    Returns true if all commands run returned 0, false otherwise.
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
    configure_return_code = execute_cmd(cmd, 'Running configure script', verbose=verbose, exit_on_fail=exit_on_fail)

    # display warning if necessary
    if warning_prefix_ignored:
        log('PG_CONFIGURE_OPTIONS contained option --prefix, but this has been '
            'ignored.', 'warning')

    return configure_return_code == 0


def create_virtualenv(pg_venv):
    '''
    Create a new venv, by copying the source tree, configuring, compiling,
    installing, initializing the cluster, creating a db and starting the
    server.
    '''
    if pg_venv is None:
        pg_venv = get_env_var('PG_VENV')

    copy_return_code = fetch_pg_source(pg_venv)

    configure_return_code = configure(pg_venv=pg_venv, exit_on_fail=True)
    make_return_code = make(additional_args=['-j {}'.format(multiprocessing.cpu_count())], pg_venv=pg_venv, exit_on_fail=True)
    install_return_code = install(pg_venv=pg_venv, exit_on_fail=True)

    initdb_return_code = initdb(pg_venv, exit_on_fail=True)

    start_return_code = start(pg_venv, exit_on_fail=True)

    cmd = os.path.join(get_pg_bin(pg_venv), 'createdb -p {}'.format(get_pg_port(pg_venv)))
    createdb_return_code = execute_cmd(cmd, 'Creating a database', exit_on_fail=True)

    log('pg_virtualenv {} created. Run `pg workon {}` to use it.'.format(pg_venv, pg_venv), 'success')

    return copy_return_code \
        and make_return_code \
        and install_return_code \
        and initdb_return_code \
        and start_return_code \
        and createdb_return_code == 0


def fetch_pg_source(pg_venv=None):
    '''
    Get a new copy of postgresql's source code and copy it in the pg_venv
    '''
    if pg_venv is None:
        pg_venv = get_env_var('PG_VENV')

    pg_dir = get_env_var('PG_DIR')
    pg_src = get_pg_src(pg_venv)

    # remove the previous source tree if needed
    if os.path.isdir(pg_src):
        cmd = 'rm -r {}'.format(pg_src)
        rm_return_code = execute_cmd(cmd, 'Removing previous source tree', exit_on_fail=True)
    else:
        rm_return_code = 0

    # create the necessary directories
    cmd = 'mkdir -p "{}"'.format(pg_src)
    execute_cmd(cmd, 'Creating directories', exit_on_fail=True)

    # copy the source tree
    current_commit = subprocess.check_output('cd {} && git describe --tags'.format(pg_dir), shell=True).strip().decode('utf-8')
    cmd = 'cd {} && git archive --format=tar HEAD | (cd {} && tar xf -)'.format(pg_dir, pg_src)
    copy_return_code = execute_cmd(cmd, "Copying PostgreSQL's source tree, commit {}".format(current_commit), exit_on_fail=True)

    return rm_return_code == 0 and  copy_return_code == 0



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

    output += prefix + 'cmd_output=$({} $@ 2>&1)\n'.format(script_path)
    output += prefix + 'if [ $? -eq 0 ]; then\n'
    prefix += '    '
    output += prefix + 'source <(echo $cmd_output)\n'
    prefix = prefix[:-4]
    output += prefix + 'else\n'
    prefix += '    '
    output += prefix + 'echo $cmd_output\n'
    prefix = prefix[:-4]
    output += prefix + 'fi\n'

    prefix = prefix[:-4]
    output += prefix + 'else\n'
    prefix += '    '

    output += prefix + '{} $@\n'.format(script_path)

    prefix = prefix[:-4]
    output += prefix + 'fi\n'

    prefix = prefix[:-4]
    output += '}'

    print(output)


def install(pg_venv, verbose=True, exit_on_fail=False):
    '''
    Run make install in postgresql source dir

    Returns true if all commands run returned 0, false otherwise.
    '''
    if not pg_venv:
        pg_venv = get_env_var('PG_VENV')
    pg_src_dir = get_pg_src(pg_venv)
    cmd = 'cd {} && make -s install && cd contrib && make -s install'.format(pg_src_dir)
    install_return_code = execute_cmd(cmd, 'Installing PostgreSQL', verbose, process_output=False, exit_on_fail=exit_on_fail)

    return install_return_code == 0


def list_pg_venv():
    '''
    List active and inactive pg_venv
    '''
    pg_venvs = available_pg_venvs()
    current_pg_venv = get_env_var('PG_VENV', error_on_fail=False)

    current_str = ' [current]'
    sep_size = 4
    pg_venv_column_size = max(max(map(len, pg_venvs)), len(current_pg_venv) + len(current_str)) + sep_size
    port_column_size = 5 + sep_size
    version_column_size = 7 + sep_size
    format_str = '{:<' + str(pg_venv_column_size) + '}{:<' + str(port_column_size) + '}{:<' + str(version_column_size) + '}{}'

    print(format_str.format('PG_VENV', 'PORT', 'VERSION', 'RUNNING'))
    for pg_venv in pg_venvs:
        pg_venv_str = pg_venv + current_str if pg_venv == current_pg_venv else pg_venv
        running_str = colorize('Yes', 'success') if pg_is_running(pg_venv) else 'No'
        print(format_str.format(pg_venv_str, get_pg_port(pg_venv), get_pg_version(pg_venv), running_str))


def make(additional_args=[], pg_venv=None, verbose=True, exit_on_fail=False):
    '''
    Run make in the postgresql source dir

    Uses env var PG_DIR
    <make_args> options that are passed to make

    Returns true if all commands run returned 0, false otherwise.
    '''
    if not pg_venv:
        pg_venv = get_env_var('PG_VENV')

    pg_src_dir = get_pg_src(pg_venv)

    # convert make_args list into a string
    additional_args = ' '.join(additional_args)

    cmd = 'cd {} && make -s {} && cd contrib && make -s {}'.format(pg_src_dir, additional_args, additional_args)
    make_return_code = execute_cmd(cmd, 'Compiling PostgreSQL', verbose, exit_on_fail=exit_on_fail, process_output=False)

    return make_return_code == 0


def make_check(pg_venv=None):
    '''
    Run make check in postgresql's source

    Returns true if all commands run returned 0, false otherwise.
    '''
    if pg_venv is None:
        pg_venv = get_env_var('PG_VENV')

    pg_src_dir = get_pg_src(pg_venv)
    cmd = 'cd {} && make -s check'.format(pg_src_dir)
    make_check_return_code = execute_cmd(cmd, 'Running make check', process_output=False)

    return make_check_return_code == 0


def make_clean(pg_venv=None):
    '''
    Run make clean in the postgresql source dir

    Uses env var PG_DIR
    '''
    if pg_venv is None:
        pg_venv = get_env_var('PG_VENV')

    pg_src_dir = get_pg_src(pg_venv)
    cmd = 'cd {} && make -s clean'.format(pg_src_dir)
    execute_cmd(cmd, 'Running make clean')


def restart(pg_venv):
    '''
    Runs actions stop and start
    '''
    if pg_is_running(pg_venv):
        stop(pg_venv)
    start(pg_venv)


def rm_data(pg_venv):
    '''
    Removes the data directory for the specified pg_venv.
    If a pg_venv is not provided, remove the data directory for the current one.
    '''
    if pg_venv is None:
        pg_venv = get_env_var('PG_VENV')

    pg_data_dir = get_pg_data(pg_venv)

    # ask for a confirmation to remove the data
    log(
        'You are about to delete all the data in your database, located in {}. '
        'Please type its name to confirm:'.format(pg_data_dir),
        message_type='warning'
    )
    data_delete_confirmation = input()

    if data_delete_confirmation != pg_venv:
        log("The data won't be deleted.", message_type='error')
        return False
    else:
        if pg_is_running(pg_venv):
            stop(pg_venv)
        cmd = 'rm -r {}/*'.format(pg_data_dir)
        rm_return_code = execute_cmd(cmd, 'Removing all the data')

        return rm_return_code == 0


def rm_virtualenv(pg_venv):
    '''
    Remove everything about a virtualenv
    '''
    pg_venv_specified = pg_venv is not None
    if not pg_venv_specified:
        pg_venv = get_env_var('PG_VENV')

    if not pg_virtualenv_exists(pg_venv):
        log('This virtualenv does not exist.', 'error')
        return

    pg_venv_dir = get_pg_venv_dir(pg_venv)

    # ask for a confirmation to remove the data
    log(
        'You are about to delete all the data for the {} pg_venv, located in {}. '
        'Please type its name to confirm:'.format(
            'specified' if pg_venv_specified else 'current',
            pg_venv_dir
        ),
        message_type='warning'
    )
    data_delete_confirmation = input()

    if data_delete_confirmation != pg_venv:
        log("The data won't be deleted.", message_type='error')
        return False
    else:
        if pg_is_running(pg_venv):
            stop_return_code = stop(pg_venv)
        else:
            stop_return_code = True

        cmd = 'rm -r {}'.format(pg_venv_dir)
        rm_return_code = execute_cmd(cmd, 'Removing virtualenv {}'.format(pg_venv))
        return stop_return_code and rm_return_code == 0


def server_log(pg_venv):
    '''
    Display the server log
    If a pg_venv name is not provided, show the log for the current one.
    '''
    if pg_venv is None:
        pg_venv = get_env_var('PG_VENV')

    # show the log
    cmd = 'tail -f {}'.format(get_pg_log(pg_venv))
    execute_cmd(cmd, 'Displaying server log')


def start(pg_venv, exit_on_fail=False):
    '''
    Start a postgresql instance
    If a pg_venv name is not provided, start the current one.
    '''
    if pg_venv is None:
        pg_venv = get_env_var('PG_VENV')

    # start postgresql
    cmd = '{} start -D {} -l {} --core-files --wait -o "-p {}"'.format(
        os.path.join(get_pg_bin(pg_venv), 'pg_ctl'),
        get_pg_data(pg_venv),
        get_pg_log(pg_venv),
        get_pg_port(pg_venv)
    )
    start_return_code = execute_cmd(cmd, 'Starting PostgreSQL', process_output=False, exit_on_fail=exit_on_fail)

    return start_return_code == 0


def stop(pg_venv):
    '''
    Stop a postgresql instance
    If a pg_venv name is not provided, stop the current one.
    '''
    if pg_venv is None:
        pg_venv = get_env_var('PG_VENV')

    pg_ctl = os.path.join(get_pg_bin(pg_venv), 'pg_ctl')
    pg_data_dir = get_pg_data(pg_venv)
    cmd = '{} stop -D {}'.format(pg_ctl, pg_data_dir)

    # stop postgresql
    stop_return_code = execute_cmd(cmd, 'Stopping PostgreSQL', process_output=False)

    return stop_return_code == 0


def workon(pg_venv):
    '''
    Print commands to set PG_VENV, PATH, PGDATA, LD_LIBRARY_PATH, PGPORT.
    The result of this command is made to be sourced by the shell.

    There is a default value for args even though the parameter is mandatory,
    because we want to exit gracefully (since the output of this function is
    sourced).
    '''
    try:
        # raise an exception if the desired virtualenv does not exist
        if not pg_virtualenv_exists(pg_venv):
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
    'configure': Action('configure', configure, "Run configure on postgresql's source"),
    'create_virtualenv': Action('create_virtualenv', create_virtualenv, 'Create a new pg_venv'),
    'fetch_pg_source': Action('fetch_pg_source', fetch_pg_source, "Fetch a new copy of postgresql's source code"),
    'get_shell_function': Action('get_shell_function', get_shell_function, 'Get the shell function to source'),
    'install': Action('install', install, "Install posgresql's binaries"),
    'list': Action('list', list_pg_venv, 'List active and inactive pg_venv'),
    'log': Action('log', server_log, 'Display the server log', alias='l'),
    'make': Action('make', make, 'Compile postgresql'),
    'make_check': Action('make_check', make_check, "Run make check on postgres' source"),
    'make_clean': Action('make_clean', make_clean, "Run make clean on postgresql's source"),
    'restart': Action('restart', restart, 'Restart postgresql'),
    'rm_data': Action('rm_data', rm_data, "Remove postgresql's data directory"),
    'rm_virtualenv': Action('rm_virtualenv', rm_virtualenv, 'Remove a pg_venv'),
    'start': Action('start', start, 'Start postgresql'),
    'stop': Action('stop', stop, 'Stop postgresql'),
    'workon': Action('workon', workon, 'Activate a pg_venv', alias='w'),
}
