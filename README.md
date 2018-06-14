# pg\_wrapper

This is a wrapper script for various PostgreSQL common actions.
It is intended for PostgreSQL development purposes, and has not been thoroughly
tested. Use at your own risks.

It is inspired by python virtualenv: when working in a pg\_venv, the relevant
environment variables are set so that you don't have to worry about it
yourself.

Different pg\_venv can use different versions of PostgreSQL without problem.
Several instances can be run at the same time, they will all use the appropriate
binaries and data directories, and a different port each.

The port number is derived from the name of the venv; there can be collisions
and they are not handled. If you encounter one, you should just change the name
of the venv (moving the relevant directories manually might be relevant in case
you don't want to reinsert all the data and/or recompile postgres).

A completion file for zsh is provided.

# Installation

To install it, you just need to define a few environment variables in your
bashrc, and to source the output of `./pg_wrapper.py get_shell_function`.

It generates a bash function to determine at runtime if the output of a command
should be displayed (general case) or sourced (currently, only needed when
switching venv). A comment in the output of this function will tell you the
exact line you should copy in your bashrc.

The meaning of the variables is explained in the help text: `./pg_wrapper.py
--help`.

For example, in your bashrc:

```
export PG_DIR=$HOME/projects/postgresql
export PG_VIRTUALENV_HOME=$HOME/.pg_virtualenvs
export PG_CONFIGURE_OPTIONS="--enable-cassert --enable-debug --enable-depend"
source <(/home/user/projects/pg_wrapper/pg_wrapper.py get_shell_function)
```

If necessary, correct the path to the script, it's possible in some cases that
the function can't reliably display the correct one.

# Usage

All the functions can be called from anywhere in your filesystem: paths are
derived from the environment variables, not from your current working directory.

Example usage:

```sh
# create a pg_venv
# this will copy postgres' source, compile it, install it, start it and create a
# db
pg create_virtualenv awesomefeature

# enter a pg_venv
# this will set several env variables derived from the name of the venv, e.g.
# the install directory, data directory, shell prompt, etc.
pg workon awesomefeature

# recompile postgres
# note: the following actions do nothing but call the underlying programs
# (configure and make); they are here merely because they allow to compile
# postgres without moving to its source tree.
pg configure
pg make -j 8 # you can pass arguments to make
pg check # make check
pg install # runs make install

# initialize the database
initdb
pg start # start postgres
pg log # check the logs, in case there was a problem
createdb
psql # hack around
pg stop
pg rmdata # it will ask to type the name of the venv as a confirmation

```
