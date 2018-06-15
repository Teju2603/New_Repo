
## ALMAtasks

This repository contains the ALMA tasks which are used with [CASAtools](https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtools/browse) and [CASAtasks](https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtasks/browse).

These tasks are specific to the [ALMA Observatory](http://www.almaobservatory.org/en/home/).

#### Build

After all of the dependencies have been installed and the source code for ALMAtasks is available we can build ALMAtasks. Make sure that =which python= returns the version of python that was used to build [CASAtools](https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtools/browse). Then build the tasks with:
```
-bash-4.2$ cd ALMAtasks
-bash-4.2$ PYTHONPATH=../CASAtools/build/lib.macosx-10.12-x86_64-3.6 ./setup.py build
```
**Substitute** the path to your build of [CASAtools](https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtools/browse) in the build line above.

