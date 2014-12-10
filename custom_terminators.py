"""
    ===============================================
    Changed version of inspyred.ec.terminators
    ===============================================
    
    -- Fixes user_termination
    -- Addes convergence_termination

    original author: Aaron Garrett <aaron.lee.garrett@gmail.com>

    modified by: Andreas Tsichritzis <tsadreas@gmail.com>
"""

import itertools
import sys
import time
import csv
from collections import defaultdict



def user_termination(population, num_generations, num_evaluations, args):
    """Return True if user presses the ESC key when prompted.

    This function prompts the user to press the ESC key to terminate the
    evolution. The prompt persists for a specified number of seconds before
    evolution continues. Additionally, the function can be customized to
    allow any press of the ESC key to be stored until the next time this
    function is called.

    .. note::

       This function makes use of the ``msvcrt`` (Windows) and ``curses``
       (Unix) libraries. Other systems may not be supported.

    .. Arguments:
       population -- the population of Individuals
       num_generations -- the number of elapsed generations
       num_evaluations -- the number of candidate solution evaluations
       args -- a dictionary of keyword arguments

    Optional keyword arguments in args:

    - *termination_response_timeout* -- the number of seconds to wait for
      the user to press the ESC key (default 5)
    - *clear_termination_buffer* -- whether the keyboard buffer should be
      cleared before allowing the user to press a key (default True)

    """
    def getch():
        unix = ('darwin', 'linux2')
        if sys.platform not in unix:
            try:
                import msvcrt
            except ImportError:
                return -1
            if msvcrt.kbhit():
                return msvcrt.getch()
            else:
                return -1
        elif sys.platform in unix:
            def _getch(stdscr):
                stdscr.nodelay(1)
                ch = stdscr.getch()
                stdscr.nodelay(0)
                return ch
            import curses
            return curses.wrapper(_getch)

    num_secs = args.get('termination_response_timeout', 5)
    clear_buffer = args.get('clear_termination_buffer', True)
    if clear_buffer:
        while getch() > -1:
            pass
    sys.stdout.write('Press ESC to terminate (%d secs):' % num_secs)
    count = 1
    start = time.time()
    while time.time() - start < num_secs:
        ch = getch()
        if ch > -1 and ch == 27:
            sys.stdout.write('\n\n')
            return True
        elif time.time() - start == count:
            sys.stdout.write('.')
            count += 1
    sys.stdout.write('\n')
    return False



def convergence_termination(population, num_generations, num_evaluations, args):
    """Return True if criteria are fulfilled.

    .. Arguments:
       population -- the population of Individuals
       num_generations -- the number of elapsed generations
       num_evaluations -- the number of candidate solution evaluations
       args -- a dictionary of keyword arguments

    """
    filename = args.get('statistics_file_name')
    columns = defaultdict(list)
    with open(filename) as f:
        reader = csv.DictReader(f,skipinitialspace=True)
        for row in reader: 
            for (k,v) in row.items(): 
                columns[k].append(v)
    fit = []
    for i in range(len(columns.get('Best Fit'))):
        fit.append(float(columns.get('Best Fit')[i]))
    if len(fit) > 3 and abs(fit[-1] - fit[-2]) <= abs(fit[-1]*args.get('tol')):
        if args.get('c_maximize'):
            if fit[-1] >= fit[-2] and fit[-1]>= max(fit):
                stop = True
            else:
                stop = False
        else:
            if fit[-1] <= fit[-2] and fit[-1]<= min(fit):
                stop = True
            else:
                stop = False
    else:
        stop = False
    return stop

