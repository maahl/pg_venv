import os
import subprocess


LOG_PREFIX = 'pg: '


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


def execute_cmd(cmd, cmd_description='', verbose=True, verbose_cmd=False, exit_on_fail=False, process_output=True, error_output=True):
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
    if process.returncode != 0 and not process_output and error_output:
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


def get_env_var(env_var, error_on_fail=True):
    '''
    Return the value of an environment variable
    '''
    try:
        return os.environ[env_var]
    except KeyError:
        if error_on_fail:
            # handle PG_VENV differently, as it mustn't be set by the user directly
            if env_var == 'PG_VENV':
                log('PG_VENV not set. Please run `pg workon <pg_venv>` first', 'error')

            else:
                log('Please set environment variable {}. See help for '
                    'detail (pg help).'.format(env_var), 'error')

            exit(-1)
        else:
            return None


def get_disk_usage(pg_venv):
    '''
    Compute the disk space used by a pg_venv
    '''
    cmd = 'du -hd 0 {} | cut -f 1'.format(get_pg_venv_dir(pg_venv))
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    out = out.decode('utf-8').strip()

    return out


def get_pg_bin(pg_venv):
    '''
    Compute the path where a pg_venv has been/will be installed
    '''
    return os.path.join(get_pg_venv_dir(pg_venv), 'bin')


def get_pg_data(pg_venv):
    '''
    Compute PGDATA for a pg_venv
    '''
    return os.path.join(get_pg_venv_dir(pg_venv), 'data')


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


def get_pg_src(pg_venv):
    '''
    Compute PGDATA for a pg_venv
    '''
    return os.path.join(get_pg_venv_dir(pg_venv), 'src')


def get_pg_venv_dir(pg_venv):
    '''
    Return the directory containing a pg_venv
    '''
    pg_venv_home = get_env_var('PG_VIRTUALENV_HOME')
    return os.path.join(pg_venv_home, pg_venv)


def get_pg_version(pg_venv):
    '''
    Return the version of postgresql in a pg_venv
    '''
    pg_config = os.path.join(get_pg_bin(pg_venv), 'pg_config')
    cmd = '{} --version'.format(pg_config)
    version = subprocess.check_output(cmd, shell=True).strip().decode('utf-8').split()[1]

    return version


def available_pg_venvs():
    return os.listdir(get_env_var('PG_VIRTUALENV_HOME'))


def initdb(pg_venv=None, exit_on_fail=False):
    '''
    Run initdb
    '''
    if not pg_venv:
        pg_venv = get_env_var('PG_VENV')

    pg_bin = get_pg_bin(pg_venv)

    cmd = os.path.join(pg_bin, 'initdb -D {}'.format(get_pg_data(pg_venv)))
    initdb_return_code = execute_cmd(cmd, 'Initializing database', process_output=False, exit_on_fail=exit_on_fail)

    return initdb_return_code == 0


def pg_is_running(pg_venv=None):
    '''
    Check if postgres is running
    '''
    if not pg_venv:
        pg_venv = get_env_var('PG_VENV')

    pg_ctl = os.path.join(get_pg_bin(pg_venv), 'pg_ctl')

    if os.path.isfile(pg_ctl):
        cmd = '{} status -D {}'.format(pg_ctl, get_pg_data(pg_venv))
        return_code = execute_cmd(cmd, verbose=False, process_output=False, error_output=False)

        return return_code == 0
    else:
        # binary does not exist so postgres likely isn't running
        return False


def pg_virtualenv_exists(pg_venv):
    return os.path.isdir(get_pg_venv_dir(pg_venv))
