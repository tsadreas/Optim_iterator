Optim_iterator
==============

GA,DEA,PSO Python Optimization algorithm using multiprocessing

Modified souce code of the [inspyred](https://github.com/aarongarrett/inspyred) library.

None of the files was created by me but I modified them,for the needs of my Master Thesis, to enable:
- tracking of many responses except of the fitness
- solving DEA startegies: 
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

The DEA strategies were obtained from [PyGMO](http://esa.github.io/pygmo/index.html).

## Example

`python solve.py <folder name> <algorithm> <mutation rate> <crossover rate>`

where:
* *folder name* : defines where to store the output files
* *algorithm* : DEA, GA or PSO
* *mutation rate* : if DEA or GA is used
* *crossover rate* : if DEA or GA is used


The function implemented is the Styblinski–Tang optimization test function. Any other function can be used if implemented in the same way.
The optimization function can be mathemetical or the result of another script.

## Requirements

- Python 2.7+
- inspyred
- pyDOE to create initial population using Latin Hypercube

## Licence

This package is distributed under the GNU General Public License version 3.0 (GPLv3).


