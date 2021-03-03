
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

#### Run

While only the [CASAtools](https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtools/browse) python module is require for building ALMAtasks, both the [CASAtools](https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtools/browse) **and** [CASAtasks](https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtasks/browse) modules are required for use of the ALMAtasks at runtime. For example, the _wvrgcal_ test can be run like:
```
-bash-4.2$ cd ALMAtasks
-bash-4.2$ mkdir testing
-bash-4.2$ cd testing
-bash-4.2$ PYTHONPATH=../build/lib.macosx-10.12-x86_64-3.6:../../CASAtools/build/lib.macosx-10.12-x86_64-3.6:../../CASAtasks/build/lib.macosx-10.12-x86_64-3.6 python ../tests/tasks/test_wvrgcal.py
```
**Substitute** the path to your build of [CASAtools](https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtools/browse), [CASAtasks](https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtasks/browse), and [ALMAtasks](https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtools/browse) in the line above. It is also important to use the same version of python at runtime as was used at build-time.
