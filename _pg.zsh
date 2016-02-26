#compdef pg

typeset -A opt_args

_arguments -C \
    '1:action:->actions' \
    '*:args:->args' \
    && ret=0

case "$state" in
    (actions)
        local actions; actions=(
            "ck:alias for 'check'"
            "check:run make check in postgresql source dir"
            "c:alias for 'configure'"
            "configure:run ./configure in source dir"
            "get_shell_function:output the wrapper function"
            "h:alias for 'help'"
            "help:display the help text"
            "i:alias for 'install'"
            "install:run make install in source dir"
            "m:alias for 'make'"
            "make:run make in source dir"
            "mc:alias for 'make_clean'"
            "make_clean:run make clean in source dir"
            "start:start a postgresql instance"
            "stop:stop a postgresql instance"
            "w:alias for 'workon'"
            "workon:work on a particular postgresql instance"
        )

        _describe -t actions 'action' actions && ret=0
    ;;
    (args)
        case "$line[1]" in
            (start|stop|workon|w)
                _values 'pg versions' "${(uonzf)$(ls $PG_INSTALL_DIR | cut -d '-' -f 2)}"
            ;;
        esac
    ;;
esac

return 1
