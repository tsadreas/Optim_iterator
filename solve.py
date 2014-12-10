'''
    ===============================================
    Main function that executes optimization procedure
    ===============================================

    author: Andreas Tsichritzis <tsadreas@gmail.com>
'''

from random import Random
from time import time
import inspyred
import os
import sys
import shutil
import datetime
import math
import numpy as np
import plot_results
import misc
import logging
import pyDOE
import GA_ec
import DEA_ec
import custom_swarm
import custom_evaluators
import custom_observers
import custom_terminators
import custom_mutators
import custom_benchmarks

path = os.getcwd()
# get folder name from input
case = str(sys.argv[1])
# get algorithm from input
algorithm = str(sys.argv[2])

if algorithm != 'PSO':
    # get mutation rate from input
    F = str(sys.argv[3])
    # get crossover rate from input
    CR = str(sys.argv[4])


def evaluator(x, args):
    '''Evaluator function, returns fitness and responses values'''
    # give the normalized candidates values inside the real design space
    x = [10*i-5 for i in x[0]]
    # calculate fitness
    f = sum([np.power(i,4)-16*np.power(i,2)+5*i for i in x])/2
    # calculate values for other responses
    res = {'r1':f-5,'r2':2*f}
    fitness = dict(Obj=f,**res)
    return fitness



def main(prng=None, display=False):

    if prng is None:
        prng = Random()
        prng.seed(time())

    ############### create file structure
    if os.path.exists(path + '/' + case):
        shutil.rmtree(path + '/' + case)

    os.makedirs(path + '/' + case)

    ############### logging
    logfile = case + '/inspyred.log'
    logger = logging.getLogger('inspyred.ec')
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(logfile, mode='w')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    ############### confirm start of run and delete old files
    os.chdir(path + '/' + case)
    home = os.getcwd()
    if os.listdir(path) != []:
        tmp_dir = os.listdir(home)
        for d in tmp_dir:
            shutil.rmtree(d,True)

    ############### start time count
    start_time = time()

    ############### specify problem (dimentions #,  maximize True or Flase)
    ############### and population (# of candidates at each generation)
    parameters = ['x1', 'x2', 'x3', 'x4']
    responses = ['r1','r2']
    problem = custom_benchmarks.StyblinskiTang(len(parameters), maximize=False)
    population = 12

    ############### set observer files and open them
    projdir = os.getcwd()
    stat_file_name = '{0}/statistics.csv'.format(projdir)
    ind_file_name = '{0}/individuals.csv'.format(projdir)
    stat_file = open(stat_file_name, 'w')
    ind_file = open(ind_file_name, 'w')


    ############### build initial population using DOE (Latin Hypercube)
    initial_population = pyDOE.lhs(len(parameters), samples = population, criterion = 'center')

    ############### specify algorithm
    if algorithm == 'DEA':
        """ Differential Evolutionary Algorithm

            * can be used with different mutators/crossovers/selectors/replacers,
              or with one of the following strategies:
                  * DE/best/1/exp
                  * DE/rand/1/exp
                  * DE/rand-to-best/1/exp
                  * DE/best/2/exp
                  * DE/rand/2/exp
                  * DE/best/1/bin
                  * DE/rand/1/bin
                  * DE/rand-to-best/1/bin
                  * DE/best/2/bin
                  * DE/rand/2/bin

            * Dont set both strategy and specific mutators/crossovers/selectors/replacers!!!
            * Strategies to be used with populations > 6!!!
            * If one of the strategies is used: ea = DEA_ec.DEA(prng)
            * If other mutators/crossovers/selectors/replacers: ea = GA_ec.DEA(prng)

        """
        ea = DEA_ec.DEA(prng)

        ea.terminator = inspyred.ec.terminators.evaluation_termination
        ea.observer = custom_observers.file_observer
        ea.strategy = 'DE/best/2/exp'


        ############### solve
        final_pop = ea.evolve(generator = problem.generator,
                              evaluator = custom_evaluators.parallel_evaluation_mp,
                              mp_evaluator = evaluator,
                              mp_nprocs = 2,
                              pop_size = population,
                              bounder = problem.bounder,
                              maximize = problem.maximize,
                              crossover_rate = CR,
                              mutation_rate = F,
                              gaussian_mean = 0,
                              gaussian_stdev = 1,
                              max_evaluations = 100,
                              statistics_file = stat_file,
                              statistics_file_name = stat_file_name,
                              individuals_file = ind_file,
                              par = parameters,
                              res = responses,
                              tol = 0.5,
                              c_maximize = problem.maximize,
                              initial_pop = initial_population)

    elif algorithm == 'GA':
        """ Genetic Algorithm """
        ea = GA_ec.GA(prng)

        ea.terminator = inspyred.ec.terminators.evaluation_termination
        ea.observer = custom_observers.file_observer
        ea.selection = inspyred.ec.selectors.rank_selection
        ea.variator = [inspyred.ec.variators.n_point_crossover,
                       inspyred.ec.variators.gaussian_mutation]

        ############### solve
        final_pop = ea.evolve(generator = problem.generator,
                              evaluator = custom_evaluators.parallel_evaluation_mp,
                              mp_evaluator = evaluator,
                              mp_nprocs = 2,
                              pop_size = population,
                              bounder = problem.bounder,
                              maximize = problem.maximize,
                              crossover_rate = CR,
                              mutation_rate = F,
                              max_evaluations = 100,
                              statistics_file = stat_file,
                              statistics_file_name = stat_file_name,
                              individuals_file = ind_file,
                              par = parameters,
                              res = responses,
                              tol = 0.5,
                              c_maximize = problem.maximize,
                              initial_pop = initial_population)

    elif algorithm == 'PSO':
        """ Particle Swarm Optimization """
        ea = custom_swarm.PSO(prng)
        ea.terminator = inspyred.ec.terminators.evaluation_termination
        ea.observer = custom_observers.file_observer
        ea.topology = inspyred.swarm.topologies.star_topology
        final_pop = ea.evolve(generator = problem.generator,
                                evaluator = custom_evaluators.parallel_evaluation_mp,
                                mp_evaluator = evaluator,
                                mp_nprocs = 2,
                                pop_size = population,
                                bounder = problem.bounder,
                                maximize = problem.maximize,
                                max_evaluations = 240,
                                inetria = 0.5,
                                cognitive_rate = 2.1,
                                social_rate = 2.1,
                                statistics_file = stat_file,
                                statistics_file_name = stat_file_name,
                                individuals_file = ind_file,
                                par = parameters,
                                res = responses,
                                tol = 0.05,
                                c_maximize = problem.maximize,
                                initial_pop = initial_population)



    ############### close observer files
    stat_file.close()
    ind_file.close()

    ############### count execution time
    total_time_s = time() - start_time
    total_time = datetime.timedelta(seconds=total_time_s)
    total_time = misc.formatTD(total_time)

    ################ find best solution
    x = misc.find_best(ind_file_name,population)

    ################ plot Fitness Stats during generations
    plot_results.generation_plot(stat_file_name,case)

    ################# create new files that replace normalized parameters with real values
    custom_benchmarks.correct_par(ind_file_name,parameters)

    ################# print report
    os.chdir(projdir)
    misc.report(x,parameters,total_time)

if __name__ == '__main__':
    main(display=True)