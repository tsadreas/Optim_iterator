'''
    ===============================================
    Functions called when ploting the results
    ===============================================

    author: Andreas Tsichritzis <tsadreas@gmail.com>

'''
import os
import csv
import math
import pylab
import matplotlib.font_manager
import matplotlib.pyplot as plt
import scipy
import numpy as np
import misc
from matplotlib.ticker import ScalarFormatter, FormatStrFormatter

class FixedOrderFormatter(ScalarFormatter):
    def __init__(self, order_of_mag=0, useOffset=True, useMathText=False):
        self._order_of_mag = order_of_mag
        ScalarFormatter.__init__(self, useOffset=useOffset, useMathText=useMathText)
    def _set_orderOfMagnitude(self, range):
        """Over-riding this to avoid having orderOfMagnitude reset elsewhere"""
        self.orderOfMagnitude = self._order_of_mag

path = os.getcwd()

def generation_plot(filename,case):
    """Plot the results of the algorithm using generation statistics.

    """
    generation = []
    psize = []
    worst = []
    best = []
    median = []
    average = []
    stdev = []
    reader = csv.reader(open(filename))
    reader.next()
    for row in reader:
        generation.append(int(row[0]))
        psize.append(int(row[1]))
        worst.append(float(row[2]))
        best.append(float(row[3]))
        median.append(float(row[4]))
        average.append(float(row[5]))
        stdev.append(float(row[6]))
    stderr = [s / math.sqrt(p) for s, p in zip(stdev, psize)]

    data = [average, median, best, worst]
    colors = ['black', 'blue', 'green', 'red']
    labels = ['average', 'median', 'best', 'worst']
    figure = plt.figure()
    ax = plt.axes()
    plt.plot(generation, average, color=colors[0], label=labels[0])
    for d, col, lab in zip(data[1:], colors[1:], labels[1:]):
        plt.plot(generation, d, color=col, label=lab)
    plt.fill_between(generation, data[2], data[3], color='#e6f2e6')
    ymin = min([min(d) for d in data])
    ymax = max([max(d) for d in data])
    yrange = ymax - ymin
    plt.ylim((ymin - 0.1*yrange, ymax + 0.1*yrange))
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif', serif='Computer Modern Roman',size=22)
    plt.rc('lines', linewidth=1.5)
    plt.xlabel('Generation')
    plt.ylabel('Fitness')
    yls = int(math.log10(abs(ymax)))
    ax.get_yaxis().set_major_formatter(FixedOrderFormatter(yls))
    plt.legend(bbox_to_anchor=(0., 1.0, 1., .10), loc=1, ncol=4, mode="expand", borderaxespad=0.)
    figure = plt.gcf()
    figure.set_size_inches(23.833,16.1944)
    filename = path + '/' + case + '/fitness.png'
    plt.savefig(filename, dpi = 72,bbox_inches='tight')

def responses_plot(matrix, par, units, strings, case):
    """Plots responses vs Fitness and prints responses file

    """

    keys =  matrix.keys()

    for k in keys:
        if k != 'Fitness' and k not in par and k !='Ind':
            if matrix.get(k) == matrix.get('Fitness'):
                objective = k
    os.chdir(path + '/' + case + '/')


    for k in keys:
        if k != 'Fitness' and k != objective and k != 'Gen' and k not in par and k !='Ind':
            fig, ax1 = plt.subplots()
            plt.rc('text', usetex=True)
            plt.rc('font', family='serif', serif='Computer Modern Roman',size=22)
            plt.rc('lines', linewidth=1.5)
            x = matrix.get('Gen')
            s1 = matrix.get(objective)
            line1 = ax1.plot(x, s1, 'b',label = strings.get(objective))
            ymax = max([float(i) for i in s1])
            yls = int(math.log10(abs(ymax)))
            ax1.set_xlabel('Generations')
            ax1.set_ylabel(strings.get(objective) + units.get(objective))
            ax1.get_yaxis().set_major_formatter(FixedOrderFormatter(yls-1))
            ax2 = ax1.twinx()
            s2 = matrix.get(k)
            line2 = ax2.plot(x, s2, 'r', label = strings.get(k))
            ymax = max([float(i) for i in s2])
            yls = int(math.log10(abs(ymax)))
            lns = line1 + line2
            labs = [l.get_label() for l in lns]
            ax2.set_ylabel(strings.get(k) + units.get(k))
            ax2.get_yaxis().set_major_formatter(FixedOrderFormatter(yls-1))
            plt.legend(lns, labs,bbox_to_anchor=(0., 1.0, 1., .10), loc=1, ncol=4, mode="expand", borderaxespad=0.)
            filename = k+'.png'
            figure = plt.gcf()
            figure.set_size_inches(23.833,16.1944)
            plt.savefig(filename, dpi = 72,bbox_inches='tight')


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

    file = open('responses.csv','w+')
    file.write('{0}\n'.format(', '.join(map(str, line))))

    for i in range(len(matrix.get('Gen'))):
        line = []
        for j in line1:
            line.append(matrix.get(j)[i])
        line = ['{0:>10}'.format(l)[:10] for l in line]
        file.write('{0}\n'.format(', '.join(map(str, line))))
    file.close()

