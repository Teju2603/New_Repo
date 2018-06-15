#!/usr/bin/env python
# Copyright (C) 2018
# Associated Universities, Inc. Washington DC, USA.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Library General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Library General Public
# License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 675 Massachusetts Ave, Cambridge, MA 02139, USA.
#
# Correspondence concerning AIPS++ should be addressed as follows:
#        Internet email: aips2-request@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA


"""ALMAtasks Python Module

This is python module that provides provides a set of ALMA specific tasks
for use with CASAtasks and CASAtools.
"""
from __future__ import division, print_function

classifiers = """\
Development Status :: 3 - Alpha
Intended Audience :: Developers
License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)
Programming Language :: Python :: 2.7
Programming Language :: C++
Topic :: Software Development
Topic :: Scientific/Engineering :: Astronomy
Topic :: Software Development :: Libraries :: Python Modules
Operating System :: MacOS :: MacOS X
Operating System :: POSIX
"""
import sysconfig
import errno
import sys
import os

try:
    from CASAtools.config import build as props
except:
    print("cannot find CASAtools (https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtools/browse) in PYTHONPATH")
    os._exit(1)

from distutils.ccompiler import new_compiler, CCompiler
from distutils.sysconfig import customize_compiler
from distutils.core import setup, Extension
from distutils.ccompiler import get_default_compiler
from distutils.ccompiler import show_compilers
from distutils.command.build_ext import build_ext
from distutils.errors import DistutilsExecError, CompileError
from distutils.dir_util import copy_tree, remove_tree
from distutils.core import Command
from distutils.util import spawn

module_name = 'ALMAtasks'

platform_cflags = { 'darwin': [ ],
                    'linux2': [ '-fcx-fortran-rules' ],
                    'linux': [ '-fcx-fortran-rules' ],
#####
#####  these cause a segmentation violation in test_setjy
#####
#                    'linux2': [ '-fopenmp', '-fcx-fortran-rules' ],
#                    'linux': [ '-fopenmp', '-fcx-fortran-rules' ],
};

module_cflags = { '/casacore/': ['-DCFITSIO_VERSION_MAJOR=3', '-DCFITSIO_VERSION_MINOR=370', '-DCASA_BUILD=1'\
                                 '-DHAVE_FFTW3', '-DHAVE_FFTW3_THREADS', '-DHAVE_READLINE', \
                                 '-DUSE_THREADS', '-DUseCasacoreNamespace', '-DWCSLIB_VERSION_MAJOR=5', \
                                 '-DWCSLIB_VERSION_MINOR=15', '-fsigned-char', '-DWITHOUT_BOOST',
                                 '-DCASATOOLS' ] + platform_cflags[sys.platform],
                       '/code/':     ['-DAIPS_64B', '-DAIPS_AUTO_STL', '-DAIPS_DEBUG', \
                                      '-DAIPS_HAS_QWT', '-DAIPS_LINUX', '-DAIPS_LITTLE_ENDIAN', \
                                      '-DAIPS_STDLIB', '-DCASACORE_NEEDS_RETHROW', '-DCASA_USECASAPATH', \
                                      '-DDBUS_CPP', '-DQWT6', '-DUseCasacoreNamespace', \
                                      '-D_FILE_OFFSET_BITS=64', '-D_LARGEFILE_SOURCE', '-DNO_CRASH_REPORTER', \
                                      '-fno-omit-frame-pointer', '-DWITHOUT_ACS', '-DWITHOUT_BOOST',
                                      '-DCASATOOLS' ] + platform_cflags[sys.platform],
                       'binding/':     ['-DAIPS_64B', '-DAIPS_AUTO_STL', '-DAIPS_DEBUG', '-DAIPS_HAS_QWT', \
                                        '-DAIPS_LINUX', '-DAIPS_LITTLE_ENDIAN', '-DAIPS_STDLIB', \
                                        '-DCASACORE_NEEDS_RETHROW', '-DCASA_USECASAPATH', '-DDBUS_CPP', '-DQWT6', \
                                        '-DUseCasacoreNamespace', '-D_FILE_OFFSET_BITS=64', '-D_LARGEFILE_SOURCE', \
                                        '-DNO_CRASH_REPORTER', '-fno-omit-frame-pointer', '-DWITHOUT_ACS', '-DWITHOUT_BOOST',
                                        '-DCASATOOLS' ] + platform_cflags[sys.platform] }

def clean_args(l):
    return [a for a in l if len(a) > 0]

def mkpath(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

## https://stackoverflow.com/questions/14320220/testing-python-c-libraries-get-build-path
def distutils_dir_name(dname):
    """Returns the name of a distutils build directory"""
    f = "{dirname}.{platform}-{version[0]}.{version[1]}"
    return f.format(dirname=dname,platform=sysconfig.get_platform(),version=sys.version_info)

def customize_compiler(self, verbose=False):
    """inject customization into distutils.

    Getting distutils to use a specfic compiler with a fully-quaified
    path and specfic flags is difficult. By default, it seems to just
    use 'gcc', i.e. whichever compiler happens to be in the user's
    path. I want to select a specific compiler using autoconf.

    I found this reference useful:
    https://github.com/rmcgibbo/npcuda-example/blob/master/cython/setup.py
    """

    # make it swallow fortran files....
    self.src_extensions.extend( [".f",".f90"] )

    # save references to the default compiler_so and _comple methods
    default_compiler_so = self.compiler_so
    default_linker_so = self.linker_so
    default_linker_exe = self.linker_exe
    supercc = self._compile
    superld = self.link
    ccache = [ props['build.compiler.ccache'] ] if 'build.compiler.ccache' in props and len(props['build.compiler.ccache']) > 0 else [ ]
    cflags = map(lambda pair: pair[1],filter(lambda pair: pair[0].startswith('build.flags.compile'),props.items()))
    cflags = [item for sublist in cflags for item in sublist]         ### python has not yet hit upon a flatten function...
    ldflags = map(lambda pair: pair[1],filter(lambda pair: pair[0].startswith('build.flags.link'),props.items()))
    ldflags = [item for sublist in cflags for item in sublist]         ### python has not yet hit upon a flatten function...
    if 'build.python.numpy_dir' in props and len(props['build.python.numpy_dir']) > 0:
        cflags.insert(0,'-I' + props['build.python.numpy_dir'])       ### OS could have different version of python in
                                                                      ###     /usr/include (e.g. rhel6)
    new_compiler_cxx = ccache + [props['build.compiler.cxx'], '-g', '-std=c++11','-Ibinding/include','-Ibinding/generated/include','-Ilibcasatools/generated/include','-Icasa-source/code','-Icasa-source','-Icasa-source/casacore', '-Iinclude', '-Isakura-source/src'] + cflags + default_compiler_so[1:]
    new_compiler_cc = ccache + [props['build.compiler.cc'], '-g', '-Ibinding/include','-Ibinding/generated/include','-Ilibcasatools/generated/include','-Icasa-source/code','-Icasa-source','-Icasa-source/casacore', '-Iinclude', 'sakura-source/src'] + cflags + default_compiler_so[1:]
    new_compiler_fortran = [props['build.compiler.fortran']]

    new_compiler_cxx = list(filter(lambda flag: not flag.startswith('-O'),new_compiler_cxx))
    new_compiler_ccc = list(filter(lambda flag: not flag.startswith('-O'),new_compiler_cc))

    new_linker_cxx = [ props['build.compiler.cxx'] ]

    local_path_file = ".lib-path.%d" % sys.hexversion
    local_mangle_file = ".lib-mangle.%d" % sys.hexversion

    if os.path.isfile(local_path_file):
        with open(local_path_file,'rb') as f:
            local_library_path = pickle.load(f)
    else:
        local_library_path = [ ]

    if os.path.isfile(local_mangle_file):
        with open(local_mangle_file,'rb') as f:
            library_mangle = pickle.load(f)
    else:
        library_mangle = { }

    def _link(target_desc, objects, output_filename, output_dir=None,
              libraries=None, library_dirs=None, runtime_library_dirs=None,
              export_symbols=None, debug=0, extra_preargs=None,
              extra_postargs=None, build_temp=None, target_lang=None):

        if target_desc == CCompiler.EXECUTABLE:
            self.set_executable('linker_exe', new_linker_cxx)
        else:
            fn = os.path.basename(output_filename)
            if fn.startswith('lib') and fn.endswith(".so"):
                print("linking shared library...")
                self.linker_so = list(map(lambda f: "-dynamiclib" if f == "-bundle" else f,self.linker_so))
                if sys.platform == 'darwin':
                    if output_filename.endswith(".so"):
                        output_filename = output_filename[:-3] + ".dylib"
                    subname = os.path.basename(output_filename)
                    extra_postargs=list(map( lambda arg: arg % subname if '%s' in arg else arg, extra_postargs ))
                dir = os.path.dirname(output_filename)
                target_desc=CCompiler.SHARED_LIBRARY
                if dir not in local_library_path:
                    local_library_path.insert(0,dir)
                    with open(local_path_file,'wb') as f:
                        pickle.dump(local_library_path,f)

                bfn = (fn[3:])[:-3]
                library_mangle[bfn.split('.')[0]] = bfn
                with open(local_mangle_file,'wb') as f:
                    pickle.dump(library_mangle,f)

        if verbose:
            print("linking %s" % output_filename)
        superld( target_desc, objects, output_filename, output_dir,
                 None if libraries is None else [library_mangle[l] if l in library_mangle else l for l in libraries],
                 None if library_dirs is None else library_dirs+local_library_path, runtime_library_dirs, export_symbols,
                 debug, extra_preargs, extra_postargs, build_temp, target_lang )

        self.compiler_so = default_compiler_so
        self.linker_so = default_linker_so
        self.linker_exe = default_linker_exe

    # now redefine the _compile method. This gets executed for each
    # object but distutils doesn't have the ability to change compilers
    # based on source extension: we add it.
    def _compile(obj, src, ext, cc_args, postargs, pp_opts):
        if ext == ".f" or ext == ".f90" :
            print("fortran compile...")
            arch = platform.architecture()[0].lower()
            if sys.platform == 'darwin' or sys.platform.startswith('linux'):
                compiler_so = new_compiler_fortran
                if (ext == ".f90"):
                    cc_args = ["-O3", "-fPIC", "-c", "-ffree-form", "-ffree-line-length-none"]
                if (ext == ".f"):
                    cc_args = ["-O3", "-fPIC", "-c", "-fno-automatic", "-ffixed-line-length-none"]
                # Force architecture of shared library.
                if arch == "32bit":
                    cc_args.append("-m32")
                elif arch == "64bit":
                    cc_args.append("-m64")
                else:
                    print("\nPlatform has architecture '%s' which is unknown to "
                          "the setup script. Proceed with caution\n" % arch)

            try:
                self.spawn(compiler_so + cc_args + [src, '-o', obj] + postargs)
            except DistutilsExecError as msg:
                raise CompileError(msg)
        else:
            if ext == ".c" :
                print("c compile...")
                new_compiler = new_compiler_cc
            else:
                print("c++ compile...")
                new_compiler = new_compiler_cxx
            ## get the cflags for the module being built; key is a subdir, value are flags
            m_cflags = map(lambda x: x[1] if x[0] in src else [], module_cflags.items())
            m_cflags = [item for sublist in m_cflags for item in sublist] ### python has not yet hit upon a flatten function...
            self.set_executable('compiler_so', clean_args(new_compiler + m_cflags + ( [ '-DUSE_GRPC' ] if props['option.grpc'] != "0" else [ ] )))
            if verbose:
                print("compiling %s" % src)
            supercc(obj, src, ext, clean_args(cc_args), clean_args(postargs), clean_args(pp_opts))

        # reset the default compiler_so (may not be necessary)
        self.compiler_so = default_compiler_so

    # inject our redefined _compile method into the class
    self._compile = _compile
    self.link = _link


# run the customize_compiler
class casa_build_ext(build_ext):
    def build_extensions(self):
        customize_compiler(self.compiler)
        build_ext.build_extensions(self)

ext = [ Extension( module_name + ".__private__.bin.wvrgcal_exe", language='c++', sources=["helloworld.cc"], include_dirs=['binding'], extra_link_args=[ ], libraries=['m']) ]

if __name__ == '__main__':
    tmpdir = os.path.join('build', distutils_dir_name('temp'))
    moduledir = os.path.join('build', distutils_dir_name('lib'), module_name)
    bindir = os.path.join(moduledir, '__private__', "bin")
    libdir = os.path.join(moduledir, "lib")
    mkpath(bindir)
    mkpath(libdir)
    cc = new_compiler("posix", verbose=False)
    customize_compiler(cc,True)
    objs = cc.compile( ["helloworld.cc"], os.path.join(tmpdir,"wvrgcal") )
    cc.link( CCompiler.EXECUTABLE, objs, os.path.join(bindir,"wvrgcal") )
    
#    setup( name="ALMAtasks",version="1.0.1",
#           maintainer="Darrell Schiebel",
#           maintainer_email="drs@nrao.edu",
#           author="CASA development team",
#           author_email="aips2-request@nrao.edu",
#           url="http://casa.nrao.edu",
#           download_url="https://casa.nrao.edu/download/",
#           license="GNU Library or Lesser General Public License (LGPL)",
#           platforms=["MacOS X"],
#           description = __doc__.split("\n")[0],
#           long_description="\n".join(__doc__.split("\n")[2:]),
#           classifiers=filter(None, classifiers.split("\n")),
#           package_dir={'ALMAtasks': libdir},
#           packages=['ALMAtasks'],
#           cmdclass={ 'build_ext': casa_build_ext },
#           ext_modules=ext)
