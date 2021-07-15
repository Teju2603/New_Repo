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
Programming Language :: Python :: 3
Programming Language :: C++
Topic :: Software Development
Topic :: Scientific/Engineering :: Astronomy
Topic :: Software Development :: Libraries :: Python Modules
Operating System :: MacOS :: MacOS X
Operating System :: POSIX
"""
import subprocess
from subprocess import call as Proc
from subprocess import Popen, PIPE
from shutil import copy2
import fileinput
import sysconfig
import errno
import sys
import os
import re
import argparse

parser=argparse.ArgumentParser()
parser.add_argument('--version', help='version')
parser.add_argument('bdist_wheel', help='bdist_wheel')
args=parser.parse_args()

print (args.version)

pyversion = float(sys.version_info[0]) + float(sys.version_info[1]) / 10.0

try:
    from casatools.config import build as props
    from casatools.config import build as tools_config
    openmp_flags = [] if len(props['build.flags.link.openmp']) == 0 else []
except:
    print("cannot find CASAtools (https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtools/browse) in PYTHONPATH")
    os._exit(1)

from setuptools import setup, find_packages
from distutils.ccompiler import new_compiler, CCompiler
from distutils.sysconfig import customize_compiler
from distutils.core import Extension
from distutils.ccompiler import get_default_compiler
from distutils.ccompiler import show_compilers
from distutils.command.build_ext import build_ext
from distutils.errors import DistutilsExecError, CompileError
from distutils.dir_util import copy_tree, remove_tree
from distutils.core import Command
from distutils.util import spawn
from setuptools.dist import Distribution


from wheel.bdist_wheel import bdist_wheel


module_name = 'almatasks'

if pyversion < 3:
    str_encode = str
    str_decode = str
    def pipe_decode(output):
        return output
else:
    def str_encode(s):
        return bytes(s,sys.getdefaultencoding())
    def str_decode(bs):
        return bs.decode(sys.getdefaultencoding(),"strict")
    def pipe_decode(output):
        if isinstance(output,bytes) or isinstance(output,bytearray):
            return str_decode(output)
        elif isinstance(output,tuple):
            return (str_decode(output[0]),str_decode(output[1]))
        else:
            return ("","")

def compute_version( ):
    if (args.version != None ):
        print (args.version.split("."))
        (major, minor, patch) = args.version.split(".")
        return(int(major), int(minor), int(patch))
    else:
        proc = Popen( [ "./version" ], stdout=PIPE, stderr=PIPE )
        out,err = pipe_decode(proc.communicate( ))
        print(out)
        devbranchtag = out.split(" ")[0].strip()
        print(devbranchtag)
        releasetag = out.split(" ")[1].strip()
        dirty=""
        if (len(out.split(" ")) == 3):
            print("Latest commit doesn't have a tag. Adding -dirty flag to version string.")
            dirty="+" + out.split(" ")[2].strip() # "+" denotes local version identifier as described in PEP440
        print(releasetag)
        devbranchversion = ""
        devbranchrevision = ""
        if (devbranchtag != releasetag):
            if (devbranchtag.startswith("CAS-")):
                devbranchversion=devbranchtag.split("-")[1]
            else:
                devbranchversion=100
            devbranchrevision = devbranchtag.split("-")[-1]
        else:
            isDevBranch = False
        (major, minor, patch) = releasetag.split(".")
        return(int(major), int(minor), int(patch), devbranchversion, devbranchrevision, dirty)

(almatasks_major,almatasks_minor,almatasks_patch,devbranchversion,devbranchrevision,dirty) = compute_version( )
almatasks_version = '%d.%d.%d%s' % (almatasks_major,almatasks_minor,almatasks_patch,dirty)
if devbranchversion !="":
    almatasks_version = '%d.%d.%da%sdev%s%s' % (almatasks_major,almatasks_minor,almatasks_patch,devbranchversion,devbranchrevision,dirty)

class BdistWheel(bdist_wheel):

    user_options = bdist_wheel.user_options + [
        ('build=', None, 'specify build number') ]

    def initialize_options(self):
        bdist_wheel.initialize_options(self)
        self.build=almatasks_version

    def finalize_options(self):
        bdist_wheel.finalize_options(self)
        # Mark us as not a pure python package
        self.root_is_pure = False

    def get_tag(self):
        python, abi, plat = bdist_wheel.get_tag(self)
        return python, abi, plat

CASACORE_LEX=[ 'casa-source/casatools/casacore/tables/TaQL/RecordGram.ll',
               'casa-source/casatools/casacore/tables/TaQL/TableGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSSpwGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSTimeGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSStateGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSUvDistGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSFeedGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSScanGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSCorrGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSArrayGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSFieldGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSAntennaGram.ll',
               'casa-source/casatools/casacore/ms/MSSel/MSObservationGram.ll' ]
CASACORE_YACC=[ 'casa-source/casatools/casacore/tables/TaQL/RecordGram.yy',
                'casa-source/casatools/casacore/tables/TaQL/TableGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSSpwGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSTimeGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSStateGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSUvDistGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSFeedGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSScanGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSCorrGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSArrayGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSFieldGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSAntennaGram.yy',
                'casa-source/casatools/casacore/ms/MSSel/MSObservationGram.yy' ]

CASAWVR_SOURCE = [ 'src/code/air_casawvr/cmdline/wvrgcal.cpp', 'src/code/air_casawvr/cmdline/wvrgcalerrors.cpp',
                   'src/code/air_casawvr/cmdline/wvrgcalfeedback.cpp', 'src/code/air_casawvr/src/apps/arraygains.cpp',
                   'src/code/air_casawvr/src/apps/segmentation.cpp', 'src/code/air_casawvr/src/apps/arraydata.cpp',
                   'src/code/air_casawvr/casawvr/mswvrdata.cpp', 'src/code/air_casawvr/casawvr/msutils.cpp',
                   'src/code/air_casawvr/src/dipmodel_iface.cpp', 'src/code/air_casawvr/src/apps/almaresults.cpp',
                   'src/code/air_casawvr/src/apps/almaopts.cpp', 'src/code/air_casawvr/src/apps/almaabs_i.cpp',
                   'src/code/air_casawvr/src/model_iface.cpp', 'src/code/air_casawvr/src/measure_iface.cpp',
                   'src/code/air_casawvr/casawvr/msspec.cpp', 'src/code/air_casawvr/casawvr/msgaintable.cpp',
                   'src/code/air_casawvr/src/dispersion.cpp', 'src/code/air_casawvr/src/radiometermeasure.cpp',
                   'src/code/air_casawvr/src/radiometer_utils.cpp', 'src/code/air_casawvr/src/apps/dtdlcoeffs.cpp',
                   'src/code/air_casawvr/src/model_make.cpp', 'src/code/air_casawvr/src/cloudywater.cpp',
                   'src/code/air_casawvr/src/rtranfer.cpp', 'src/code/air_casawvr/src/columns.cpp',
                   'src/code/air_casawvr/src/lineparams.cpp', 'src/code/air_casawvr/src/models_basic.cpp',
                   'src/code/air_casawvr/src/singlelayerwater.cpp', 'src/code/air_casawvr/src/slice.cpp',
                   'src/code/air_casawvr/src/basicphys.cpp', 'src/code/air_casawvr/src/apps/antennautils.cpp',
                   'src/code/air_casawvr/src/dtdltools.cpp', 'src/code/air_casawvr/casawvr/msantdata.cpp',
                   'src/code/air_casawvr/src/layers.cpp', 'src/code/air_casawvr/src/columns_data.cpp',
                   'src/code/air_casawvr/src/partitionsum.cpp', 'src/code/air_casawvr/src/partitionsum_testdata.cpp',
                   'src/code/air_casawvr/src/libair_main.cpp',

                   'src/code/bnmin1/src/nestedsampler.cxx',
                   'src/code/bnmin1/src/nestederr.cxx', 'src/code/bnmin1/src/priors.cxx',
                   'src/code/bnmin1/src/minimmodel.cxx', 'src/code/bnmin1/src/bnmin_main.cxx',
                   'src/code/bnmin1/src/prior_sampler.cxx', 'src/code/bnmin1/src/mcpoint.cxx',
                   'src/code/bnmin1/src/markovchain.cxx', 'src/code/bnmin1/src/metro_propose.cxx',
                   'src/code/bnmin1/src/paramalgo.cxx', 'src/code/bnmin1/src/minim.cxx',
                   'src/code/bnmin1/src/nestedinitial.cxx',

                   'src/code/air_casawvr/src/apps/almaabs.cpp',

                   'casa-source/casatools/src/code/synthesis/CalTables/NewCalTable.cc', 'casa-source/casatools/src/code/synthesis/CalTables/CTMainRecord.cc',
                   'casa-source/casatools/src/code/synthesis/CalTables/CTMainColumns.cc', 'casa-source/casatools/src/code/synthesis/CalTables/RIorAParray.cc',
                   'casa-source/casatools/src/code/synthesis/CalTables/CalHistRecord.cc', 'casa-source/casatools/src/code/msvis/MSVis/MSCalEnums.cc',
                   'casa-source/casatools/src/code/synthesis/CalTables/CTDesc.cc', 'casa-source/casatools/src/code/synthesis/CalTables/CTEnums.cc',
                   'casa-source/casatools/src/code/synthesis/CalTables/CalTable.cc', 'casa-source/casatools/src/code/synthesis/CalTables/CalDescRecord.cc',
                   'casa-source/casatools/src/code/synthesis/CalTables/CalMainRecord.cc', 'casa-source/casatools/src/code/synthesis/CalTables/CTColumns.cc',

                   'casa-source/casatools/casacore/casa/Exceptions/Error2.cc', 'casa-source/casatools/casacore/casa/Arrays/ArrayError.cc',
                   'casa-source/casatools/casacore/casa/Containers/Block.cc', 'casa-source/casatools/casacore/tables/Tables/ColumnDesc.cc',
                   'casa-source/casatools/casacore/tables/Tables/BaseColumn.cc', 'casa-source/casatools/casacore/measures/Measures/MDirection.cc',
                   'casa-source/casatools/casacore/measures/Measures/MFrequency.cc', 'casa-source/casatools/casacore/ms/MSOper/MSMetaData.cc',
                   'casa-source/casatools/casacore/measures/Measures/MCPosition.cc', 'casa-source/casatools/casacore/casa/Quanta/MVPosition.cc',
                   'casa-source/casatools/casacore/tables/Tables/TableRow.cc', 'casa-source/casatools/casacore/tables/Tables/TableError.cc',
                   'casa-source/casatools/casacore/tables/Tables/TableProxy.cc', 'casa-source/casatools/casacore/tables/Tables/TableTrace.cc',
                   'casa-source/casatools/casacore/casa/BasicSL/String.cc', 'casa-source/casatools/casacore/tables/TaQL/TaQLResult.cc',
                   'casa-source/casatools/casacore/casa/System/AipsrcValue2.cc', 'casa-source/casatools/casacore/tables/Tables/ArrayColumn_tmpl.cc',
                   'casa-source/casatools/casacore/tables/DataMan/DataManager.cc', 'casa-source/casatools/casacore/casa/Quanta/MVDirection.cc',
                   'casa-source/casatools/casacore/tables/DataMan/DataManagerColumn.cc', 'casa-source/casatools/casacore/tables/DataMan/StManColumnBase.cc',
                   'casa-source/casatools/casacore/tables/Tables/PlainTable.cc', 'casa-source/casatools/casacore/tables/Tables/ColumnCache.cc',
                   'casa-source/casatools/casacore/tables/Tables/TableCache.cc', 'casa-source/casatools/casacore/casa/Quanta/MVFrequency.cc',
                   'casa-source/casatools/casacore/casa/OS/MemoryTrace.cc',
                   'casa-source/casatools/casacore/tables/Tables/PlainColumn.cc', 'casa-source/casatools/casacore/casa/Utilities/RegSequence.cc',
                   'casa-source/casatools/casacore/tables/DataMan/StManAipsIO.cc', 'casa-source/casatools/casacore/tables/Tables/TableColumn.cc',
                   'casa-source/casatools/casacore/tables/Tables/TableRecord.cc', 'casa-source/casatools/casacore/casa/Containers/ValueHolder.cc',
                   'casa-source/casatools/casacore/tables/DataMan/BitFlagsEngine.cc', 'casa-source/casatools/casacore/tables/Tables/ConcatColumn.cc',
                   'casa-source/casatools/casacore/casa/Utilities/Notice.cc', 'casa-source/casatools/casacore/tables/Tables/ScalarColumn_tmpl.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprNode.cc', 'casa-source/casatools/casacore/tables/Tables/BaseColDesc.cc',
                   'casa-source/casatools/casacore/tables/Tables/ConcatTable.cc', 'casa-source/casatools/casacore/tables/DataMan/StManColumn.cc',
                   'casa-source/casatools/casacore/tables/Tables/ConcatRows.cc', 'casa-source/casatools/casacore/casa/Utilities/Copy2.cc',
                   'casa-source/casatools/casacore/tables/DataMan/DataManError.cc', 'casa-source/casatools/casacore/measures/Measures/MConvertBase.cc',
                   'casa-source/casatools/casacore/casa/Containers/RecordInterface.cc', 'casa-source/casatools/casacore/tables/Tables/SubTabDesc.cc',
                   'casa-source/casatools/casacore/tables/TaQL/TableParse.cc', 'casa-source/casatools/casacore/tables/Tables/ColDescSet.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSObservation.cc', 'casa-source/casatools/casacore/casa/Arrays/Array2Math.cc',
                   'casa-source/casatools/casacore/casa/Containers/RecordDescRep.cc', 'casa-source/casatools/casacore/tables/Tables/TableLockData.cc',
                   'casa-source/casatools/casacore/tables/Tables/TableSyncData.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSFieldColumns.cc', 'casa-source/casatools/casacore/casa/Logging/LogOrigin.cc',
                   'casa-source/casatools/casacore/tables/DataMan/StArrayFile.cc', 'casa-source/casatools/casacore/scimath/StatsFramework/StatisticsData.cc',
                   'casa-source/casatools/casacore/tables/Tables/TableRecordRep.cc', 'casa-source/casatools/casacore/casa/OS/Conversion.cc',
                   'casa-source/casatools/casacore/casa/Containers/RecordDesc.cc', 'casa-source/casatools/casacore/casa/IO/CanonicalIO.cc',
                   'casa-source/casatools/casacore/casa/OS/RegularFile.cc', 'casa-source/casatools/casacore/tables/Tables/TableKeyword.cc',
                   'casa-source/casatools/casacore/casa/IO/LECanonicalIO.cc', 'casa-source/casatools/casacore/measures/Measures/MeasureHolder.cc',
                   'casa-source/casatools/casacore/casa/System/ProgressMeter.cc', 'casa-source/casatools/casacore/tables/Tables/SetupNewTab.cc',
                   'casa-source/casatools/casacore/tables/DataMan/StandardStMan.cc', 'casa-source/casatools/casacore/tables/Tables/StorageOption.cc',
                   'casa-source/casatools/casacore/tables/Tables/TableIter.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MeasurementSet.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSPointing.cc', 'casa-source/casatools/casacore/casa/System/AipsrcBool.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSProcessor.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSFreqOffset.cc',
                   'casa-source/casatools/casacore/measures/Measures/MEarthMagnetic.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSPolarization.cc',
                   'casa-source/casatools/casacore/casa/Containers/ValueHolderRep.cc', 'casa-source/casatools/casacore/tables/Tables/ArrColDesc_tmpl.cc',
                   'casa-source/casatools/casacore/tables/Tables/ArrColData.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSSelection.cc', 'casa-source/casatools/casacore/ms/MSOper/MSKeys.cc',
                   'casa-source/casatools/casacore/tables/Tables/ArrColDesc.cc', 'casa-source/casatools/casacore/tables/Tables/ArrayColumnBase.cc',
                   'casa-source/casatools/casacore/tables/DataMan/CompressFloat.cc', 'casa-source/casatools/casacore/casa/Quanta/QuantumHolder.cc',
                   'casa-source/casatools/casacore/casa/IO/RegularFileIO.cc', 'casa-source/casatools/casacore/casa/Utilities/StringDistance.cc',
                   'casa-source/casatools/casacore/tables/DataMan/TiledDataStMan.cc',
                   'casa-source/casatools/casacore/casa/Arrays/ArrayUtil2.cc', 'casa-source/casatools/casacore/tables/DataMan/CompressComplex.cc',
                   'casa-source/casatools/casacore/measures/Measures/MRadialVelocity.cc',
                   'casa-source/casatools/casacore/ms/MSOper/MSDerivedValues.cc', 'casa-source/casatools/casacore/casa/Quanta/MVEarthMagnetic.cc',
                   'casa-source/casatools/casacore/casa/Logging/LogMessage.cc', 'casa-source/casatools/casacore/ms/MSSel/MSSpwParse.cc',
                   'casa-source/casatools/casacore/tables/TaQL/RecordGram.cc', 'casa-source/casatools/casacore/tables/DataMan/TiledStMan.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSColumns.cc', 'casa-source/casatools/casacore/casa/Utilities/DataType.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSStateParse.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSDopplerUtil.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSAntennaParse.cc', 'casa-source/casatools/casacore/tables/DataMan/TiledCellStMan.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSMainColumns.cc', 'casa-source/casatools/casacore/measures/Measures/MCDirection.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSFeedParse.cc', 'casa-source/casatools/casacore/ms/MSSel/MSSelectableTable.cc',
                   'casa-source/casatools/casacore/tables/DataMan/TSMCubeBuff.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSFeedColumns.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSSourceIndex.cc', 'casa-source/casatools/casacore/ms/MSSel/MSAntennaIndex.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSStateColumns.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSSourceColumns.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSSysCalColumns.cc', 'casa-source/casatools/casacore/casa/Containers/Record2Interface.cc',
                   'casa-source/casatools/casacore/tables/TaQL/TaQLNodeHandler.cc', 'casa-source/casatools/casacore/casa/IO/BucketBase.cc',
                   'casa-source/casatools/casacore/tables/DataMan/TSMCubeMMap.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSTableIndex.cc', 'casa-source/casatools/casacore/measures/TableMeasures/TableMeasColumn.cc',
                   'casa-source/casatools/casacore/casa/IO/BucketMapped.cc', 'casa-source/casatools/casacore/tables/Tables/ColumnsIndex.cc',
                   'casa-source/casatools/casacore/tables/TaQL/TaQLNode.cc', 'casa-source/casatools/casacore/casa/IO/BucketBuffered.cc',
                   'casa-source/casatools/casacore/tables/TaQL/RecordExpr.cc', 'casa-source/casatools/casacore/tables/TaQL/TaQLNodeVisitor.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprLogicNode.cc', 'casa-source/casatools/casacore/tables/DataMan/TiledShapeStMan.cc',
                   'casa-source/casatools/casacore/measures/Measures/VelocityMachine.cc', 'casa-source/casatools/casacore/tables/DataMan/IncrementalStMan.cc',
                   'casa-source/casatools/casacore/measures/Measures/MCFrequency.cc', 'casa-source/casatools/casacore/tables/Tables/TableLocker.cc',
                   'casa-source/casatools/casacore/tables/TaQL/TaQLNodeDer.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprRange.cc',
                   'casa-source/casatools/casacore/measures/Measures/Aberration.cc', 'casa-source/casatools/casacore/tables/TaQL/TaQLNodeRep.cc',
                   'casa-source/casatools/casacore/casa/Arrays/Array2.cc', 'casa-source/casatools/casacore/measures/Measures/MCRadialVelocity.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSAntennaColumns.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSDopplerColumns.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSFlagCmdColumns.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSHistoryColumns.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSSelectionError.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSSpectralWindow.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSWeatherColumns.cc', 'casa-source/casatools/casacore/casa/Quanta/MVRadialVelocity.cc',
                   'casa-source/casatools/casacore/tables/Tables/RefRows.cc', 'casa-source/casatools/casacore/tables/Tables/ScaColDesc_tmpl.cc',
                   'casa-source/casatools/casacore/tables/Tables/RowNumbers.cc', 'casa-source/casatools/casacore/tables/DataMan/VirtArrCol.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprMathNode.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprNodeRep.cc',
                   'casa-source/casatools/casacore/tables/TaQL/MArrayBase.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprNodeSet.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprUDFNode.cc', 'casa-source/casatools/casacore/measures/TableMeasures/TableQuantumDesc.cc',
                   'casa-source/casatools/casacore/tables/DataMan/TiledColumnStMan.cc',
                   'casa-source/casatools/casacore/casa/Containers/Allocator.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSSelectionTools.cc', 'casa-source/casatools/casacore/casa/Arrays/ArrayBase.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSDataDescColumns.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSSpWindowColumns.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSPointingColumns.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSDataDescription.cc',
                   'casa-source/casatools/casacore/tables/DataMan/DataManAccessor.cc', 'casa-source/casatools/casacore/tables/TaQL/TaQLNodeResult.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprAggrNode.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprConeNode.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprFuncNode.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprUnitNode.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprGroupAggrFunc.cc',
                   'casa-source/casatools/casacore/measures/TableMeasures/TableMeasDescBase.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprGroup.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSProcessorColumns.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprNodeArray.cc',
                   'casa-source/casatools/casacore/measures/TableMeasures/TableMeasType.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprDerNode.cc',
                   'casa-source/casatools/casacore/tables/TaQL/TableGram.cc', 'casa-source/casatools/casacore/tables/DataMan/VirtualTaQLColumn.cc',
                   'casa-source/casatools/casacore/measures/TableMeasures/TableMeasValueDesc.cc', 'casa-source/casatools/casacore/ms/MSSel/MSSpwGram.cc',
                   'casa-source/casatools/casacore/tables/DataMan/ISMColumn.cc', 'casa-source/casatools/casacore/ms/MSSel/MSSpwIndex.cc',
                   'casa-source/casatools/casacore/casa/OS/CanonicalConversion.cc', 'casa-source/casatools/casacore/casa/OS/EnvVar.cc',
                   'casa-source/casatools/casacore/tables/DataMan/ForwardCol.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSFreqOffColumns.cc',
                   'casa-source/casatools/casacore/casa/Utilities/RecordTransformable.cc', 'casa-source/casatools/casacore/measures/TableMeasures/TableMeasRefDesc.cc',
                   'casa-source/casatools/casacore/tables/DataMan/VirtColEng.cc', 'casa-source/casatools/casacore/casa/BasicSL/Constants.cc',
                   'casa-source/casatools/casacore/measures/TableMeasures/TableMeasOffsetDesc.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSObsColumns.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprLogicNodeArray.cc', 'casa-source/casatools/casacore/casa/Arrays/ArrayPosIter.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSTimeGram.cc', 'casa-source/casatools/casacore/ms/MSSel/MSTimeParse.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSStateGram.cc', 'casa-source/casatools/casacore/ms/MSSel/MSStateIndex.cc',
                   'casa-source/casatools/casacore/measures/Measures/MCDoppler.cc',
                   'casa-source/casatools/casacore/casa/OS/LECanonicalDataConversion.cc', 'casa-source/casatools/casacore/casa/OS/DataConversion.cc',
                   'casa-source/casatools/casacore/casa/OS/LECanonicalConversion.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSPolColumns.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprMathNodeArray.cc', 'casa-source/casatools/casacore/ms/MSSel/MSUvDistGram.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSUvDistParse.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprUDFNodeArray.cc',
                   'casa-source/casatools/casacore/tables/Tables/ScaRecordColDesc.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprFuncNodeArray.cc',
                   'casa-source/casatools/casacore/casa/Arrays/ArrayPartMath.cc', 'casa-source/casatools/casacore/tables/Tables/ScaRecordColData.cc',
                   'casa-source/casatools/casacore/tables/DataMan/StArrAipsIO.cc', 'casa-source/casatools/casacore/tables/TaQL/ExprAggrNodeArray.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprGroupAggrFuncArray.cc', 'casa-source/casatools/casacore/ms/MSSel/MSFeedGram.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSPolnGram.cc', 'casa-source/casatools/casacore/ms/MSSel/MSFeedIndex.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSPolnParse.cc', 'casa-source/casatools/casacore/ms/MSSel/MSScanGram.cc',
                   'casa-source/casatools/casacore/scimath/StatsFramework/ClassicalStatisticsData.cc', 'casa-source/casatools/casacore/ms/MSSel/MSCorrGram.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprDerNodeArray.cc', 'casa-source/casatools/casacore/ms/MSSel/MSCorrParse.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSScanParse.cc', 'casa-source/casatools/casacore/ms/MSSel/MSDataDescIndex.cc',
                   'casa-source/casatools/casacore/tables/DataMan/StIndArrAIO.cc', 'casa-source/casatools/casacore/casa/Quanta/UnitVal.cc',
                   'casa-source/casatools/casacore/derivedmscal/DerivedMC/UDFMSCal.cc', 'casa-source/casatools/casacore/tables/DataMan/StIndArray.cc',
                   'casa-source/casatools/casacore/derivedmscal/DerivedMC/MSCalEngine.cc', 'casa-source/casatools/casacore/ms/MSSel/MSPolIndex.cc',
                   'casa-source/casatools/casacore/measures/Measures/MCBaseline.cc', 'casa-source/casatools/casacore/casa/Quanta/MVBaseline.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/StokesConverter.cc', 'casa-source/casatools/casacore/ms/MSSel/MSSelectionErrorHandler.cc',
                   'casa-source/casatools/casacore/scimath/Mathematics/SquareMatrix2.cc', 'casa-source/casatools/casacore/ms/MSSel/MSArrayGram.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSArrayParse.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSFieldGram.cc', 'casa-source/casatools/casacore/ms/MSSel/MSAntennaGram.cc',
                   'casa-source/casatools/casacore/tables/TaQL/ExprNodeRecord.cc', 'casa-source/casatools/casacore/ms/MSSel/MSFieldIndex.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSFieldParse.cc', 'casa-source/casatools/casacore/casa/OS/DOos.cc',
                   'casa-source/casatools/casacore/casa/OS/DirectoryIterator.cc', 'casa-source/casatools/casacore/ms/MSSel/MSObservationGram.cc',
                   'casa-source/casatools/casacore/ms/MSSel/MSObservationParse.cc', 'casa-source/casatools/casacore/casa/Utilities/CountedPtr2.cc',
                   'casa-source/casatools/casacore/casa/OS/OMP.cc', 'casa-source/casatools/casacore/casa/BasicMath/Random.cc',
                   'casa-source/casatools/casacore/measures/Measures/Muvw.cc', 'casa-source/casatools/casacore/casa/OS/Path.cc',
                   'casa-source/casatools/casacore/casa/Utilities/Sort.cc', 'casa-source/casatools/casacore/casa/OS/Time.cc',
                   'casa-source/casatools/casacore/casa/Quanta/Unit.cc', 'casa-source/casatools/casacore/casa/Utilities/SortError.cc',
                   'casa-source/casatools/casacore/casa/BasicMath/Math.cc', 'casa-source/casatools/casacore/casa/BasicSL/Complex.cc',
                   'casa-source/casatools/casacore/casa/Arrays/Matrix2Math.cc', 'casa-source/casatools/casacore/casa/Arrays/Array_tmpl.cc',
#                  'casa-source/casatools/casacore/measures/TableMeasures/TableMeas_tmpl.cc',
                   'casa-source/casatools/casacore/casa/Containers/Block_tmpl.cc',
                   'casa-source/casatools/casacore/casa/Quanta/Euler.cc', 'casa-source/casatools/casacore/casa/Logging/LogIO.cc',
                   'casa-source/casatools/casacore/casa/Quanta/MVuvw.cc', 'casa-source/casatools/casacore/measures/Measures/MCuvw.cc',
                   'casa-source/casatools/casacore/casa/Quanta/QBase.cc', 'casa-source/casatools/casacore/casa/Utilities/Regex.cc',
                   'casa-source/casatools/casacore/tables/Tables/ReadAsciiTable.cc', 'casa-source/casatools/casacore/casa/Arrays/Slice.cc',
                   'casa-source/casatools/casacore/tables/Tables/Table.cc', 'casa-source/casatools/casacore/tables/Tables/MemoryTable.cc',
                   'casa-source/casatools/casacore/casa/IO/AipsIO.cc', 'casa-source/casatools/casacore/tables/DataMan/MemoryStMan.cc',
                   'casa-source/casatools/casacore/casa/OS/File.cc', 'casa-source/casatools/casacore/casa/System/Aipsrc.cc',
                   'casa-source/casatools/casacore/measures/Measures/MCBase.cc', 'casa-source/casatools/casacore/casa/OS/Timer.cc',
                   'casa-source/casatools/casacore/casa/IO/ByteIO.cc', 'casa-source/casatools/casacore/casa/OS/DynLib.cc',
                   'casa-source/casatools/casacore/measures/Measures/MEpoch.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSFeed.cc',
                   'casa-source/casatools/casacore/measures/Measures/MRBase.cc', 'casa-source/casatools/casacore/casa/Quanta/MVTime.cc',
                   'casa-source/casatools/casacore/casa/Arrays/Matrix_tmpl.cc', 'casa-source/casatools/casacore/casa/Containers/Record.cc',
                   'casa-source/casatools/casacore/casa/Containers/Record2.cc', 'casa-source/casatools/casacore/casa/Arrays/Slicer.cc',
                   'casa-source/casatools/casacore/casa/IO/TypeIO.cc',
                   'casa-source/casatools/casacore/measures/Measures/Stokes.cc', 'casa-source/casatools/casacore/casa/Arrays/Vector_tmpl.cc',
                   'casa-source/casatools/casacore/tables/DataMan/ISMBase.cc', 'casa-source/casatools/casacore/casa/Logging/LogSink.cc',
                   'casa-source/casatools/casacore/casa/IO/BucketFile.cc', 'casa-source/casatools/casacore/casa/IO/BucketCache.cc',
                   'casa-source/casatools/casacore/casa/Logging/NullLogSink.cc', 'casa-source/casatools/casacore/tables/DataMan/ISMIndColumn.cc',
                   'casa-source/casatools/casacore/casa/Logging/MemoryLogSink.cc', 'casa-source/casatools/casacore/casa/IO/MultiFileBase.cc',
                   'casa-source/casatools/casacore/casa/Logging/StreamLogSink.cc', 'casa-source/casatools/casacore/casa/Logging/LogSinkInterface.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSField.cc', 'casa-source/casatools/casacore/measures/Measures/MCEpoch.cc',
                   'casa-source/casatools/casacore/tables/DataMan/MSMBase.cc',  'casa-source/casatools/casacore/ms/MSSel/MSParse.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSState.cc', 'casa-source/casatools/casacore/tables/DataMan/MSMDirColumn.cc',
                   'casa-source/casatools/casacore/tables/DataMan/MSMIndColumn.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSTable.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSTable2.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSTableImpl.cc',
                   'casa-source/casatools/casacore/casa/Quanta/MVAngle.cc', 'casa-source/casatools/casacore/casa/Quanta/MVEpoch.cc',
                   'casa-source/casatools/casacore/casa/System/AppInfo.cc', 'casa-source/casatools/casacore/casa/System/AipsrcVString.cc',
                   'casa-source/casatools/casacore/casa/System/AipsrcVBool.cc',
                   'casa-source/casatools/casacore/measures/Measures/Measure.cc', 'casa-source/casatools/casacore/casa/Quanta/Quantum2.cc',
                   'casa-source/casatools/casacore/tables/DataMan/SSMBase.cc', 'casa-source/casatools/casacore/tables/DataMan/SSMDirColumn.cc',
                   'casa-source/casatools/casacore/tables/DataMan/SSMStringHandler.cc', 'casa-source/casatools/casacore/tables/DataMan/SSMIndColumn.cc',
                   'casa-source/casatools/casacore/casa/OS/SymLink.cc', 'casa-source/casatools/casacore/tables/DataMan/TSMCube.cc',
                   'casa-source/casatools/casacore/tables/DataMan/SSMIndStringColumn.cc', 'casa-source/casatools/casacore/tables/DataMan/TSMFile.cc',
                   'casa-source/casatools/casacore/tables/TaQL/UDFBase.cc', 'casa-source/casatools/casacore/casa/Quanta/UnitDim.cc',
                   'casa-source/casatools/casacore/casa/Quanta/UnitMap.cc', 'casa-source/casatools/casacore/casa/Quanta/UnitMap2.cc',
                   'casa-source/casatools/casacore/casa/Quanta/UnitMap5.cc', 'casa-source/casatools/casacore/casa/Quanta/UnitMap6.cc',
                   'casa-source/casatools/casacore/casa/Quanta/UnitMap7.cc', 'casa-source/casatools/casacore/casa/Quanta/UnitMap3.cc',
                   'casa-source/casatools/casacore/casa/Quanta/UnitMap4.cc', 'casa-source/casatools/casacore/casa/Utilities/ValType.cc',
                   'casa-source/casatools/casacore/casa/OS/HostInfo.cc', 'casa-source/casatools/casacore/tables/DataMan/ISMIndex.cc',
                   'casa-source/casatools/casacore/casa/IO/LockFile.cc', 'casa-source/casatools/casacore/measures/Measures/MDoppler.cc',
                   'casa-source/casatools/casacore/casa/IO/MFFileIO.cc', 'casa-source/casatools/casacore/casa/IO/MMapfdIO.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSSource.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSSysCal.cc',
                   'casa-source/casatools/casacore/casa/Utilities/MUString.cc', 'casa-source/casatools/casacore/casa/IO/FileLocker.cc',
                   'casa-source/casatools/casacore/measures/Measures/MeasData.cc', 'casa-source/casatools/casacore/measures/Measures/MeasMath.cc',
                   'casa-source/casatools/casacore/measures/Measures/Precession.cc', 'casa-source/casatools/casacore/casa/IO/MemoryIO.cc',
                   'casa-source/casatools/casacore/measures/Measures/Nutation.cc', 'casa-source/casatools/casacore/casa/System/ObjectID.cc',
                   'casa-source/casatools/casacore/tables/Tables/RefTable.cc', 'casa-source/casatools/casacore/tables/DataMan/SSMIndex.cc',
                   'casa-source/casatools/casacore/measures/Measures/SolarPos.cc', 'casa-source/casatools/casacore/tables/DataMan/TSMShape.cc',
                   'casa-source/casatools/casacore/casa/Quanta/UnitName.cc', 'casa-source/casatools/casacore/tables/Tables/BaseTable.cc',
                   'casa-source/casatools/casacore/tables/Tables/BaseTabIter.cc', 'casa-source/casatools/casacore/tables/TaQL/TaQLShow.cc',
                   'casa-source/casatools/casacore/tables/Tables/ColumnSet.cc', 'casa-source/casatools/casacore/casa/OS/Directory.cc',
                   'casa-source/casatools/casacore/casa/IO/FilebufIO.cc', 'casa-source/casatools/casacore/casa/Arrays/IPosition.cc',
#                  'casa-source/casatools/casacore/casa/Arrays/IPosition2.cc',
                   'casa-source/casatools/casacore/tables/DataMan/ISMBucket.cc',
                   'casa-source/casatools/casacore/casa/Logging/LogFilter.cc',
                   'casa-source/casatools/casacore/casa/Logging/LogFilterInterface.cc',
                   'casa-source/casatools/casacore/casa/IO/FiledesIO.cc', 'casa-source/casatools/casacore/measures/Measures/MBaseline.cc',
                   'casa-source/casatools/casacore/measures/Measures/MPosition.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSAntenna.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSDoppler.cc', 'casa-source/casatools/casacore/ms/MeasurementSets/MSFlagCmd.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSHistory.cc', 'casa-source/casatools/casacore/tables/DataMan/MSMColumn.cc',
                   'casa-source/casatools/casacore/ms/MeasurementSets/MSWeather.cc', 'casa-source/casatools/casacore/casa/Quanta/MVDoppler.cc',
                   'casa-source/casatools/casacore/measures/Measures/MeasFrame.cc', 'casa-source/casatools/casacore/measures/Measures/MeasTable.cc',
                   'casa-source/casatools/casacore/measures/Measures/MeasTableMul.cc', 'casa-source/casatools/casacore/measures/Measures/MCFrame.cc',
                   'casa-source/casatools/casacore/measures/Measures/MeasIERS.cc', 'casa-source/casatools/casacore/measures/Measures/MeasComet.cc',
                   'casa-source/casatools/casacore/casa/Quanta/MeasValue.cc', 'casa-source/casatools/casacore/casa/IO/MultiFile.cc',
                   'casa-source/casatools/casacore/casa/Quanta/QLogical2.cc', 'casa-source/casatools/casacore/casa/Containers/RecordRep.cc',
                   'casa-source/casatools/casacore/casa/Quanta/RotMatrix.cc', 'casa-source/casatools/casacore/tables/DataMan/SSMColumn.cc',
                   'casa-source/casatools/casacore/casa/System/AppState.cc', 'casa-source/casatools/casacore/measures/Measures/MeasJPL.cc',
                   'casa-source/casatools/casacore/tables/DataMan/TSMColumn.cc', 'casa-source/casatools/casacore/tables/DataMan/TSMIdColumn.cc',
                   'casa-source/casatools/casacore/tables/DataMan/TSMDataColumn.cc', 'casa-source/casatools/casacore/tables/DataMan/TSMCoordColumn.cc',
                   'casa-source/casatools/casacore/casa/IO/MultiHDF5.cc', 'casa-source/casatools/casacore/tables/Tables/NullTable.cc',
                   'casa-source/casatools/casacore/tables/Tables/RefColumn.cc',
#                  'casa-source/casatools/casacore/casa/BasicSL/RegexBase.cc',
                   'casa-source/casatools/casacore/tables/DataMan/TSMOption.cc', 'casa-source/casatools/casacore/tables/TaQL/TaQLStyle.cc',
                   'casa-source/casatools/casacore/tables/Tables/TableAttr.cc', 'casa-source/casatools/casacore/casa/HDF5/HDF5Object.cc',
                   'casa-source/casatools/casacore/casa/HDF5/HDF5Record.cc', 'casa-source/casatools/casacore/casa/HDF5/HDF5DataSet.cc',
                   'casa-source/casatools/casacore/casa/HDF5/HDF5File.cc', 'casa-source/casatools/casacore/casa/HDF5/HDF5Group.cc',
                   'casa-source/casatools/casacore/tables/Tables/TableCopy.cc', 'casa-source/casatools/casacore/tables/Tables/TableDesc.cc',
                   'casa-source/casatools/casacore/casa/HDF5/HDF5DataType.cc', 'casa-source/casatools/casacore/tables/DataMan/DataManInfo.cc',
                   'casa-source/casatools/casacore/casa/HDF5/HDF5HidMeta.cc', 'casa-source/casatools/casacore/tables/Tables/TableInfo.cc',
                   'casa-source/casatools/casacore/casa/HDF5/HDF5Error.cc', 'casa-source/casatools/casacore/tables/Tables/TableLock.cc',
                   'casa-source/casatools/casacore/tables/Tables/TabPath.cc', 'casa-source/casatools/casacore/ms/MSSel/MSSSpwErrorHandler.cc',
#                  'casa-source/casatools/casacore/casa/Utilities/cregex.cc',
                   'casa-source/casatools/casacore/casa/aips.cc',
                   #### compile asdm storage manager into executable
                   'casa-source/casatools/src/code/asdmstman/AsdmColumn.cc', 'casa-source/casatools/src/code/asdmstman/AsdmStMan.cc',
                   'casa-source/casatools/src/code/asdmstman/AsdmIndex.cc', 'casa-source/casatools/src/code/asdmstman/Register.cc',
                   #### version information
                   'generated/source/version.cc',
]

platform_cflags = { 'darwin': [ ],
                    'linux2': [ '-fopenmp', '-fcx-fortran-rules' ],
                    'linux': [ '-fopenmp', '-fcx-fortran-rules' ],
};
platform_ldflags = { 'darwin': [ ],
                     'linux2': [ '-fopenmp' ],
                     'linux': [ '-fopenmp' ],
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
                                      '-fno-omit-frame-pointer', '-DWITHOUT_ACS', '-DWITHOUT_BOOST', '-DCASA6', \
                                      '-DCASATOOLS' ] + platform_cflags[sys.platform],
                       'generated/':     ['-DAIPS_64B', '-DAIPS_AUTO_STL', '-DAIPS_DEBUG', '-DAIPS_HAS_QWT', \
                                          '-DAIPS_LINUX', '-DAIPS_LITTLE_ENDIAN', '-DAIPS_STDLIB', \
                                          '-DCASACORE_NEEDS_RETHROW', '-DCASA_USECASAPATH', '-DDBUS_CPP', '-DQWT6', \
                                          '-DUseCasacoreNamespace', '-D_FILE_OFFSET_BITS=64', '-D_LARGEFILE_SOURCE', \
                                          '-DNO_CRASH_REPORTER', '-fno-omit-frame-pointer', '-DWITHOUT_ACS', '-DWITHOUT_BOOST',
                                          '-DCASATOOLS', '-DCASA6' ] + platform_cflags[sys.platform] }

xml_xlate = { }
xml_files = [ 'xml/wvrgcal.xml' ]
public_files = [ 'src/tasks/LICENSE.txt' ]
private_scripts = [ 'src/tasks/task_wvrgcal.py', 'src/scripts/almahelpers.py' ]
private_modules = [  ]

if pyversion < 3:
    str_encode = str
    str_decode = str
    def pipe_decode(output):
        return output
else:
    def str_encode(s):
        return bytes(s,sys.getdefaultencoding())
    def str_decode(bs):
        return bs.decode(sys.getdefaultencoding(),"strict")
    def pipe_decode(output):
        if isinstance(output,bytes) or isinstance(output,bytearray):
            return str_decode(output)
        elif isinstance(output,tuple):
            return ( None if output[0] is None else str_decode(output[0]), None if output[1] is None else str_decode(output[1]) )
        else:
            return ("","")

def isexe(f):
    return os.path.isfile(f) and os.access(f, os.X_OK)

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
    ccache = [ tools_config['build.compiler.ccache'] ] if 'build.compiler.ccache' in tools_config and len(tools_config['build.compiler.ccache']) > 0 else [ ]
    cflags = map(lambda pair: pair[1],filter(lambda pair: pair[0].startswith('build.flags.compile'),tools_config.items()))
    cflags = [item for sublist in cflags for item in sublist]         ### python has not yet hit upon a flatten function...
    ldflags = list(map(lambda pair: pair[1],filter(lambda pair: pair[0].startswith('build.flags.link'),tools_config.items())))
    ldflags = clean_args([item for sublist in ldflags for item in sublist])         ### python has not yet hit upon a flatten function...
    ldflags = ldflags + [ '-L%s/local/lib' % os.getcwd( ) ]
    ld_dirs = list(set(map(lambda s: s[2:],filter(lambda s: s.startswith("-L"),ldflags))))
    if 'build.python.numpy_dir' in tools_config and len(tools_config['build.python.numpy_dir']) > 0:
        cflags.insert(0,'-I' + tools_config['build.python.numpy_dir'])       ### OS could have different version of python in
                                                                      ###     /usr/include (e.g. rhel6)
    new_compiler_cxx = ccache + [tools_config['build.compiler.cxx'], '-g', '-std=c++11', '-I%s/local/include' % os.getcwd( ), '-Isrc/code', '-Ibinding/include','-Igenerated/include','-Ilibcasatools/generated/include','-Icasa-source/casatools/src/code','-Icasa-source','-Icasa-source/casatools/casacore', '-Iinclude', '-Isakura-source/src'] + cflags + default_compiler_so[1:]
    new_compiler_cc = ccache + [tools_config['build.compiler.cc'], '-g', '-Isrc/code', '-Ibinding/include','-Igenerated/include','-Ilibcasatools/generated/include','-Icasa-source/casatools/src/code','-Icasa-source','-Icasa-source/casatools/casacore', '-Iinclude', 'sakura-source/src'] + cflags + default_compiler_so[1:]
    new_compiler_fortran = [tools_config['build.compiler.fortran']]

    new_compiler_cxx = list(filter(lambda flag: not flag.startswith('-O'),new_compiler_cxx))
    new_compiler_ccc = list(filter(lambda flag: not flag.startswith('-O'),new_compiler_cc))

    new_linker_cxx = [ tools_config['build.compiler.cxx'] ]

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

        if target_desc == "executable":
            try:
                cxx = [ props['build.compiler.cxx'] ] 
                link_line = cxx + [ '-o', output_filename ] + platform_ldflags[sys.platform] + rpath + objects + [ os.path.join('local', 'lib', l) for l in ['libboost_filesystem.a', 'libboost_program_options.a', 'libboost_random.a', 'libboost_regex.a', 'libboost_system.a', 'libgsl.a', 'libgslcblas.a'] ] + [ "-l%s" % x for x in libraries if not any([f in x for f in ['boost', 'gsl']]) ] + [ "-L%s" % l for l in ld_dirs ]
                print(link_line)
                self.spawn(link_line)
            except DistutilsExecError as msg:
                raise CompileError(msg)
        else:
            superld( target_desc, objects, output_filename, output_dir,
                     None if libraries is None else [library_mangle[l] if l in library_mangle else l for l in libraries],
                     ld_dirs if library_dirs is None else ["-L/tmp"]+ld_dirs+library_dirs+local_library_path, runtime_library_dirs, export_symbols,
#                    debug, ["-L/opt/local/lib"], extra_postargs, build_temp, target_lang )
                     debug, extra_preargs, None, build_temp, target_lang )

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
                new_compiler = new_compiler_cxx
            ## get the cflags for the module being built; key is a subdir, value are flags
            m_cflags = map(lambda x: x[1] if x[0] in src else [], module_cflags.items())
            m_cflags = [item for sublist in m_cflags for item in sublist] ### python has not yet hit upon a flatten function...
            self.set_executable('compiler_so', clean_args(new_compiler + m_cflags + ( [ '-DUSE_GRPC' ] if tools_config['option.grpc'] != "0" else [ ] )))
            if verbose:
                print("compiling %s" % src)
            supercc(obj, src, ext, clean_args(cc_args), clean_args(postargs), clean_args(pp_opts))

        # reset the default compiler_so (may not be necessary)
        self.compiler_so = default_compiler_so

    # inject our redefined _compile method into the class
    self._compile = _compile
    self.link = _link

def casa_version( ):
    ##  With:
    ##
    ##  version_proc = subprocess.Popen(['code/install/resolvegitrevision.sh', '--pretty-print'], stdout=subprocess.PIPE, shell=True, cwd='casa-source')
    ##
    ##  script did NOT receive '--pretty-print' parameter....
    version_info = os.popen("cd casa-source/casa5 && code/install/resolvegitrevision.sh --pretty-print").read( ).splitlines( )
    assert len(version_info) > 0, "could not generate CASA version string"
    version_match = re.compile(r'(\d+)\.(\d+)\.(\d+).*?(\d+).?')
    version = version_match.findall(version_info[0])
    assert len(version[0]) >= 4, "CASA version string format error, '%s' got '%s'" % (version_info[0],version[0])
    return list(version[0])

def generate_version_file( file ):
    version = casa_version( )
    mkpath(os.path.dirname(file))

    replacements = { '@CASA_VERSION_MAJOR@': version[0], '@CASA_VERSION_MINOR@': version[1],
                     '@CASA_VERSION_PATCH@': version[2], '@CASA_VERSION_FEATURE@': version[3],
                     '@CASA_VERSION_DESC@': 'ALMAtasks:v1.0.0' }

    with open('casa-source/casatools/src/code/stdcasa/version.cc.in') as infile, open(file, 'w') as outfile:
        for line in infile:
            for src, target in replacements.items( ):
                line = line.replace(src, target)
            outfile.write(line)


def generate_lex(sources,output_dir='generated/include'):
    """Generate lex compilation files...
    """
    mkpath(output_dir)
    for file in sources:
        name = os.path.basename(file)
        base = os.path.splitext(name)[0]
        if Proc([tools_config['build.compiler.flex'], "-P%s" % base, "-o", "%s%s%s.lcc" % (output_dir,os.sep,base), file]) != 0:
            sys.exit('lex generation of %s%s%s.lcc failed' % (output_dir,os.sep,base))

def generate_yacc(sources,output_dir='generated/include'):
    """Generate yacc compilation files...
    """
    mkpath(output_dir)
    for file in sources:
        name = os.path.basename(file)
        base = os.path.splitext(name)[0]
        if Proc([tools_config['build.compiler.bison'], "-y", "-p", base, "-o", "%s%s%s.ycc" % (output_dir,os.sep,base), file]) != 0:
            sys.exit('lex generation of %s%s%s.ycc failed' % (output_dir,os.sep,base))

def upgrade_xml( conversions ):
    mkpath("xml")
    for k in conversions.keys( ):
        if not os.path.exists(conversions[k]):
            print("upgrading %s" % k)

            print("%s %s %s" % (tools_config['build.compiler.xml-casa'], "-upgrade", k))
            proc = Popen( [tools_config['build.compiler.xml-casa'], "-upgrade", k],
                          stdout=subprocess.PIPE )

            (output, error) = pipe_decode(proc.communicate( ))

            exit_code = proc.wait( )
            if exit_code != 0:
                sys.exit('upgrading %s failed' % conversions[k])
            xmlfd = open(conversions[k], 'w')
            xmlfd.write(output)
            xmlfd.close( )

def generate_pyinit(moduledir,tasks):
    """Generate __init__.py for the module
    """
    outfile = os.path.join(moduledir,'__init__.py')
    with open(outfile, "w") as fd:
        fd.write("""###########################################################################\n""")
        fd.write("""########################## generated by setup.py ##########################\n""")
        fd.write("""###########################################################################\n""")
        fd.write("from __future__ import absolute_import\n")
        fd.write("__name__ = '%s'\n" % module_name)
        fd.write("__all__ = [ \n")
        for task in tasks:
            fd.write("            '%s',\n" % task)
        fd.write("          ]\n\n")
        for task in tasks:
            fd.write("from .%s import %s\n" % (task,task))
        fd.write("\n")
        for imp in [ 'from .private.almahelpers import tsysspwmap' ]:
            fd.write( "%s\n" % imp )
        fd.write("\n")

# run the customize_compiler
class casa_build_ext(build_ext):
    def build_extensions(self):
        customize_compiler(self.compiler)
        build_ext.build_extensions(self)

class BinaryDistribution(Distribution):
    user_options = BdistWheel.user_options + [
        ('build=', None, 'specify build number') ]

    def initialize_options(self):
        Distribution.initialize_options(self)
        self.build = build_number

    """Distribution which always forces a binary package with platform name"""
    def is_pure(self):
        return False
    def has_ext_modules(self):
        return True

def all_files( dir ):
    acc = [ ]
    initial_dir = os.getcwd( )
    os.chdir(os.path.join('build', distutils_dir_name('lib')))
    for root, directories, filenames in os.walk(dir):
        r = os.path.join(*root.split(os.sep)[1:])
        for filename in filenames:
            acc.append(os.path.join(r,filename))
    os.chdir(initial_dir)
    return acc

from setuptools.command.install import install
class InstallPlatlib(install):
    def finalize_options(self):
        install.finalize_options(self)
        if self.distribution.has_ext_modules():
            self.install_lib = self.install_platlib


if __name__ == '__main__':

    if not os.path.exists('local'):
        print("building third party packages (boost and gsl), this will take several minutes...")
        proc = Popen( [ "scripts/build-tpp" ], stdout=PIPE, stderr=PIPE )
        out,err = pipe_decode(proc.communicate( ))
        print(out)
        exit_code = proc.wait( )
        if exit_code != 0:
            sys.exit('installing third party packages failed')

    generate_version_file("generated/source/version.cc")
    generate_lex(CASACORE_LEX)
    generate_yacc(CASACORE_YACC)
    tmpdir = os.path.join('build', distutils_dir_name('temp'))
    moduledir = os.path.join('build', distutils_dir_name('lib'), module_name)
    privatedir = os.path.join(moduledir,"private")
    bindir = os.path.join(moduledir, "__bin__")
    libdir = os.path.join(moduledir, "__lib__")
    mkpath(bindir)
    mkpath(libdir)
    mkpath(privatedir)
    cc = new_compiler("posix", verbose=True)
    customize_compiler(cc,True)
    objs = cc.compile( CASAWVR_SOURCE, os.path.join(tmpdir,"wvrgcal") )

    libs = ["boost_program_options", "lapack", "blas", "pthread", "dl"]

    if sys.platform == 'darwin':
        ### need to get '/opt/local/lib/gcc5' from gfortran directly
        rpath = [ '-Wl,-rpath,@loader_path/../__lib__' ]
        archflags = ['-L/opt/local/lib/gcc5']
    else:
        libs.append("rt")
        rpath = [ '-Wl,-rpath,$ORIGIN/../__lib__']
        archflags = [ ]

    cc.link( CCompiler.EXECUTABLE, objs, os.path.join(bindir,"wvrgcal"), libraries=libs, extra_preargs=props['build.flags.link.openmp'] + rpath + props['build.flags.link.gsl'] + archflags )
    if isexe("scripts/mod-closure") and not os.path.isfile(".created.closure"):
        print("generating module closure...")
        if Proc([ "scripts/mod-closure", moduledir, "lib=%s" % libdir ]) != 0:
            sys.exit("\tclosure generation failed...")
        open(".created.closure",'a').close( )

    upgrade_xml(xml_xlate)
    print("generating task python files...")
    proc = Popen( [tools_config['build.compiler.xml-casa'], "output-task=%s" % moduledir, "-task"] + xml_files,
                  stdout=subprocess.PIPE )

    (output, error) = pipe_decode(proc.communicate( ))

    exit_code = proc.wait( )

    if exit_code != 0:
        sys.exit('python file generation failed')

    tasks = output.split( )
    generate_pyinit(moduledir,tasks)

    print("generating gotask wrappers...\n");
    mkpath(os.path.join(moduledir,'gotasks'));
    go_dir = os.path.join(moduledir,'gotasks')
    go_init = os.path.join(go_dir,'__init__.py')
    with open(go_init, "w") as fd:
        fd.write("""###########################################################################\n""")
        fd.write("""########################## generated by setup.py ##########################\n""")
        fd.write("""###########################################################################\n""")

    proc = Popen( [tools_config['build.compiler.xml-casa'], "gotask-imp-module=almatasks", "output-gotask=%s" % go_dir, "-gotask"] + xml_files,
                  stdout=subprocess.PIPE )

    (output, error) = pipe_decode(proc.communicate( ))

    exit_code = proc.wait( )

    if exit_code != 0:
        sys.exit('python gotask generation failed')

    for f in public_files:
        copy2(f,moduledir)

    for f in private_scripts:
        copy2(f,privatedir)

    ### create empty __init__.py for private
    with open(os.path.join(privatedir,'__init__.py'), 'w') as fp: 
        pass

    for m in private_modules:
        tgt = os.path.join(privatedir,os.path.basename(m))
        copy_tree(m,tgt)

    setup( name=module_name,
           version=almatasks_version,
           maintainer="Darrell Schiebel",
           maintainer_email="drs@nrao.edu",
           author="CASA development team",
           author_email="aips2-request@nrao.edu",
           url="https://open-bitbucket.nrao.edu/projects/CASA/repos/almatasks/browse",
           download_url="https://casa.nrao.edu/download/",
           license="GNU Library or Lesser General Public License (LGPL)",
           classifiers=[ 'Programming Language :: Python :: 3'],
           description="ALMA tasks (inc wvrgcal)",
           distclass=BinaryDistribution,
           long_description="ALMA tasks",
           cmdclass={ 'bdist_wheel': BdistWheel,'install': InstallPlatlib },
           package_dir = { '' : os.path.join('build', distutils_dir_name('lib')) },
           packages=[ "almatasks", "almatasks.private", "almatasks.gotasks" ],
           package_data= { 'almatasks': all_files('almatasks/__lib__') + \
                                        all_files('almatasks/__bin__') + \
                                        ["LICENSE.txt"] },
           install_requires=["casatasks", "casatools"]
    )
