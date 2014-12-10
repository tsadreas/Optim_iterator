'''
    ===============================================
    Uniform Mutator based on inspyred.ec.variators
    ===============================================
    
    author: Andreas Tsichritzis <tsadreas@gmail.com>
'''

import copy
import functools
    
    
def mutator(mutate):
    """Return an inspyred mutator function based on the given function.
    
    This function generator takes a function that operates on only
    one candidate to produce a single mutated candidate. The generator 
    handles the iteration over each candidate in the set to be mutated.

    The given function ``mutate`` must have the following signature::
    
        mutant = mutate(random, candidate, args)
        
    This function is most commonly used as a function decorator with
    the following usage::
    
        @mutator
        def mutate(random, candidate, args):
            # Implementation of mutation
            pass
            
    The generated function also contains an attribute named
    ``single_mutation`` which holds the original mutation function.
    In this way, the original single-candidate function can be
    retrieved if necessary.
    
    """
    @functools.wraps(mutate)
    def ecspy_mutator(random, candidates, args):
        mutants = []
        for i, cs in enumerate(candidates):
            mutants.append(mutate(random, cs, args))
        return mutants
    ecspy_mutator.single_mutation = mutate
    return ecspy_mutator
    
@mutator
def uniform_mutation(random, candidate, args):
    """Mutate an individual by replacing attributes by a number uniformly
    drawn between *low* and *up* inclusively.
    .. Arguments:
       random -- the random number generator object
       candidate -- the candidate solution
       args -- a dictionary of keyword arguments
    Optional keyword arguments in args:
    - **mutation_rate* -- the rate at which mutation is performed (default 0.1)
    """
    bounder = args['_ec'].bounder
    num_gens = args['_ec'].num_generations
    mut_rate = args.setdefault('mutation_rate', 0.1)
    mutant = copy.copy(candidate)
    for i, (c, lo, hi) in enumerate(zip(candidate, bounder.lower_bound, bounder.upper_bound)):
        if random.random() <= mut_rate:
            new_value = random.uniform(lo,hi)
            mutant[i] = new_value
    return mutant
 
