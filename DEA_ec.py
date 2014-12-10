'''
    ===============================================
       Changed version of inspyred.ec
    ===============================================

    -- Is called when using DEA strategies
    -- DEA strategies implementation is based on PAGMO

    modified by: Andreas Tsichritzis <tsadreas@gmail.com>
'''

import collections
import copy
import functools
from inspyred.ec import archivers
from inspyred.ec import generators
from inspyred.ec import migrators
from inspyred.ec import observers
from inspyred.ec import replacers
from inspyred.ec import selectors
from inspyred.ec import terminators
from inspyred.ec import variators
import itertools
import logging
import math
import time
import random
import numpy as np
import custom_replacer

class Error(Exception):
    """An empty base exception."""
    pass


class EvolutionExit(Error):
    """An exception that may be raised and caught to end the evolution.

    This is an empty exception class that can be raised by the user
    at any point in the code and caught outside of the ``evolve``
    method.

    .. note::

       Be aware that ending the evolution in such a way will almost
       certainly produce an erroneous population (e.g., not all
       individuals will have been reevaluated, etc.). However, this
       approach can be viable if solutions have been archived such
       that the current population is not of critical importance.

    """
    pass


class Bounder(object):
    """Defines a basic bounding function for numeric lists.

    This callable class acts as a function that bounds a
    numeric list between the lower and upper bounds specified.
    These bounds can be single values or lists of values. For
    instance, if the candidate is composed of five values, each
    of which should be bounded between 0 and 1, you can say
    ``Bounder([0, 0, 0, 0, 0], [1, 1, 1, 1, 1])`` or just
    ``Bounder(0, 1)``. If either the ``lower_bound`` or
    ``upper_bound`` argument is ``None``, the Bounder leaves
    the candidate unchanged (which is the default behavior).

    As an example, if the bounder above were used on the candidate
    ``[0.2, -0.1, 0.76, 1.3, 0.4]``, the resulting bounded
    candidate would be ``[0.2, 0, 0.76, 1, 0.4]``.

    A bounding function is necessary to ensure that all
    evolutionary operators respect the legal bounds for
    candidates. If the user is using only custom operators
    (which would be aware of the problem constraints), then
    those can obviously be tailored to enforce the bounds
    on the candidates themselves. But the built-in operators
    make only minimal assumptions about the candidate solutions.
    Therefore, they must rely on an external bounding function
    that can be user-specified (so as to contain problem-specific
    information).

    In general, a user-specified bounding function must accept
    two arguments: the candidate to be bounded and the keyword
    argument dictionary. Typically, the signature of such a
    function would be the following::

        bounded_candidate = bounding_function(candidate, args)

    This function should return the resulting candidate after
    bounding has been performed.

    Public Attributes:

    - *lower_bound* -- the lower bound for a candidate
    - *upper_bound* -- the upper bound for a candidate

    """
    def __init__(self, lower_bound=None, upper_bound=None):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        if self.lower_bound is not None and self.upper_bound is not None:
            if not isinstance(self.lower_bound, collections.Iterable):
                self.lower_bound = itertools.repeat(self.lower_bound)
            if not isinstance(self.upper_bound, collections.Iterable):
                self.upper_bound = itertools.repeat(self.upper_bound)

    def __call__(self, candidate, args):
        # The default would be to leave the candidate alone
        # unless both bounds are specified.
        if self.lower_bound is None or self.upper_bound is None:
            return candidate
        else:
            if not isinstance(self.lower_bound, collections.Iterable):
                self.lower_bound = [self.lower_bound] * len(candidate)
            if not isinstance(self.upper_bound, collections.Iterable):
                self.upper_bound = [self.upper_bound] * len(candidate)
            bounded_candidate = candidate
            for i, (c, lo, hi) in enumerate(zip(candidate, self.lower_bound,
                                                self.upper_bound)):
                bounded_candidate[i] = max(min(c, hi), lo)
            return bounded_candidate


class DiscreteBounder(object):
    """Defines a basic bounding function for numeric lists of discrete values.

    This callable class acts as a function that bounds a
    numeric list to a set of legitimate values. It does this by
    resolving a given candidate value to the nearest legitimate
    value that can be attained. In the event that a candidate value
    is the same distance to multiple legitimate values, the legitimate
    value appearing earliest in the list will be used.

    For instance, if ``[1, 4, 8, 16]`` was used as the *values* parameter,
    then the candidate ``[6, 10, 13, 3, 4, 0, 1, 12, 2]`` would be
    bounded to ``[4, 8, 16, 4, 4, 1, 1, 8, 1]``.

    Public Attributes:

    - *values* -- the set of attainable values
    - *lower_bound* -- the smallest attainable value
    - *upper_bound* -- the largest attainable value

    """
    def __init__(self, values):
        self.values = values
        self.lower_bound = itertools.repeat(min(self.values))
        self.upper_bound = itertools.repeat(max(self.values))

    def __call__(self, candidate, args):
        if not isinstance(self.lower_bound, collections.Iterable):
            self.lower_bound = [min(self.values)] * len(candidate)
        if not isinstance(self.upper_bound, collections.Iterable):
            self.upper_bound = [max(self.values)] * len(candidate)
        closest = lambda target: min(self.values, key=lambda x: abs(x-target))
        bounded_candidate = candidate
        for i, c in enumerate(bounded_candidate):
            bounded_candidate[i] = closest(c)
        return bounded_candidate


class Individual(object):
    """Represents an individual in an evolutionary computation.

    An individual is defined by its candidate solution and the
    fitness (or value) of that candidate solution. Individuals
    can be compared with one another by using <, <=, >, and >=.
    In all cases, such comparisons are made using the individuals'
    fitness values. The ``maximize`` attribute is respected in all
    cases, so it is better to think of, for example, < (less-than)
    to really mean "worse than" and > (greater-than) to mean
    "better than". For instance, if individuals a and b have fitness
    values 2 and 4, respectively, and if ``maximize`` were ``True``,
    then a < b would be true. If ``maximize`` were ``False``, then
    a < b would be false (because a is "better than" b in terms of
    the fitness evaluation, since we're minimizing).

    .. note::

       ``Individual`` objects are almost always created by the EC,
       rather than the user. The ``evolve`` method of the EC also
       has a ``maximize`` argument, whose value is passed directly
       to all created individuals.

    Public Attributes:

    - *candidate* -- the candidate solution
    - *fitness* -- the value of the candidate solution
    - *birthdate* -- the system time at which the individual was created
    - *maximize* -- Boolean value stating use of maximization

    """
    def __init__(self, candidate=None, maximize=True):
        self._candidate = candidate
        self.fitness = None
        self.birthdate = time.time()
        self.maximize = maximize
        self.responses = None

    @property
    def candidate(self):
        return self._candidate

    @candidate.setter
    def candidate(self, value):
        self._candidate = value
        self.fitness = None
        self.responses = None

    def __str__(self):
        return '{0} : {1}, {2}'.format(self.candidate, self.fitness, self.responses)

    def __repr__(self):
        return '<Individual: candidate = {0}, fitness = {1}, birthdate = {2}>'.format(self.candidate, self.fitness, self.birthdate)

    def __lt__(self, other):
        if self.fitness is not None and other.fitness is not None:
            if self.maximize:
                return self.fitness < other.fitness
            else:
                return self.fitness > other.fitness
        else:
            raise Error('fitness cannot be None when comparing Individuals')

    def __le__(self, other):
        return self < other or not other < self

    def __gt__(self, other):
        if self.fitness is not None and other.fitness is not None:
            return other < self
        else:
            raise Error('fitness cannot be None when comparing Individuals')

    def __ge__(self, other):
        return other < self or not self < other

    def __eq__(self, other):
        return ((self._candidate, self.fitness, self.maximize) ==
                (other._candidate, other.fitness, other.maximize))

    def __ne__(self, other):
        return not (self == other)



class EvolutionaryComputation(object):
    """Represents a basic evolutionary computation.

    This class encapsulates the components of a generic evolutionary
    computation. These components are the selection mechanism, the
    variation operators, the replacement mechanism, the migration
    scheme, the archival mechanism, the terminators, and the observers.

    The ``observer``, ``terminator``, and ``variator`` attributes may be
    specified as lists of such operators. In the case of the ``observer``,
    all elements of the list will be called in sequence during the
    observation phase. In the case of the ``terminator``, all elements of
    the list will be combined via logical ``or`` and, thus, the evolution will
    terminate if any of the terminators return True. Finally, in the case
    of the ``variator``, the elements of the list will be applied one
    after another in pipeline fashion, where the output of one variator
    is used as the input to the next.

    Public Attributes:

    - *selector* -- the selection operator (defaults to ``default_selection``)
    - *variator* -- the (possibly list of) variation operator(s) (defaults to
      ``default_variation``)
    - *replacer* -- the replacement operator (defaults to
      ``default_replacement``)
    - *migrator* -- the migration operator (defaults to ``default_migration``)
    - *archiver* -- the archival operator (defaults to ``default_archiver``)
    - *observer* -- the (possibly list of) observer(s) (defaults to
      ``default_observer``)
    - *terminator* -- the (possibly list of) terminator(s) (defaults to
      ``default_termination``)
    - *logger* -- the logger to use (defaults to the logger 'inspyred.ec')

    The following attributes do not have legitimate values until after
    the ``evolve`` method executes:

    - *termination_cause* -- the name of the function causing
      ``evolve`` to terminate, in the event that multiple terminators are used
    - *generator* -- the generator function passed to ``evolve``
    - *evaluator* -- the evaluator function passed to ``evolve``
    - *bounder* -- the bounding function passed to ``evolve``
    - *maximize* -- Boolean stating use of maximization passed to ``evolve``
    - *archive* -- the archive of individuals
    - *population* -- the population of individuals
    - *num_evaluations* -- the number of fitness evaluations used
    - *num_generations* -- the number of generations processed

    Note that the attributes above are, in general, not intended to
    be modified by the user. (They are intended for the user to query
    during or after the ``evolve`` method's execution.) However,
    there may be instances where it is necessary to modify them
    within other functions. This is possible to do, but it should be the
    exception, rather than the rule.

    If logging is desired, the following basic code segment can be
    used in the ``main`` or calling scope to accomplish that::

        import logging
        logger = logging.getLogger('inspyred.ec')
        logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler('inspyred.log', mode='w')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    Protected Attributes:

    - *_random* -- the random number generator object
    - *_kwargs* -- the dictionary of keyword arguments initialized
      from the *args* parameter in the *evolve* method

    """
    def __init__(self, random):
        self.selector = selectors.default_selection
        self.strategy = None
        self.variator = variators.default_variation
        self.replacer = replacers.default_replacement
        self.migrator = migrators.default_migration
        self.observer = observers.default_observer
        self.archiver = archivers.default_archiver
        self.terminator = terminators.default_termination
        self.termination_cause = None
        self.generator = None
        self.evaluator = None
        self.bounder = None
        self.maximize = True
        self.archive = None
        self.population = None
        self.num_evaluations = 0
        self.num_generations = 0
        self.logger = logging.getLogger('inspyred.ec')
        try:
            self.logger.addHandler(logging.NullHandler())
        except AttributeError:
            # If Python < 2.7, then NullHandler doesn't exist.
            pass
        self._random = random
        self._kwargs = dict()

    def _should_terminate(self, pop, ng, ne):
        terminate = False
        fname = ''
        if isinstance(self.terminator, collections.Iterable):
            for clause in self.terminator:
                self.logger.debug('termination test using {0} at generation {1} and evaluation {2}'.format(clause.__name__, ng, ne))
                terminate = terminate or clause(population=pop, num_generations=ng, num_evaluations=ne, args=self._kwargs)
                if terminate:
                    fname = clause.__name__
                    break
        else:
            self.logger.debug('termination test using {0} at generation {1} and evaluation {2}'.format(self.terminator.__name__, ng, ne))
            terminate = self.terminator(population=pop, num_generations=ng, num_evaluations=ne, args=self._kwargs)
            fname = self.terminator.__name__
        if terminate:
            self.termination_cause = fname
            self.logger.debug('termination from {0} at generation {1} and evaluation {2}'.format(self.termination_cause, ng, ne))
        return terminate


    def evolve(self, generator, evaluator, pop_size=100, seeds=None, maximize=True, bounder=None, **args):
        """Perform the evolution.


        - *_ec* -- the evolutionary computation (this object)

        """
        self._kwargs = args
        self._kwargs['_ec'] = self

        if seeds is None:
            seeds = []
        if bounder is None:
            bounder = Bounder()

        self.termination_cause = None
        self.generator = generator
        self.evaluator = evaluator
        self.bounder = bounder
        self.maximize = maximize
        self.population = []
        self.archive = []

        # Create the initial population.
        if not isinstance(seeds, collections.Sequence):
            seeds = [seeds]
        initial_cs = copy.copy(seeds)
        num_generated = max(pop_size - len(seeds), 0)
        i = 0
        self.logger.debug('generating initial population')
        while i < num_generated:
            cs = generator(random=self._random, args=self._kwargs)
            initial_cs.append(cs)
            i += 1
        self.logger.debug('evaluating initial population')
        initial_fit, initial_res = evaluator(candidates=initial_cs, args=self._kwargs)
        for cs, fit, res in zip(initial_cs, initial_fit, initial_res):
            if fit is not None:
                ind = Individual(cs, maximize=maximize)
                ind.fitness = fit
                ind.responses = res
                self.population.append(ind)
            else:
                self.logger.warning('excluding candidate {0} because fitness received as None'.format(cs))
        self.logger.debug('population size is now {0}'.format(len(self.population)))

        self.num_evaluations = len(initial_fit)
        self.num_generations = 0

        self.logger.debug('archiving initial population')
        self.archive = self.archiver(random=self._random, population=list(self.population), archive=list(self.archive), args=self._kwargs)
        self.logger.debug('archive size is now {0}'.format(len(self.archive)))
        self.logger.debug('population size is now {0}'.format(len(self.population)))

        if isinstance(self.observer, collections.Iterable):
            for obs in self.observer:
                self.logger.debug('observation using {0} at generation {1} and evaluation {2}'.format(obs.__name__, self.num_generations, self.num_evaluations))
                obs(population=list(self.population), num_generations=self.num_generations, num_evaluations=self.num_evaluations, args=self._kwargs)
        else:
            self.logger.debug('observation using {0} at generation {1} and evaluation {2}'.format(self.observer.__name__, self.num_generations, self.num_evaluations))
            self.observer(population=list(self.population), num_generations=self.num_generations, num_evaluations=self.num_evaluations, args=self._kwargs)




        best = max(self.population)
        gbfit = best.fitness
        gbX = best.candidate

        gbIter = gbX

        NP = len(self.population)
        D = len(gbX)

        parent_cs = [copy.deepcopy(i.candidate) for i in self.population]
        parent_fit = [copy.deepcopy(i.fitness) for i in self.population]
        parents = copy.deepcopy(self.population)

        m_f = float(args['mutation_rate'])
        m_cr = float(args['crossover_rate'])

        while not self._should_terminate(list(self.population), self.num_generations, self.num_evaluations):
            offspring_cs = []

            for i in range(0,NP):

                ### pick random population memebers
                while True:
                    r1 = random.randint(0,NP-1)
                    if r1!=i:
                        break
                while True:
                    r2 = random.randint(0,NP-1)
                    if r2!=i and r2!=r1:
                        break
                while True:
                    r3 = random.randint(0,NP-1)
                    if r3!=i and r3!=r2 and r3!=r1:
                        break
                while True:
                    r4 = random.randint(0,NP-1)
                    if r4!=i and r4!=r3 and r4!=r2 and r4!=r1:
                        break
                while True:
                    r5 = random.randint(0,NP-1)
                    if r5!=i and r5!=r4 and r4!=r3 and r4!=r2 and r4!=r1:
                        break

                strategy = self.strategy

                if strategy == 'DE/best/1/exp':
                    n = random.randint(0,D-1)
                    L = 0
                    tmp = parent_cs[i]
                    while L < D:
                        tmp[n] = gbIter[n] + m_f*(parent_cs[r2][n]-parent_cs[r3][n])
                        n = (n+1)%D
                        L += 1
                        m_dprn = random.random()
                        if m_cr < m_dprn:
                            break
                elif strategy == 'DE/rand/1/exp':
                    n = random.randint(0,D-1)
                    L = 0
                    tmp = parent_cs[i]
                    while L < D:
                        tmp[n] = parent_cs[r1][n] + m_f*(parent_cs[r2][n]-parent_cs[r3][n])
                        n = (n+1)%D
                        L += 1
                        m_dprn = random.random()
                        if m_cr < m_dprn:
                            break
                elif strategy == 'DE/rand-to-best/1/exp':
                    n = random.randint(0,D-1)
                    L = 0
                    tmp = parent_cs[i]
                    while L < D:
                        tmp[n] = tmp[n] + m_f*(gbIter[n] - tmp[n]) + m_f*(parent_cs[r1][n]-parent_cs[r2][n])
                        n = (n+1)%D
                        L += 1
                        m_dprn = random.random()
                        if m_cr < m_dprn:
                            break
                elif strategy == 'DE/best/2/exp':
                    n = random.randint(0,D-1)
                    L = 0
                    tmp = parent_cs[i]
                    while L < D:
                        tmp[n] = gbIter[n] + (parent_cs[r1][n]+parent_cs[r2][n]-parent_cs[r3][n]-parent_cs[r4][n])*m_f
                        n = (n+1)%D
                        L += 1
                        m_dprn = random.random()
                        if m_cr < m_dprn:
                            break
                elif strategy == 'DE/rand/2/exp':
                    n = random.randint(0,D-1)
                    L = 0
                    tmp = parent_cs[i]
                    while L < D:
                        tmp[n] = parent_cs[r5][n] + (parent_cs[r1][n]+parent_cs[r2][n]-parent_cs[r3][n]-parent_cs[r4][n])*m_f
                        n = (n+1)%D
                        L += 1
                        m_dprn = random.random()
                        if m_cr < m_dprn:
                            break
                elif strategy == 'DE/best/1/bin':
                    n = random.randint(0,D-1)
                    tmp = parent_cs[i]
                    for L in range(0,D):
                        m_dprn = random.random()
                        if m_dprn < m_cr or L+1 == D:
                            tmp[n] = gbIter[n] + m_f*(parent_cs[r2][n]-parent_cs[r3][n])
                elif strategy == 'DE/rand/1/bin':
                    n = random.randint(0,D-1)
                    tmp = parent_cs[i]
                    for L in range(0,D):
                        m_dprn = random.random()
                        if m_dprn < m_cr or L+1 == D:
                            tmp[n] = parent_cs[r1][n] + m_f*(parent_cs[r2][n]-parent_cs[r3][n])
                elif strategy == 'DE/rand-to-best/1/bin':
                    n = random.randint(0,D-1)
                    tmp = parent_cs[i]
                    for L in range(0,D):
                        m_dprn = random.random()
                        if m_dprn < m_cr or L+1 == D:
                            tmp[n] = tmp[n] + m_f*(gbIter[n] - tmp[n]) + m_f*(parent_cs[r1][n]-parent_cs[r2][n])
                elif strategy == 'DE/best/2/bin':
                    n = random.randint(0,D-1)
                    tmp = parent_cs[i]
                    for L in range(0,D):
                        m_dprn = random.random()
                        if m_dprn < m_cr or L+1 == D:
                            tmp[n] = gbIter[n] +(parent_cs[r1][n]+parent_cs[r2][n]-parent_cs[r3][n]-parent_cs[r4][n])*m_f
                elif strategy == 'DE/rand/2/bin':
                    n = random.randint(0,D-1)
                    tmp = parent_cs[i]
                    for L in range(0,D):
                        m_dprn = random.random()
                        if m_dprn < m_cr or L+1 == D:
                            tmp[n] = parent_cs[r5][n] + (parent_cs[r1][n]+parent_cs[r2][n]-parent_cs[r3][n]-parent_cs[r4][n])*m_f

                # check if mutated are in bounds
                for i2 in range(D):
                    if tmp[i2] > 1 or tmp[i2]<0:
                        tmp[i2] = round(random.random(),3)

                offspring_cs.append(tmp)

            offspring_fit, offspring_res = evaluator(candidates=offspring_cs, args=self._kwargs)

            offspring = []

            for cs, fit, res in zip(offspring_cs, offspring_fit, offspring_res):
                if fit is not None:
                    off = Individual(cs, maximize=maximize)
                    off.fitness = fit
                    off.responses = res
                    offspring.append(off)
                else:
                    self.logger.warning('excluding candidate {0} because fitness received as None'.format(cs))
            self.num_evaluations += len(offspring_fit)

            gbIter = gbX

            # Replace individuals.
            self.logger.debug('replacement using {0} at generation {1} and evaluation {2}'.format(self.replacer.__name__, self.num_generations, self.num_evaluations))
            self.population = custom_replacer.dea_replacer(random=self._random, population=self.population, parents=parents, offspring=offspring, maximize=self.maximize, args=self._kwargs)
            self.logger.debug('population size is now {0}'.format(len(self.population)))

            # Archive individuals.
            self.logger.debug('archival using {0} at generation {1} and evaluation {2}'.format(self.archiver.__name__, self.num_generations, self.num_evaluations))
            self.archive = self.archiver(random=self._random, archive=self.archive, population=list(self.population), args=self._kwargs)
            self.logger.debug('archive size is now {0}'.format(len(self.archive)))
            self.logger.debug('population size is now {0}'.format(len(self.population)))

            self.num_generations += 1
            if isinstance(self.observer, collections.Iterable):
                for obs in self.observer:
                    self.logger.debug('observation using {0} at generation {1} and evaluation {2}'.format(obs.__name__, self.num_generations, self.num_evaluations))
                    obs(population=list(self.population), num_generations=self.num_generations, num_evaluations=self.num_evaluations, args=self._kwargs)
            else:
                self.logger.debug('observation using {0} at generation {1} and evaluation {2}'.format(self.observer.__name__, self.num_generations, self.num_evaluations))
                self.observer(population=list(self.population), num_generations=self.num_generations, num_evaluations=self.num_evaluations, args=self._kwargs)
        return self.population

class DEA(EvolutionaryComputation):
    """Evolutionary computation representing a differential evolutionary algorithm.

    This class represents a differential evolutionary algorithm which uses, by
    default, tournament selection, heuristic crossover, Gaussian mutation,
    and steady-state replacement. It is expected that each candidate solution
    is a ``Sequence`` of real values.

    Optional keyword arguments in ``evolve`` args parameter:

    - *num_selected* -- the number of individuals to be selected (default 2)
    - *tournament_size* -- the tournament size (default 2)
    - *crossover_rate* -- the rate at which crossover is performed
      (default 1.0)
    - *mutation_rate* -- the rate at which mutation is performed (default 0.1)
    - *gaussian_mean* -- the mean used in the Gaussian function (default 0)
    - *gaussian_stdev* -- the standard deviation used in the Gaussian function
      (default 1)

    """
    def __init__(self, random):
        EvolutionaryComputation.__init__(self, random)
        self.selector = selectors.tournament_selection
        self.variator = [variators.heuristic_crossover, variators.gaussian_mutation]
        self.replacer = replacers.steady_state_replacement
        self.strategy = None

    def evolve(self, generator, evaluator, pop_size=100, seeds=None, maximize=True, bounder=None, **args):
        args.setdefault('num_selected', 2)
        return EvolutionaryComputation.evolve(self, generator, evaluator, pop_size, seeds, maximize, bounder, **args)

