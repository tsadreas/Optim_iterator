'''
    ===============================================
       Changed version of inspyred.ec.evaluators
    ===============================================
    -- Multiple responses tracking feature added in parallel evaluator

    modified by: Andreas Tsichritzis <tsadreas@gmail.com>
'''

import functools
try:
    import cPickle as pickle
except ImportError:
    import pickle


def parallel_evaluation_mp(candidates, args):
    """Evaluate the candidates in parallel using ``multiprocessing``.

    This function allows parallel evaluation of candidate solutions.
    It uses the standard multiprocessing library to accomplish the
    parallelization. The function assigns the evaluation of each
    candidate to its own job, all of which are then distributed to the
    available processing units.

    .. note::

       All arguments to the evaluation function must be pickleable.
       Those that are not will not be sent through the ``args`` variable
       and will be unavailable to your function.

    .. Arguments:
       candidates -- the candidate solutions
       args -- a dictionary of keyword arguments

    Required keyword arguments in args:

    - *mp_evaluator* -- actual evaluation function to be used (This function
      should have the same signature as any other inspyred evaluation function.)

    Optional keyword arguments in args:

    - *mp_nprocs* -- number of processors that will be used (default machine
      cpu count)

    """
    import time
    import multiprocessing
    logger = args['_ec'].logger

    try:
        evaluator = args['mp_evaluator']
    except KeyError:
        logger.error('parallel_evaluation_mp requires \'mp_evaluator\' be defined in the keyword arguments list')
        raise
    try:
        nprocs = args['mp_nprocs']
    except KeyError:
        nprocs = multiprocessing.cpu_count()

    pickled_args = {}
    for key in args:
        try:
            pickle.dumps(args[key])
            pickled_args[key] = args[key]
        except (TypeError, pickle.PickleError, pickle.PicklingError):
            logger.debug('unable to pickle args parameter {0} in parallel_evaluation_mp'.format(key))
            pass

    start = time.time()
    try:
        pool = multiprocessing.Pool(processes=nprocs)
        results = [pool.apply_async(evaluator, ([c], pickled_args)) for c in candidates]
        pool.close()
        pool.join()
        f = [r.get()['Obj'] for r in results]
        for r in results:
            del r.get()['Obj']
        return (f, [r.get() for r in results])
    except (OSError, RuntimeError) as e:
        logger.error('failed parallel_evaluation_mp: {0}'.format(str(e)))
        raise
    else:
        end = time.time()
        logger.debug('completed parallel_evaluation_mp in {0} seconds'.format(end - start))

