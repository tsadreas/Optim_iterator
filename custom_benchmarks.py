import os
import sys
import shutil
import inspyred
import numpy as np
import random
import math
from collections import defaultdict
import csv

path = os.getcwd()

class Benchmark(object):
    """Defines a global optimization benchmark problem.

    This abstract class defines the basic structure of a global
    optimization problem. Subclasses should implement the ``generator``
    and ``evaluator`` methods for a particular optimization problem,
    which can be used with inspyred's evolutionary computations.

    In addition to being used with evolutionary computations, subclasses
    of this class are also callable. The arguments passed to such a call
    are combined into a list and passed as the single candidate to the
    evaluator method. The single calculated fitness is returned. What
    this means is that a given benchmark can act as a mathematical function
    that takes arguments and returns the value of the function, like the
    following example.::

        my_function = benchmarks.Ackley(2)
        output = my_function(-1.5, 4.2)

    Public Attributes:

    - *dimensions* -- the number of inputs to the problem
    - *objectives* -- the number of outputs of the problem (default 1)
    - *bounder* -- the bounding function for the problem (default None)
    - *maximize* -- whether the problem is one of maximization (default
      True)

    """
    def __init__(self, dimensions, objectives=1, maximize = True):
        self.dimensions = dimensions
        self.objectives = objectives
        self.bounder = None
        self.maximize = maximize

    def __str__(self):
        if self.objectives > 1:
            return '{0} ({1} dimensions, {2} objectives)'.format(self.__class__.__name__, self.dimensions, self.objectives)
        else:
            return '{0} ({1} dimensions)'.format(self.__class__.__name__, self.dimensions)

    def __repr__(self):
        return self.__class__.__name__

    def generator(self, random, args):
        """The generator function for the benchmark problem."""
        raise NotImplementedError

    def evaluator(self, candidates, args):
        """The evaluator function for the benchmark problem."""
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        candidate = [a for a in args]
        fit = self.evaluator([candidate], kwargs)
        return fit[0]


class StyblinskiTang(Benchmark):
    """Defines the Styblinski-Tang benchmark problem.

    .. math::

        f(x) = 1/2 \sum_{i=1}^{d} (x_i^4 - 16x_i^2 + 5x_i)

    Public Attributes:

    - *global_optimum* -- the problem input that produces the optimum output.
      Here, this corresponds to [0, 0, ..., 0].

    """
    def __init__(self, dimensions=2,maximize=False):
        Benchmark.__init__(self, dimensions)
        self.bounder = inspyred.ec.Bounder([0] * self.dimensions, [1] * self.dimensions)
        self.maximize = maximize
        self.global_optimum = [2.903 for _ in range(self.dimensions)]
        self.candidates = []

    def generator(self, random, args):
        i_pop= args['initial_pop']
        c = i_pop[len(self.candidates)]
        self.candidates.append(c)
        return c


def correct_par(filename,par):
    columns = defaultdict(list) # each value in each column is appended to a list
    with open(filename) as f:
        reader = csv.DictReader(f,skipinitialspace=True) # read rows into a dictionary format
        for row in reader: # read a row as {column1: value1, column2: value2,...}
            for (k,v) in row.items(): # go over each column name and value
                columns[k].append(v) # append the value into the appropriate list
        keys = columns.keys()
        for p in par:
            if p in keys:
                col = []
                for i,k in enumerate(columns[p]):
                    k = float(k)
                    if p in par:
                        n = 10*k-5
                    col.append(n)
                columns[p] = col

    outputfile = filename

    file = open(outputfile,'w+')
    head = []
    head.append('Gen')
    head.append('Ind')
    for i in par:
        head.append(i)
    head.append('Fitness')
    for i in keys:
        if i not in head:
            head.append(i)
    par = ['{0:>10}'.format(i)[:10] for i in par]
    line = ['{0:>10}'.format(l)[:10] for l in head]
    file.write('{0}\n'.format(', '.join(map(str, line))))
    for i in range(len(columns.get('Gen'))):
        line = []
        for j in head:
            line.append(columns.get(j)[i])
        line = ['{0:>10}'.format(l)[:10] for l in line]
        file.write('{0}\n'.format(', '.join(map(str, line))))
    file.close()