#compdef pg

typeset -A opt_args

_arguments -C \
    '1:action:->actions' \
    '*:args:->args' \
    && ret=0

case "$state" in
    (actions)
        local actions; actions=(
            "configure:run ./configure in source dir"
            "create_virtualenv:create a new virtualenv"
            "fetch_pg_source:fetch postgresql's source code"
            "get_shell_function:output the wrapper function"
            "install:run make install in source dir"
            "list:list pg_venv and show which ones are active"
            "l:alias for 'log'"
            "log:display server log"
            "make:run make in source dir"
            "make_check:run make check in postgresql source dir"
            "make_clean:run make clean in source dir"
            "restart:stops and starts the server"
            "rm_data:remove the data of a postgresql instance"
            "rm_virtualenv:remove a virtualenv"
            "start:start a postgresql instance"
            "stop:stop a postgresql instance"
            "w:alias for 'workon'"
            "workon:work on a particular postgresql instance"
        )

        _describe -t actions 'action' actions && ret=0
    ;;
    (args)
        case "$line[1]" in
            (l|log|rm_virtualenv|start|stop|w|workon)
                _values 'pg versions' "${(uonzf)$(ls $PG_VIRTUALENV_HOME)}"
            ;;
        esac
    ;;
esac

return 1
