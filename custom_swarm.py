"""
    ===============================================
    Changed and combined inspyred.ec, inspyred.swarm
    ===============================================
    
    -- Added reponses tracking

    original author: Aaron Garrett <aaron.lee.garrett@gmail.com>

    modified by: Andreas Tsichritzis <tsadreas@gmail.com>
"""

import collections
import copy
import functools
import inspyred
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
        return '{0} : {1} {2}'.format(self.candidate, self.fitness, self.responses)
        
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
        
        This function creates a population and then runs it through a series
        of evolutionary epochs until the terminator is satisfied. The general
        outline of an epoch is selection, variation, evaluation, replacement,
        migration, archival, and observation. The function returns a list of
        elements of type ``Individual`` representing the individuals contained
        in the final population.
        
        Arguments:
        
        - *generator* -- the function to be used to generate candidate solutions 
        - *evaluator* -- the function to be used to evaluate candidate solutions
        - *pop_size* -- the number of Individuals in the population (default 100)
        - *seeds* -- an iterable collection of candidate solutions to include
          in the initial population (default None)
        - *maximize* -- Boolean value stating use of maximization (default True)
        - *bounder* -- a function used to bound candidate solutions (default None)
        - *args* -- a dictionary of keyword arguments

        The *bounder* parameter, if left as ``None``, will be initialized to a
        default ``Bounder`` object that performs no bounding on candidates.
        Note that the *_kwargs* class variable will be initialized to the *args* 
        parameter here. It will also be modified to include the following 'built-in' 
        keyword argument:
        
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
        
        while not self._should_terminate(list(self.population), self.num_generations, self.num_evaluations):
            # Select individuals.
            self.logger.debug('selection using {0} at generation {1} and evaluation {2}'.format(self.selector.__name__, self.num_generations, self.num_evaluations))
            parents = self.selector(random=self._random, population=list(self.population), args=self._kwargs)
            self.logger.debug('selected {0} candidates'.format(len(parents)))
            parent_cs = [copy.deepcopy(i.candidate) for i in parents]
            offspring_cs = parent_cs
            
            if isinstance(self.variator, collections.Iterable):
                for op in self.variator:
                    self.logger.debug('variation using {0} at generation {1} and evaluation {2}'.format(op.__name__, self.num_generations, self.num_evaluations))
                    offspring_cs = op(random=self._random, candidates=offspring_cs, args=self._kwargs)
            else:
                self.logger.debug('variation using {0} at generation {1} and evaluation {2}'.format(self.variator.__name__, self.num_generations, self.num_evaluations))
                offspring_cs = self.variator(random=self._random, candidates=offspring_cs, args=self._kwargs)
            self.logger.debug('created {0} offspring'.format(len(offspring_cs)))
            
            # Evaluate offspring.
            self.logger.debug('evaluation using {0} at generation {1} and evaluation {2}'.format(evaluator.__name__, self.num_generations, self.num_evaluations))
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

            # Replace individuals.
            self.logger.debug('replacement using {0} at generation {1} and evaluation {2}'.format(self.replacer.__name__, self.num_generations, self.num_evaluations))
            self.population = self.replacer(random=self._random, population=self.population, parents=parents, offspring=offspring, args=self._kwargs)
            self.logger.debug('population size is now {0}'.format(len(self.population)))
            
            # Migrate individuals.
            self.logger.debug('migration using {0} at generation {1} and evaluation {2}'.format(self.migrator.__name__, self.num_generations, self.num_evaluations))
            self.population = self.migrator(random=self._random, population=self.population, args=self._kwargs)
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


class PSO(EvolutionaryComputation):
    """Represents a basic particle swarm optimization algorithm.
    
    This class is built upon the ``EvolutionaryComputation`` class making
    use of an external archive and maintaining the population at the previous
    timestep, rather than a velocity. This approach was outlined in 
    (Deb and Padhye, "Development of Efficient Particle Swarm Optimizers by
    Using Concepts from Evolutionary Algorithms", GECCO 2010, pp. 55--62).
    This class assumes that each candidate solution is a ``Sequence`` of
    real values.
    
    Public Attributes:
    
    - *topology* -- the neighborhood topology (default topologies.star_topology)
    
    Optional keyword arguments in ``evolve`` args parameter:
    
    - *inertia* -- the inertia constant to be used in the particle 
      updating (default 0.5)
    - *cognitive_rate* -- the rate at which the particle's current 
      position influences its movement (default 2.1)
    - *social_rate* -- the rate at which the particle's neighbors 
      influence its movement (default 2.1)
    
    """
    def __init__(self, random):
        EvolutionaryComputation.__init__(self, random)
        self.topology = inspyred.swarm.topologies.star_topology
        self._previous_population = []
        self.selector = self._swarm_selector
        self.replacer = self._swarm_replacer
        self.variator = self._swarm_variator
        self.archiver = self._swarm_archiver
        
    def _swarm_archiver(self, random, population, archive, args):
        if len(archive) == 0:
            return population[:]
        else:
            new_archive = []
            for i, (p, a) in enumerate(zip(population[:], archive[:])):
                if p < a:
                    new_archive.append(a)
                else:
                    new_archive.append(p)
            return new_archive
        
    def _swarm_variator(self, random, candidates, args):
        inertia = args.setdefault('inertia', 0.5)
        cognitive_rate = args.setdefault('cognitive_rate', 2.1)
        social_rate = args.setdefault('social_rate', 2.1)
        if len(self.archive) == 0:
            self.archive = self.population[:]
        if len(self._previous_population) == 0:
            self._previous_population = self.population[:]
        neighbors = self.topology(self._random, self.archive, args)
        offspring = []
        for x, xprev, pbest, hood in zip(self.population, 
                                         self._previous_population, 
                                         self.archive, 
                                         neighbors):
            nbest = max(hood)
            particle = []
            for xi, xpi, pbi, nbi in zip(x.candidate, xprev.candidate, 
                                         pbest.candidate, nbest.candidate):
                value = (xi + inertia * (xi - xpi) + 
                         cognitive_rate * random.random() * (pbi - xi) + 
                         social_rate * random.random() * (nbi - xi))
                particle.append(value)
            particle = self.bounder(particle, args)
            offspring.append(particle)
        return offspring
        
    def _swarm_selector(self, random, population, args):
        return population
        
    def _swarm_replacer(self, random, population, parents, offspring, args):
        self._previous_population = population[:]
        return offspring