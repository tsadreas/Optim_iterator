'''
    ===============================================
       Changed version of inspyred.ec.observers
    ===============================================
    -- Responses added in file_observer

    -- Fitness plot observer added

    original author: Aaron Garrett <aaron.lee.garrett@gmail.com>

    modified by: Andreas Tsichritzis <tsadreas@gmail.com>
'''

import os
import sys
import inspyred
import csv
import pylab
import time


def file_observer(population, num_generations, num_evaluations, args):
    """Print the output of the evolutionary computation to a file.

    This function saves the results of the evolutionary computation
    to two files. The first file, which by default is named
    'inspyred-statistics-file-<timestamp>.csv', contains the basic
    generational statistics of the population throughout the run
    (worst, best, median, and average fitness and standard deviation
    of the fitness values). The second file, which by default is named
    'inspyred-individuals-file-<timestamp>.csv', contains every individual
    during each generation of the run. Both files may be passed to the
    function as keyword arguments (see below).

    The format of each line of the statistics file is as follows::

       generation number, population size, worst, best, median, average, standard deviation

    The format of each line of the individuals file is as follows::

       generation number, individual number, fitness, string representation of candidate

    .. note::

       This function makes use of the ``fitness_statistics``
       function, so it is subject to the same requirements.

    .. Arguments:
       population -- the population of Individuals
       num_generations -- the number of elapsed generations
       num_evaluations -- the number of candidate solution evaluations
       args -- a dictionary of keyword arguments

    Optional keyword arguments in args:

    - *statistics_file* -- a file object (default: see text)
    - *individuals_file* -- a file object (default: see text)

    """

    try:
        statistics_file = args['statistics_file']
    except KeyError:
        statistics_file = open('inspyred-statistics-file-{0}.csv'.format(time.strftime('%m%d%Y-%H%M%S')), 'w')
        args['statistics_file'] = statistics_file
    try:
        individuals_file = args['individuals_file']
    except KeyError:
        individuals_file = open('inspyred-individuals-file-{0}.csv'.format(time.strftime('%m%d%Y-%H%M%S')), 'w')
        args['individuals_file'] = individuals_file

    candidates = args['par']
    candidates = ['{0:>10}'.format(i)[:10] for i in candidates]
    stats = inspyred.ec.analysis.fitness_statistics(population)
    worst_fit = '{0:>10}'.format(stats['worst'])[:10]
    best_fit = '{0:>10}'.format(stats['best'])[:10]
    avg_fit = '{0:>10}'.format(stats['mean'])[:10]
    med_fit = '{0:>10}'.format(stats['median'])[:10]
    std_fit = '{0:>10}'.format(stats['std'])[:10]


    if num_generations == 0:
        statistics_file.write('{0:>10}, {1:>10}, {2:>10}, {3:>10}, {4:>10}, {5:>10}, {6:>10}\n'.format('Gen',
                                                                                                 'Eval #',
                                                                                                 'Worst Fit',
                                                                                                 'Best Fit',
                                                                                                 'Median Fit',
                                                                                                 'Avg Fit',
                                                                                                 'Std Fit'))
        statistics_file.write('{0:>10}, {1:>10}, {2:>10}, {3:>10}, {4:>10}, {5:>10}, {6:>10}\n'.format(num_generations,
                                                                                                 num_evaluations,
                                                                                                 worst_fit,
                                                                                                 best_fit,
                                                                                                 med_fit,
                                                                                                 avg_fit,
                                                                                                 std_fit))
    else:
        statistics_file.write('{0:>10}, {1:>10}, {2:>10}, {3:>10}, {4:>10}, {5:>10}, {6:>10}\n'.format(num_generations,
                                                                                                 num_evaluations,
                                                                                                 worst_fit,
                                                                                                 best_fit,
                                                                                                 med_fit,
                                                                                                 avg_fit,
                                                                                                 std_fit))
    responses = args['res']
    for i, p in enumerate(population):
        a = ['{0:>10}'.format(l)[:10] for l in p.candidate]
        b = p.responses
        k = []
        v = []
        for key in responses:
            v.append(b[key])
        v = ['{0:>10}'.format(l)[:10] for l in v]
        fit = '{0:>10}'.format(p.fitness)[:10]
        if num_generations == 0 and i == 0:
            r = ['{0:>10}'.format(i)[:10] for i in responses]
            individuals_file.write('{0:>10}, {1:>10}, {2}, {3:>10}, {4}\n'.format('Gen', 'Ind', ', '.join(map(str, candidates)), 'Fitness', ', '.join(map(str, r))))
            individuals_file.write('{0:>10}, {1:>10}, {2}, {3:>10}, {4}\n'.format(num_generations, i, ', '.join(map(str, a)), fit, ', '.join(map(str, v))))
        else:
            individuals_file.write('{0:>10}, {1:>10}, {2}, {3:>10}, {4}\n'.format(num_generations, i, ', '.join(map(str, a)), fit, ', '.join(map(str, v))))
    statistics_file.flush()
    individuals_file.flush()


def fitness_plot_observer(population, num_generations, num_evaluations, args):
    """ Interactive fitness plot while calculating

    """

    import pylab
    import numpy

    stats = inspyred.ec.analysis.fitness_statistics(population)
    best_fitness = stats['best']
    worst_fitness = stats['worst']
    median_fitness = stats['median']
    average_fitness = stats['mean']
    colors = ['black', 'blue', 'green', 'red']
    labels = ['average', 'median', 'best', 'worst']
    data = []
    if num_generations == 0:
        pylab.ion()
        data = [[num_generations], [average_fitness], [median_fitness], [best_fitness], [worst_fitness]]
        lines = []
        for i in range(4):
            line, = pylab.plot(data[0], data[i+1], color=colors[i], label=labels[i])
            lines.append(line)
        # Add the legend when the first data is added.
        pylab.legend(loc='lower right')
        args['plot_data'] = data
        args['plot_lines'] = lines
        pylab.xlabel('Generations')
        pylab.ylabel('Fitness')
    else:
        data = args['plot_data']
        data[0].append(num_generations)
        data[1].append(average_fitness)
        data[2].append(median_fitness)
        data[3].append(best_fitness)
        data[4].append(worst_fitness)
        lines = args['plot_lines']
        for i, line in enumerate(lines):
            line.set_xdata(numpy.array(data[0]))
            line.set_ydata(numpy.array(data[i+1]))
        args['plot_data'] = data
        args['plot_lines'] = lines
    ymin = min([min(d) for d in data[1:]])
    ymax = max([max(d) for d in data[1:]])
    yrange = ymax - ymin
    pylab.xlim((0, num_evaluations))
    pylab.ylim((ymin - 0.1*yrange, ymax + 0.1*yrange))
    pylab.draw()
    pylab.pause(1)
