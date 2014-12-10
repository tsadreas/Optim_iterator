'''
    ===============================================
    Miscellaneous functions needed in different stages
    ===============================================

    author: Andreas Tsichritzis <tsadreas@gmail.com>

'''

import os
import sys
import shutil
import csv
import numpy as np
from collections import defaultdict
from operator import itemgetter

path = os.getcwd()

def formatTD(td):
    """ Format time output for report

    """
    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    seconds = td.seconds % 60
    return '%s days %s h %s m %s s' % (days, hours, minutes, seconds)

def structure(case):
    """ Create file structure for the simulation
        Also copies input folder in case folder

    """

    if os.path.exists(path + '/' + case):
        shutil.rmtree(path + '/' + case)

    os.makedirs(path + '/' + case)
    os.makedirs(path + '/' + case + '/evaluations/')
    inputfold = path + '/input/'
    dest = path + '/' + case + '/input/'
    shutil.copytree(inputfold,dest)


def report(x,par,total_time):
    """Create and fill Report file

    """

    file = open("Report.txt", "w+")
    file.write('Initial Solution: \n')
    file.write('----------------- \n')
    init = x['initial_best']
    keys = init.keys()
    line1 = []
    line1.append('Gen')
    line1.append('Ind')
    for i in par:
        line1.append(i)
    line1.append('Fitness')
    for i in keys:
        if i not in line1:
            line1.append(i)
    line = ['{0:>10}'.format(l)[:10] for l in line1]
    file.write('{0}\n'.format(' '.join(map(str, line))))
    line = []
    for j in line1:
        line.append(init.get(j))
    line = ['{0:>10}'.format(l)[:10] for l in line]
    file.write('{0}\n\n'.format(' '.join(map(str, line))))

    file.write('Final Solution: \n')
    file.write('--------------- \n')
    glob = x['global_best']
    keys = glob.keys()
    line1 = []
    line1.append('Gen')
    line1.append('Ind')
    for i in par:
        line1.append(i)
    line1.append('Fitness')
    for i in keys:
        if i not in line1:
            line1.append(i)
    line = ['{0:>10}'.format(l)[:10] for l in line1]
    file.write('{0}\n'.format(' '.join(map(str, line))))
    line = []
    for j in line1:
        line.append(glob.get(j))
    line = ['{0:>10}'.format(l)[:10] for l in line]
    file.write('{0}\n\n'.format(' '.join(map(str, line))))

    file.write('Calculation Time: {0}'.format(total_time))
    file.close()


def find_best(filename,pop):
    """Find best of each generation, global and initial best

    """

    columns = defaultdict(list) # each value in each column is appended to a list

    with open(filename) as f:
        reader = csv.DictReader(f,skipinitialspace=True) # read rows into a dictionary format
        for row in reader: # read a row as {column1: value1, column2: value2,...}
            for (k,v) in row.items(): # go over each column name and value
                columns[k].append(v) # append the value into the appropriate list
    temp = columns.get('Gen')
    temp = [float(i) for i in temp]
    m_temp = max(temp)

    b = []
    for i,v in enumerate(temp):
        if v == m_temp and columns.get('Ind')[i] == '0' or columns.get('Ind')[i] == '0.0':
            gb = i
        if columns.get('Ind')[i] == '0' or columns.get('Ind')[i] == '0.0':
            b.append(i)

    global_best = dict()
    keys = columns.keys()
    for k in keys:
        global_best[k] = columns.get(k)[gb]

    initial_best = dict()
    for k in keys:
        initial_best[k] = columns.get(k)[0]

    best = dict()
    for k in keys:
        best[k] = []
    for i in b:
        for k in keys:
            best[k].append(columns.get(k)[i])

    return {'best':best, 'initial_best':initial_best, 'global_best':global_best }
