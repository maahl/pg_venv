# pg\_venv

This is a wrapper script for various PostgreSQL common actions.
It is intended for PostgreSQL development purposes, and has not been thoroughly
tested. Use at your own risks.

It is inspired by python virtualenv: when working in a pg\_venv, the relevant
environment variables are set so that you don't have to worry about it
yourself.

Each pg\_venv has its own copy of postgresql's source code, its binaries, its
data directory, its config and its log file.

Different pg\_venv can use different versions of PostgreSQL without problem.
Several instances can be run at the same time, they will all use the appropriate
binaries and data directories, and a different port each, so that they can run
simultaneously.

The port number is derived from the name of the venv; there can be collisions
and they are not handled. If you encounter one, you should just change the name
of the venv (moving the relevant directories manually might be relevant in case
you don't want to reinsert all the data and/or recompile postgres).

A completion file for zsh is provided.

# Installation

To install it, you just need to define a few environment variables in your
bashrc, and to source the output of `./pg_venv.py get_shell_function`.

It generates a bash function to determine at runtime if the output of a command
should be displayed (general case) or sourced (currently, only needed when
switching venv). A comment in the output of this function will tell you the
exact line you should copy in your bashrc.

The meaning of the variables is explained in the help text: `./pg_venv.py
--help`.

For example, in your bashrc:

```sh
# location of postgresql's git repository
export PG_DIR=$HOME/projects/postgresql
# location where pg_venvs will be stored
export PG_VIRTUALENV_HOME=$HOME/.pg_virtualenvs
# options to pass to the configure script for compiling postgresql
export PG_CONFIGURE_OPTIONS="--enable-cassert --enable-debug --enable-depend"
# define the pg function
source <(/home/user/projects/pg_venv/pg_venv get_shell_function)
```

If necessary, correct the path to the script, it's possible in some cases that
the function can't reliably display the correct one.

# Usage

All the functions can be called from anywhere in your filesystem: paths are
derived from the environment variables, not from your current working directory.

Example usage:

```sh
# create a pg_venv
# this will create a new git worktree of postgresql and a branch named after your 
# pg_venv, compile the code, install it, start the server and create a
# db
pg create_virtualenv awesomefeature

# enter a pg_venv
# this will set several env variables derived from the name of the venv, e.g.
# the install directory, data directory, shell prompt, etc.
pg workon awesomefeature
psql

# write your patch for postgres
# $PG_SRC points to the git worktree for the current pg_venv.
cd $PG_SRC
$EDITOR

# recompile postgres
# note: the following actions do nothing but call the underlying program
# (make); they are here merely because they allow to compile
# postgres without moving to its source tree.
pg make -- -j 8 # you can pass arguments to make
pg check # make check
pg install # runs make install

# initialize the database, your $PATH has been updated to include the 
# appropriate binaries for the current pg_venv
initdb
pg start # start postgres
pg log # check the logs, in case there was a problem
createdb
psql
pg stop

# you can run another instance at the same time
# this one will use the code from postgresql's REL_12_1 commit
pg create_virtualenv anotherfeature --pg-branch REL_12_1
pg log anotherfeature
pg workon anotherfeature
pg list
psql
pg stop awesomefeature
pg stop # defaults to current pg_venv

pg rm_data # it will ask to type the name of the venv as a confirmation
pg rm_virtualenv
```
