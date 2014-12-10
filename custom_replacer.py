'''
    ===============================================
            Based on inspyred.ec.replacers
    ===============================================
    -- replacer to be used with DEA when using one of the strategies

    original author: Aaron Garrett <aaron.lee.garrett@gmail.com>

    modified by: Andreas Tsichritzis <tsadreas@gmail.com>
'''

def dea_replacer(random, population, parents, offspring, maximize, args):
    """Replaces population with the best of the population and offspring.
    
    .. Arguments:
       random -- the random number generator object
       population -- the population of individuals
       parents -- the list of parent individuals
       offspring -- the list of offspring individuals
       maximize -- bootlean if objective is macimization or not
       args -- a dictionary of keyword arguments
    
    """
    psize = len(population)
    for i in range(psize):
        if maximize:
            if abs(parents[i].fitness) > abs(offspring[i].fitness):
                offspring[i] = parents[i]
        else:
            if abs(parents[i].fitness) < abs(offspring[i].fitness):
                offspring[i] = parents[i] 
    population = offspring
    return population
