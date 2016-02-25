#!/usr/bin/env python3

import sys


USAGE = '''
Usage:
    pg.py <action> [args]

Actions:
    help, h: display this help text
'''


def usage():
    print(USAGE)


def execute_action(action, action_args):
    '''
    Execute the function corresponding to an action
    This action can also be an alias
    '''
    # if action is an existing action name, execute the corresponding function
    if action in ACTIONS.keys():
        if action_args:
            ACTIONS[action](action_args)
        else:
            ACTIONS[action]()

    # if action is an existing alias, then execute the function corresponding to
    # the action
    elif action in ALIASES.keys():
        action = ALIASES[action]
        execute_action(action, action_args)

    # if action isn't recognized, display help and exit
    else:
        print('Unrecognized action {}'.format(action))
        usage()
        exit(-1)



ACTIONS = {
    'help': usage,
}

ALIASES = {
    'h': 'help',
}


if __name__ == '__main__':
    args = sys.argv
    if len(args) < 2:
        usage()
        exit()

    action = args[1]
    action_args = args[2:] if len(args) > 2 else None
    execute_action(action, action_args)
