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

pyversion = float(sys.version_info[0]) + float(sys.version_info[1]) / 10.0

try:
    from casatools.config import build as props
    from casatools.config import build as tools_config
    openmp_flags = [] if len(props['build.flags.link.openmp']) == 0 else []
except:
    print("cannot find CASAtools (https://open-bitbucket.nrao.edu/projects/CASA/repos/CASAtools/browse) in PYTHONPATH")
    os._exit(1)

assert tools_config['option.boost'] != 0, "Boost framework is required to build ALMAtasks"

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

module_name = 'almatasks'

CASACORE_LEX=[ 'casa-source/casacore/tables/TaQL/RecordGram.ll',
               'casa-source/casacore/tables/TaQL/TableGram.ll',
               'casa-source/casacore/ms/MSSel/MSSpwGram.ll',
               'casa-source/casacore/ms/MSSel/MSTimeGram.ll',
               'casa-source/casacore/ms/MSSel/MSStateGram.ll',
               'casa-source/casacore/ms/MSSel/MSUvDistGram.ll',
               'casa-source/casacore/ms/MSSel/MSFeedGram.ll',
               'casa-source/casacore/ms/MSSel/MSScanGram.ll',
               'casa-source/casacore/ms/MSSel/MSCorrGram.ll',
               'casa-source/casacore/ms/MSSel/MSArrayGram.ll',
               'casa-source/casacore/ms/MSSel/MSFieldGram.ll',
               'casa-source/casacore/ms/MSSel/MSAntennaGram.ll',
               'casa-source/casacore/ms/MSSel/MSObservationGram.ll' ]
CASACORE_YACC=[ 'casa-source/casacore/tables/TaQL/RecordGram.yy',
                'casa-source/casacore/tables/TaQL/TableGram.yy',
                'casa-source/casacore/ms/MSSel/MSSpwGram.yy',
                'casa-source/casacore/ms/MSSel/MSTimeGram.yy',
                'casa-source/casacore/ms/MSSel/MSStateGram.yy',
                'casa-source/casacore/ms/MSSel/MSUvDistGram.yy',
                'casa-source/casacore/ms/MSSel/MSFeedGram.yy',
                'casa-source/casacore/ms/MSSel/MSScanGram.yy',
                'casa-source/casacore/ms/MSSel/MSCorrGram.yy',
                'casa-source/casacore/ms/MSSel/MSArrayGram.yy',
                'casa-source/casacore/ms/MSSel/MSFieldGram.yy',
                'casa-source/casacore/ms/MSSel/MSAntennaGram.yy',
                'casa-source/casacore/ms/MSSel/MSObservationGram.yy' ]

CASAWVR_SOURCE = [ 'casa-source/code/air_casawvr/cmdline/wvrgcal.cpp', 'casa-source/code/air_casawvr/cmdline/wvrgcalerrors.cpp',
                   'casa-source/code/air_casawvr/cmdline/wvrgcalfeedback.cpp', 'casa-source/code/air_casawvr/src/apps/arraygains.cpp',
                   'casa-source/code/air_casawvr/src/apps/segmentation.cpp', 'casa-source/code/air_casawvr/src/apps/arraydata.cpp',
                   'casa-source/code/air_casawvr/casawvr/mswvrdata.cpp', 'casa-source/code/air_casawvr/casawvr/msutils.cpp',
                   'casa-source/code/air_casawvr/src/dipmodel_iface.cpp', 'casa-source/code/air_casawvr/src/apps/almaresults.cpp',
                   'casa-source/code/air_casawvr/src/apps/almaopts.cpp', 'casa-source/code/air_casawvr/src/apps/almaabs_i.cpp',
                   'casa-source/code/air_casawvr/src/model_iface.cpp', 'casa-source/code/air_casawvr/src/measure_iface.cpp',
                   'casa-source/code/air_casawvr/casawvr/msspec.cpp', 'casa-source/code/air_casawvr/casawvr/msgaintable.cpp',
                   'casa-source/code/air_casawvr/src/dispersion.cpp', 'casa-source/code/air_casawvr/src/radiometermeasure.cpp',
                   'casa-source/code/air_casawvr/src/radiometer_utils.cpp', 'casa-source/code/air_casawvr/src/apps/dtdlcoeffs.cpp',
                   'casa-source/code/air_casawvr/src/model_make.cpp', 'casa-source/code/air_casawvr/src/cloudywater.cpp',
                   'casa-source/code/air_casawvr/src/rtranfer.cpp', 'casa-source/code/air_casawvr/src/columns.cpp',
                   'casa-source/code/air_casawvr/src/lineparams.cpp', 'casa-source/code/air_casawvr/src/models_basic.cpp',
                   'casa-source/code/air_casawvr/src/singlelayerwater.cpp', 'casa-source/code/air_casawvr/src/slice.cpp',
                   'casa-source/code/air_casawvr/src/basicphys.cpp', 'casa-source/code/air_casawvr/src/apps/antennautils.cpp',
                   'casa-source/code/air_casawvr/src/dtdltools.cpp', 'casa-source/code/air_casawvr/casawvr/msantdata.cpp',
                   'casa-source/code/air_casawvr/src/layers.cpp', 'casa-source/code/air_casawvr/src/columns_data.cpp',
                   'casa-source/code/air_casawvr/src/partitionsum.cpp', 'casa-source/code/air_casawvr/src/partitionsum_testdata.cpp',
                   'casa-source/code/air_casawvr/src/libair_main.cpp',

                   'casa-source/code/bnmin1/src/nestedsampler.cxx',
                   'casa-source/code/bnmin1/src/nestederr.cxx', 'casa-source/code/bnmin1/src/priors.cxx',
                   'casa-source/code/bnmin1/src/minimmodel.cxx', 'casa-source/code/bnmin1/src/bnmin_main.cxx',
                   'casa-source/code/bnmin1/src/prior_sampler.cxx', 'casa-source/code/bnmin1/src/mcpoint.cxx',
                   'casa-source/code/bnmin1/src/markovchain.cxx', 'casa-source/code/bnmin1/src/metro_propose.cxx',
                   'casa-source/code/bnmin1/src/paramalgo.cxx', 'casa-source/code/bnmin1/src/minim.cxx',
                   'casa-source/code/bnmin1/src/nestedinitial.cxx',

                   'casa-source/code/air_casawvr/src/apps/almaabs.cpp',

                   'casa-source/code/synthesis/CalTables/NewCalTable.cc', 'casa-source/code/synthesis/CalTables/CTMainRecord.cc',
                   'casa-source/code/synthesis/CalTables/CTMainColumns.cc', 'casa-source/code/synthesis/CalTables/RIorAParray.cc',
                   'casa-source/code/synthesis/CalTables/CalHistRecord.cc', 'casa-source/code/msvis/MSVis/MSCalEnums.cc',
                   'casa-source/code/synthesis/CalTables/CTDesc.cc', 'casa-source/code/synthesis/CalTables/CTEnums.cc',
                   'casa-source/code/synthesis/CalTables/CalTable.cc', 'casa-source/code/synthesis/CalTables/CalDescRecord.cc',
                   'casa-source/code/synthesis/CalTables/CalMainRecord.cc', 'casa-source/code/synthesis/CalTables/CTColumns.cc',

                   'casa-source/casacore/casa/Exceptions/Error2.cc', 'casa-source/casacore/casa/Arrays/ArrayError.cc',
                   'casa-source/casacore/casa/Containers/Block.cc', 'casa-source/casacore/tables/Tables/ColumnDesc.cc',
                   'casa-source/casacore/tables/Tables/BaseColumn.cc', 'casa-source/casacore/measures/Measures/MDirection.cc',
                   'casa-source/casacore/measures/Measures/MFrequency.cc', 'casa-source/casacore/ms/MSOper/MSMetaData.cc',
                   'casa-source/casacore/measures/Measures/MCPosition.cc', 'casa-source/casacore/casa/Quanta/MVPosition.cc',
                   'casa-source/casacore/tables/Tables/TableRow.cc', 'casa-source/casacore/tables/Tables/TableError.cc',
                   'casa-source/casacore/tables/Tables/TableProxy.cc', 'casa-source/casacore/tables/Tables/TableTrace.cc',
                   'casa-source/casacore/casa/BasicSL/String.cc', 'casa-source/casacore/tables/TaQL/TaQLResult.cc',
                   'casa-source/casacore/casa/System/AipsrcValue2.cc', 'casa-source/casacore/tables/Tables/ArrayColumn_tmpl.cc',
                   'casa-source/casacore/tables/DataMan/DataManager.cc', 'casa-source/casacore/casa/Quanta/MVDirection.cc',
                   'casa-source/casacore/tables/Tables/PlainTable.cc', 'casa-source/casacore/tables/Tables/ColumnCache.cc',
                   'casa-source/casacore/tables/Tables/TableCache.cc', 'casa-source/casacore/casa/Quanta/MVFrequency.cc',
                   'casa-source/casacore/casa/OS/Mutex.cc', 'casa-source/casacore/casa/OS/MemoryTrace.cc',
                   'casa-source/casacore/tables/Tables/PlainColumn.cc', 'casa-source/casacore/casa/Utilities/RegSequence.cc',
                   'casa-source/casacore/tables/DataMan/StManAipsIO.cc', 'casa-source/casacore/tables/Tables/TableColumn.cc',
                   'casa-source/casacore/tables/Tables/TableRecord.cc', 'casa-source/casacore/casa/Containers/ValueHolder.cc',
                   'casa-source/casacore/tables/DataMan/BitFlagsEngine.cc', 'casa-source/casacore/tables/Tables/ConcatColumn.cc',
                   'casa-source/casacore/casa/Utilities/Notice.cc', 'casa-source/casacore/tables/Tables/ScalarColumn_tmpl.cc',
                   'casa-source/casacore/tables/TaQL/ExprNode.cc', 'casa-source/casacore/tables/Tables/BaseColDesc.cc',
                   'casa-source/casacore/tables/Tables/ConcatTable.cc', 'casa-source/casacore/tables/DataMan/StManColumn.cc',
                   'casa-source/casacore/tables/Tables/ConcatRows.cc', 'casa-source/casacore/casa/Utilities/Copy2.cc',
                   'casa-source/casacore/tables/DataMan/DataManError.cc', 'casa-source/casacore/measures/Measures/MConvertBase.cc',
                   'casa-source/casacore/casa/Containers/RecordInterface.cc', 'casa-source/casacore/tables/Tables/SubTabDesc.cc',
                   'casa-source/casacore/tables/TaQL/TableParse.cc', 'casa-source/casacore/tables/Tables/ColDescSet.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSObservation.cc', 'casa-source/casacore/casa/Arrays/Array2Math.cc',
                   'casa-source/casacore/casa/Containers/RecordDescRep.cc', 'casa-source/casacore/tables/Tables/TableLockData.cc',
                   'casa-source/casacore/tables/Tables/TableSyncData.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSFieldColumns.cc', 'casa-source/casacore/casa/Logging/LogOrigin.cc',
                   'casa-source/casacore/tables/DataMan/StArrayFile.cc', 'casa-source/casacore/scimath/StatsFramework/StatisticsData.cc',
                   'casa-source/casacore/tables/Tables/TableRecordRep.cc', 'casa-source/casacore/casa/OS/Conversion.cc',
                   'casa-source/casacore/casa/Containers/RecordDesc.cc', 'casa-source/casacore/casa/IO/CanonicalIO.cc',
                   'casa-source/casacore/casa/OS/RegularFile.cc', 'casa-source/casacore/tables/Tables/TableKeyword.cc',
                   'casa-source/casacore/casa/IO/LECanonicalIO.cc', 'casa-source/casacore/measures/Measures/MeasureHolder.cc',
                   'casa-source/casacore/casa/System/ProgressMeter.cc', 'casa-source/casacore/tables/Tables/SetupNewTab.cc',
                   'casa-source/casacore/tables/DataMan/StandardStMan.cc', 'casa-source/casacore/tables/Tables/StorageOption.cc',
                   'casa-source/casacore/tables/Tables/TableIter.cc', 'casa-source/casacore/ms/MeasurementSets/MeasurementSet.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSPointing.cc', 'casa-source/casacore/casa/System/AipsrcBool.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSProcessor.cc', 'casa-source/casacore/ms/MeasurementSets/MSFreqOffset.cc',
                   'casa-source/casacore/measures/Measures/MEarthMagnetic.cc', 'casa-source/casacore/ms/MeasurementSets/MSPolarization.cc',
                   'casa-source/casacore/casa/Containers/ValueHolderRep.cc', 'casa-source/casacore/tables/Tables/ArrColDesc_tmpl.cc',
                   'casa-source/casacore/ms/MSSel/MSSelection.cc', 'casa-source/casacore/ms/MSOper/MSKeys.cc',
                   'casa-source/casacore/tables/DataMan/CompressFloat.cc', 'casa-source/casacore/casa/Quanta/QuantumHolder.cc',
                   'casa-source/casacore/casa/IO/RegularFileIO.cc', 'casa-source/casacore/casa/Utilities/StringDistance.cc',
                   'casa-source/casacore/tables/DataMan/TiledDataStMan.cc',
                   'casa-source/casacore/casa/Arrays/ArrayUtil2.cc', 'casa-source/casacore/tables/DataMan/CompressComplex.cc',
                   'casa-source/casacore/measures/Measures/MRadialVelocity.cc',
                   'casa-source/casacore/ms/MSOper/MSDerivedValues.cc', 'casa-source/casacore/casa/Quanta/MVEarthMagnetic.cc',
                   'casa-source/casacore/casa/Logging/LogMessage.cc', 'casa-source/casacore/ms/MSSel/MSSpwParse.cc',
                   'casa-source/casacore/tables/TaQL/RecordGram.cc', 'casa-source/casacore/tables/DataMan/TiledStMan.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSColumns.cc', 'casa-source/casacore/casa/Utilities/DataType.cc',
                   'casa-source/casacore/ms/MSSel/MSStateParse.cc', 'casa-source/casacore/ms/MeasurementSets/MSDopplerUtil.cc',
                   'casa-source/casacore/ms/MSSel/MSAntennaParse.cc', 'casa-source/casacore/tables/DataMan/TiledCellStMan.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSMainColumns.cc', 'casa-source/casacore/measures/Measures/MCDirection.cc',
                   'casa-source/casacore/ms/MSSel/MSFeedParse.cc', 'casa-source/casacore/ms/MSSel/MSSelectableTable.cc',
                   'casa-source/casacore/tables/DataMan/TSMCubeBuff.cc', 'casa-source/casacore/ms/MeasurementSets/MSFeedColumns.cc',
                   'casa-source/casacore/ms/MSSel/MSSourceIndex.cc', 'casa-source/casacore/ms/MSSel/MSAntennaIndex.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSStateColumns.cc', 'casa-source/casacore/ms/MeasurementSets/MSSourceColumns.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSSysCalColumns.cc', 'casa-source/casacore/casa/Containers/Record2Interface.cc',
                   'casa-source/casacore/tables/TaQL/TaQLNodeHandler.cc', 'casa-source/casacore/casa/IO/BucketBase.cc',
                   'casa-source/casacore/tables/DataMan/TSMCubeMMap.cc',
                   'casa-source/casacore/ms/MSSel/MSTableIndex.cc', 'casa-source/casacore/measures/TableMeasures/TableMeasColumn.cc',
                   'casa-source/casacore/casa/IO/BucketMapped.cc', 'casa-source/casacore/tables/Tables/ColumnsIndex.cc',
                   'casa-source/casacore/tables/TaQL/TaQLNode.cc', 'casa-source/casacore/casa/IO/BucketBuffered.cc',
                   'casa-source/casacore/tables/TaQL/RecordExpr.cc', 'casa-source/casacore/tables/TaQL/TaQLNodeVisitor.cc',
                   'casa-source/casacore/tables/TaQL/ExprLogicNode.cc', 'casa-source/casacore/tables/DataMan/TiledShapeStMan.cc',
                   'casa-source/casacore/measures/Measures/VelocityMachine.cc', 'casa-source/casacore/tables/DataMan/IncrementalStMan.cc',
                   'casa-source/casacore/measures/Measures/MCFrequency.cc', 'casa-source/casacore/tables/Tables/TableLocker.cc',
                   'casa-source/casacore/tables/TaQL/TaQLNodeDer.cc', 'casa-source/casacore/tables/TaQL/ExprRange.cc',
                   'casa-source/casacore/measures/Measures/Aberration.cc', 'casa-source/casacore/tables/TaQL/TaQLNodeRep.cc',
                   'casa-source/casacore/casa/Arrays/Array2.cc', 'casa-source/casacore/measures/Measures/MCRadialVelocity.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSAntennaColumns.cc', 'casa-source/casacore/ms/MeasurementSets/MSDopplerColumns.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSFlagCmdColumns.cc', 'casa-source/casacore/ms/MeasurementSets/MSHistoryColumns.cc',
                   'casa-source/casacore/ms/MSSel/MSSelectionError.cc', 'casa-source/casacore/ms/MeasurementSets/MSSpectralWindow.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSWeatherColumns.cc', 'casa-source/casacore/casa/Quanta/MVRadialVelocity.cc',
                   'casa-source/casacore/tables/Tables/RefRows.cc', 'casa-source/casacore/tables/Tables/ScaColDesc_tmpl.cc',
                   'casa-source/casacore/tables/TaQL/ExprMathNode.cc', 'casa-source/casacore/tables/TaQL/ExprNodeRep.cc',
                   'casa-source/casacore/tables/TaQL/MArrayBase.cc', 'casa-source/casacore/tables/TaQL/ExprNodeSet.cc',
                   'casa-source/casacore/tables/TaQL/ExprUDFNode.cc', 'casa-source/casacore/measures/TableMeasures/TableQuantumDesc.cc',
                   'casa-source/casacore/tables/DataMan/TiledColumnStMan.cc',
                   'casa-source/casacore/casa/Containers/Allocator.cc',
                   'casa-source/casacore/ms/MSSel/MSSelectionTools.cc', 'casa-source/casacore/casa/Arrays/ArrayBase.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSDataDescColumns.cc', 'casa-source/casacore/ms/MeasurementSets/MSSpWindowColumns.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSPointingColumns.cc', 'casa-source/casacore/ms/MeasurementSets/MSDataDescription.cc',
                   'casa-source/casacore/tables/DataMan/DataManAccessor.cc', 'casa-source/casacore/tables/TaQL/TaQLNodeResult.cc',
                   'casa-source/casacore/tables/TaQL/ExprAggrNode.cc', 'casa-source/casacore/tables/TaQL/ExprConeNode.cc',
                   'casa-source/casacore/tables/TaQL/ExprFuncNode.cc', 'casa-source/casacore/tables/TaQL/ExprUnitNode.cc',
                   'casa-source/casacore/tables/TaQL/ExprGroupAggrFunc.cc',
                   'casa-source/casacore/measures/TableMeasures/TableMeasDescBase.cc', 'casa-source/casacore/tables/TaQL/ExprGroup.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSProcessorColumns.cc', 'casa-source/casacore/tables/TaQL/ExprNodeArray.cc',
                   'casa-source/casacore/measures/TableMeasures/TableMeasType.cc', 'casa-source/casacore/tables/TaQL/ExprDerNode.cc',
                   'casa-source/casacore/tables/TaQL/TableGram.cc', 'casa-source/casacore/tables/DataMan/VirtualTaQLColumn.cc',
                   'casa-source/casacore/measures/TableMeasures/TableMeasValueDesc.cc', 'casa-source/casacore/ms/MSSel/MSSpwGram.cc',
                   'casa-source/casacore/tables/DataMan/ISMColumn.cc', 'casa-source/casacore/ms/MSSel/MSSpwIndex.cc',
                   'casa-source/casacore/casa/OS/CanonicalConversion.cc', 'casa-source/casacore/casa/OS/EnvVar.cc',
                   'casa-source/casacore/tables/DataMan/ForwardCol.cc', 'casa-source/casacore/ms/MeasurementSets/MSFreqOffColumns.cc',
                   'casa-source/casacore/casa/Utilities/RecordTransformable.cc', 'casa-source/casacore/measures/TableMeasures/TableMeasRefDesc.cc',
                   'casa-source/casacore/tables/DataMan/VirtColEng.cc', 'casa-source/casacore/casa/BasicSL/Constants.cc',
                   'casa-source/casacore/measures/TableMeasures/TableMeasOffsetDesc.cc', 'casa-source/casacore/ms/MeasurementSets/MSObsColumns.cc',
                   'casa-source/casacore/tables/TaQL/ExprLogicNodeArray.cc', 'casa-source/casacore/casa/Arrays/ArrayPosIter.cc',
                   'casa-source/casacore/ms/MSSel/MSTimeGram.cc', 'casa-source/casacore/ms/MSSel/MSTimeParse.cc',
                   'casa-source/casacore/ms/MSSel/MSStateGram.cc', 'casa-source/casacore/ms/MSSel/MSStateIndex.cc',
                   'casa-source/casacore/measures/Measures/MCDoppler.cc',
                   'casa-source/casacore/casa/OS/LECanonicalDataConversion.cc', 'casa-source/casacore/casa/OS/DataConversion.cc',
                   'casa-source/casacore/casa/OS/LECanonicalConversion.cc', 'casa-source/casacore/ms/MeasurementSets/MSPolColumns.cc',
                   'casa-source/casacore/tables/TaQL/ExprMathNodeArray.cc', 'casa-source/casacore/ms/MSSel/MSUvDistGram.cc',
                   'casa-source/casacore/ms/MSSel/MSUvDistParse.cc', 'casa-source/casacore/tables/TaQL/ExprUDFNodeArray.cc',
                   'casa-source/casacore/tables/Tables/ScaRecordColDesc.cc', 'casa-source/casacore/tables/TaQL/ExprFuncNodeArray.cc',
                   'casa-source/casacore/casa/Arrays/ArrayPartMath.cc', 'casa-source/casacore/tables/Tables/ScaRecordColData.cc',
                   'casa-source/casacore/tables/DataMan/StArrAipsIO.cc', 'casa-source/casacore/tables/TaQL/ExprAggrNodeArray.cc',
                   'casa-source/casacore/tables/TaQL/ExprGroupAggrFuncArray.cc', 'casa-source/casacore/ms/MSSel/MSFeedGram.cc',
                   'casa-source/casacore/ms/MSSel/MSPolnGram.cc', 'casa-source/casacore/ms/MSSel/MSFeedIndex.cc',
                   'casa-source/casacore/ms/MSSel/MSPolnParse.cc', 'casa-source/casacore/ms/MSSel/MSScanGram.cc',
                   'casa-source/casacore/scimath/StatsFramework/ClassicalStatisticsData.cc', 'casa-source/casacore/ms/MSSel/MSCorrGram.cc',
                   'casa-source/casacore/tables/TaQL/ExprDerNodeArray.cc', 'casa-source/casacore/ms/MSSel/MSCorrParse.cc',
                   'casa-source/casacore/ms/MSSel/MSScanParse.cc', 'casa-source/casacore/ms/MSSel/MSDataDescIndex.cc',
                   'casa-source/casacore/tables/DataMan/StIndArrAIO.cc', 'casa-source/casacore/casa/Quanta/UnitVal.cc',
                   'casa-source/casacore/derivedmscal/DerivedMC/UDFMSCal.cc', 'casa-source/casacore/tables/DataMan/StIndArray.cc',
                   'casa-source/casacore/derivedmscal/DerivedMC/MSCalEngine.cc', 'casa-source/casacore/ms/MSSel/MSPolIndex.cc',
                   'casa-source/casacore/measures/Measures/MCBaseline.cc', 'casa-source/casacore/casa/Quanta/MVBaseline.cc',
                   'casa-source/casacore/ms/MeasurementSets/StokesConverter.cc', 'casa-source/casacore/ms/MSSel/MSSelectionErrorHandler.cc',
                   'casa-source/casacore/scimath/Mathematics/SquareMatrix2.cc', 'casa-source/casacore/ms/MSSel/MSArrayGram.cc',
                   'casa-source/casacore/casa/Containers/Map2.cc', 'casa-source/casacore/ms/MSSel/MSArrayParse.cc',
                   'casa-source/casacore/ms/MSSel/MSFieldGram.cc', 'casa-source/casacore/ms/MSSel/MSAntennaGram.cc',
                   'casa-source/casacore/tables/TaQL/ExprNodeRecord.cc', 'casa-source/casacore/ms/MSSel/MSFieldIndex.cc',
                   'casa-source/casacore/ms/MSSel/MSFieldParse.cc', 'casa-source/casacore/casa/OS/DOos.cc',
                   'casa-source/casacore/casa/OS/DirectoryIterator.cc', 'casa-source/casacore/ms/MSSel/MSObservationGram.cc',
                   'casa-source/casacore/ms/MSSel/MSObservationParse.cc', 'casa-source/casacore/casa/Utilities/CountedPtr2.cc',
                   'casa-source/casacore/casa/OS/OMP.cc', 'casa-source/casacore/casa/BasicMath/Random.cc',
                   'casa-source/casacore/measures/Measures/Muvw.cc', 'casa-source/casacore/casa/OS/Path.cc',
                   'casa-source/casacore/casa/Utilities/Sort.cc', 'casa-source/casacore/casa/OS/Time.cc',
                   'casa-source/casacore/casa/Quanta/Unit.cc', 'casa-source/casacore/casa/Utilities/SortError.cc',
                   'casa-source/casacore/casa/BasicMath/Math.cc', 'casa-source/casacore/casa/BasicSL/Complex.cc',
                   'casa-source/casacore/casa/Arrays/Matrix2Math.cc', 'casa-source/casacore/casa/Arrays/Array_tmpl.cc',
                   'casa-source/casacore/measures/TableMeasures/TableMeas_tmpl.cc', 'casa-source/casacore/casa/Containers/Block_tmpl.cc',
                   'casa-source/casacore/casa/Quanta/Euler.cc', 'casa-source/casacore/casa/Logging/LogIO.cc',
                   'casa-source/casacore/casa/Quanta/MVuvw.cc', 'casa-source/casacore/measures/Measures/MCuvw.cc',
                   'casa-source/casacore/casa/Quanta/QBase.cc', 'casa-source/casacore/casa/Utilities/Regex.cc',
                   'casa-source/casacore/tables/Tables/ReadAsciiTable.cc', 'casa-source/casacore/casa/Arrays/Slice.cc',
                   'casa-source/casacore/tables/Tables/Table.cc', 'casa-source/casacore/tables/Tables/MemoryTable.cc',
                   'casa-source/casacore/casa/IO/AipsIO.cc', 'casa-source/casacore/tables/DataMan/MemoryStMan.cc',
                   'casa-source/casacore/casa/OS/File.cc', 'casa-source/casacore/casa/System/Aipsrc.cc',
                   'casa-source/casacore/measures/Measures/MCBase.cc', 'casa-source/casacore/casa/OS/Timer.cc',
                   'casa-source/casacore/casa/IO/ByteIO.cc', 'casa-source/casacore/casa/OS/DynLib.cc',
                   'casa-source/casacore/measures/Measures/MEpoch.cc', 'casa-source/casacore/ms/MeasurementSets/MSFeed.cc',
                   'casa-source/casacore/measures/Measures/MRBase.cc', 'casa-source/casacore/casa/Quanta/MVTime.cc',
                   'casa-source/casacore/casa/Arrays/Matrix_tmpl.cc', 'casa-source/casacore/casa/Containers/Record.cc',
                   'casa-source/casacore/casa/Containers/Record2.cc', 'casa-source/casacore/casa/Arrays/Slicer.cc',
                   'casa-source/casacore/casa/IO/TypeIO.cc',
                   'casa-source/casacore/measures/Measures/Stokes.cc', 'casa-source/casacore/casa/Arrays/Vector_tmpl.cc',
                   'casa-source/casacore/tables/DataMan/ISMBase.cc', 'casa-source/casacore/casa/Logging/LogSink.cc',
                   'casa-source/casacore/casa/IO/BucketFile.cc', 'casa-source/casacore/casa/IO/BucketCache.cc',
                   'casa-source/casacore/casa/Logging/NullLogSink.cc', 'casa-source/casacore/tables/DataMan/ISMIndColumn.cc',
                   'casa-source/casacore/casa/Logging/MemoryLogSink.cc', 'casa-source/casacore/casa/IO/MultiFileBase.cc',
                   'casa-source/casacore/casa/Logging/StreamLogSink.cc', 'casa-source/casacore/casa/Logging/LogSinkInterface.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSField.cc', 'casa-source/casacore/measures/Measures/MCEpoch.cc',
                   'casa-source/casacore/tables/DataMan/MSMBase.cc',  'casa-source/casacore/ms/MSSel/MSParse.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSState.cc', 'casa-source/casacore/tables/DataMan/MSMDirColumn.cc',
                   'casa-source/casacore/tables/DataMan/MSMIndColumn.cc', 'casa-source/casacore/ms/MeasurementSets/MSTable.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSTable2.cc', 'casa-source/casacore/ms/MeasurementSets/MSTableImpl.cc',
                   'casa-source/casacore/casa/Quanta/MVAngle.cc', 'casa-source/casacore/casa/Quanta/MVEpoch.cc',
                   'casa-source/casacore/casa/System/AppInfo.cc', 'casa-source/casacore/casa/System/AipsrcVString.cc',
                   'casa-source/casacore/casa/System/AipsrcVBool.cc',
                   'casa-source/casacore/measures/Measures/Measure.cc', 'casa-source/casacore/casa/Quanta/Quantum2.cc',
                   'casa-source/casacore/tables/DataMan/SSMBase.cc', 'casa-source/casacore/tables/DataMan/SSMDirColumn.cc',
                   'casa-source/casacore/tables/DataMan/SSMStringHandler.cc', 'casa-source/casacore/tables/DataMan/SSMIndColumn.cc',
                   'casa-source/casacore/casa/OS/SymLink.cc', 'casa-source/casacore/tables/DataMan/TSMCube.cc',
                   'casa-source/casacore/tables/DataMan/SSMIndStringColumn.cc', 'casa-source/casacore/tables/DataMan/TSMFile.cc',
                   'casa-source/casacore/tables/TaQL/UDFBase.cc', 'casa-source/casacore/casa/Quanta/UnitDim.cc',
                   'casa-source/casacore/casa/Quanta/UnitMap.cc', 'casa-source/casacore/casa/Quanta/UnitMap2.cc',
                   'casa-source/casacore/casa/Quanta/UnitMap5.cc', 'casa-source/casacore/casa/Quanta/UnitMap6.cc',
                   'casa-source/casacore/casa/Quanta/UnitMap7.cc', 'casa-source/casacore/casa/Quanta/UnitMap3.cc',
                   'casa-source/casacore/casa/Quanta/UnitMap4.cc', 'casa-source/casacore/casa/Utilities/ValType.cc',
                   'casa-source/casacore/casa/OS/HostInfo.cc', 'casa-source/casacore/tables/DataMan/ISMIndex.cc',
                   'casa-source/casacore/casa/IO/LockFile.cc', 'casa-source/casacore/measures/Measures/MDoppler.cc',
                   'casa-source/casacore/casa/IO/MFFileIO.cc', 'casa-source/casacore/casa/IO/MMapfdIO.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSSource.cc', 'casa-source/casacore/ms/MeasurementSets/MSSysCal.cc',
                   'casa-source/casacore/casa/Utilities/MUString.cc', 'casa-source/casacore/casa/IO/FileLocker.cc',
                   'casa-source/casacore/measures/Measures/MeasData.cc', 'casa-source/casacore/measures/Measures/MeasMath.cc',
                   'casa-source/casacore/measures/Measures/Precession.cc', 'casa-source/casacore/casa/IO/MemoryIO.cc',
                   'casa-source/casacore/measures/Measures/Nutation.cc', 'casa-source/casacore/casa/System/ObjectID.cc',
                   'casa-source/casacore/tables/Tables/RefTable.cc', 'casa-source/casacore/tables/DataMan/SSMIndex.cc',
                   'casa-source/casacore/measures/Measures/SolarPos.cc', 'casa-source/casacore/tables/DataMan/TSMShape.cc',
                   'casa-source/casacore/casa/Quanta/UnitName.cc', 'casa-source/casacore/tables/Tables/BaseTable.cc',
                   'casa-source/casacore/tables/Tables/BaseTabIter.cc', 'casa-source/casacore/tables/TaQL/TaQLShow.cc',
                   'casa-source/casacore/tables/Tables/ColumnSet.cc', 'casa-source/casacore/casa/OS/Directory.cc',
                   'casa-source/casacore/casa/IO/FilebufIO.cc', 'casa-source/casacore/casa/Arrays/IPosition.cc',
                   'casa-source/casacore/casa/Arrays/IPosition2.cc', 'casa-source/casacore/tables/DataMan/ISMBucket.cc',
                   'casa-source/casacore/casa/Logging/LogFilter.cc',
                   'casa-source/casacore/casa/Logging/LogFilterInterface.cc',
                   'casa-source/casacore/casa/IO/FiledesIO.cc', 'casa-source/casacore/measures/Measures/MBaseline.cc',
                   'casa-source/casacore/measures/Measures/MPosition.cc', 'casa-source/casacore/ms/MeasurementSets/MSAntenna.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSDoppler.cc', 'casa-source/casacore/ms/MeasurementSets/MSFlagCmd.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSHistory.cc', 'casa-source/casacore/tables/DataMan/MSMColumn.cc',
                   'casa-source/casacore/ms/MeasurementSets/MSWeather.cc', 'casa-source/casacore/casa/Quanta/MVDoppler.cc',
                   'casa-source/casacore/measures/Measures/MeasFrame.cc', 'casa-source/casacore/measures/Measures/MeasTable.cc',
                   'casa-source/casacore/measures/Measures/MeasTableMul.cc', 'casa-source/casacore/measures/Measures/MCFrame.cc',
                   'casa-source/casacore/measures/Measures/MeasIERS.cc', 'casa-source/casacore/measures/Measures/MeasComet.cc',
                   'casa-source/casacore/casa/Quanta/MeasValue.cc', 'casa-source/casacore/casa/IO/MultiFile.cc',
                   'casa-source/casacore/casa/Quanta/QLogical2.cc', 'casa-source/casacore/casa/Containers/RecordRep.cc',
                   'casa-source/casacore/casa/Quanta/RotMatrix.cc', 'casa-source/casacore/tables/DataMan/SSMColumn.cc',
                   'casa-source/casacore/casa/System/AppState.cc', 'casa-source/casacore/measures/Measures/MeasJPL.cc',
                   'casa-source/casacore/tables/DataMan/TSMColumn.cc', 'casa-source/casacore/tables/DataMan/TSMIdColumn.cc',
                   'casa-source/casacore/tables/DataMan/TSMDataColumn.cc', 'casa-source/casacore/tables/DataMan/TSMCoordColumn.cc',
                   'casa-source/casacore/casa/IO/MultiHDF5.cc', 'casa-source/casacore/tables/Tables/NullTable.cc',
                   'casa-source/casacore/tables/Tables/RefColumn.cc', 'casa-source/casacore/casa/BasicSL/RegexBase.cc',
                   'casa-source/casacore/tables/DataMan/TSMOption.cc', 'casa-source/casacore/tables/TaQL/TaQLStyle.cc',
                   'casa-source/casacore/tables/Tables/TableAttr.cc', 'casa-source/casacore/casa/HDF5/HDF5Object.cc',
                   'casa-source/casacore/casa/HDF5/HDF5Record.cc', 'casa-source/casacore/casa/HDF5/HDF5DataSet.cc',
                   'casa-source/casacore/casa/HDF5/HDF5File.cc', 'casa-source/casacore/casa/HDF5/HDF5Group.cc',
                   'casa-source/casacore/tables/Tables/TableCopy.cc', 'casa-source/casacore/tables/Tables/TableDesc.cc',
                   'casa-source/casacore/casa/HDF5/HDF5DataType.cc', 'casa-source/casacore/tables/DataMan/DataManInfo.cc',
                   'casa-source/casacore/casa/HDF5/HDF5HidMeta.cc', 'casa-source/casacore/tables/Tables/TableInfo.cc',
                   'casa-source/casacore/casa/HDF5/HDF5Error.cc', 'casa-source/casacore/tables/Tables/TableLock.cc',
                   'casa-source/casacore/tables/Tables/TabPath.cc', 'casa-source/casacore/ms/MSSel/MSSSpwErrorHandler.cc',
                   'casa-source/casacore/casa/Utilities/cregex.cc',
                   'casa-source/casacore/casa/aips.cc',
                   'generated/source/version.cc' ]

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
                       'generated/':     ['-DAIPS_64B', '-DAIPS_AUTO_STL', '-DAIPS_DEBUG', '-DAIPS_HAS_QWT', \
                                          '-DAIPS_LINUX', '-DAIPS_LITTLE_ENDIAN', '-DAIPS_STDLIB', \
                                          '-DCASACORE_NEEDS_RETHROW', '-DCASA_USECASAPATH', '-DDBUS_CPP', '-DQWT6', \
                                          '-DUseCasacoreNamespace', '-D_FILE_OFFSET_BITS=64', '-D_LARGEFILE_SOURCE', \
                                          '-DNO_CRASH_REPORTER', '-fno-omit-frame-pointer', '-DWITHOUT_ACS', '-DWITHOUT_BOOST',
                                          '-DCASATOOLS' ] + platform_cflags[sys.platform] }

xml_xlate = { 'casa-source/gcwrap/tasks/wvrgcal.xml': 'xml/wvrgcal.xml' }
xml_files = [ 'xml/wvrgcal.xml' ]
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
    ld_dirs = list(set(map(lambda s: s[2:],filter(lambda s: s.startswith("-L"),ldflags))))
    if 'build.python.numpy_dir' in tools_config and len(tools_config['build.python.numpy_dir']) > 0:
        cflags.insert(0,'-I' + tools_config['build.python.numpy_dir'])       ### OS could have different version of python in
                                                                      ###     /usr/include (e.g. rhel6)
    new_compiler_cxx = ccache + [tools_config['build.compiler.cxx'], '-g', '-std=c++11','-Ibinding/include','-Igenerated/include','-Ilibcasatools/generated/include','-Icasa-source/code','-Icasa-source','-Icasa-source/casacore', '-Iinclude', '-Isakura-source/src'] + cflags + default_compiler_so[1:]
    new_compiler_cc = ccache + [tools_config['build.compiler.cc'], '-g', '-Ibinding/include','-Igenerated/include','-Ilibcasatools/generated/include','-Icasa-source/code','-Icasa-source','-Icasa-source/casacore', '-Iinclude', 'sakura-source/src'] + cflags + default_compiler_so[1:]
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

        superld( target_desc, objects, output_filename, output_dir,
                 None if libraries is None else [library_mangle[l] if l in library_mangle else l for l in libraries],
                 ld_dirs if library_dirs is None else ["-L/tmp"]+ld_dirs+library_dirs+local_library_path, runtime_library_dirs, export_symbols,
#                 debug, ["-L/opt/local/lib"], extra_postargs, build_temp, target_lang )
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
    version_info = os.popen("cd casa-source && code/install/resolvegitrevision.sh --pretty-print").read( ).splitlines( )
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

    with open('casa-source/code/stdcasa/version.cc.in') as infile, open(file, 'w') as outfile:
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

if __name__ == '__main__':
    generate_version_file("generated/source/version.cc")
    generate_lex(CASACORE_LEX)
    generate_yacc(CASACORE_YACC)
    tmpdir = os.path.join('build', distutils_dir_name('temp'))
    moduledir = os.path.join('build', distutils_dir_name('lib'), module_name)
    privatedir = os.path.join(moduledir,"private")
    bindir = os.path.join(privatedir, "bin")
    libdir = os.path.join(privatedir, "lib")
    mkpath(bindir)
    cc = new_compiler("posix", verbose=True)
    customize_compiler(cc,True)
    objs = cc.compile( CASAWVR_SOURCE, os.path.join(tmpdir,"wvrgcal") )
    if sys.platform == 'darwin':
        ### need to get '/opt/local/lib/gcc5' from gfortran directly
        rpath = [ '-Wl,-rpath,@loader_path/../lib' ]
        archflags = ['-L/opt/local/lib/gcc5']
    else:
        rpath = [ '-Wl,-rpath,$ORIGIN/../lib']
        archflags = [ ]

    cc.link( CCompiler.EXECUTABLE, objs, os.path.join(bindir,"wvrgcal"), libraries=["boost_program_options-mt", "lapack", "blas", "pthread", "dl"], extra_preargs=props['build.flags.link.openmp'] + rpath + props['build.flags.link.gsl'] + archflags )
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

    for f in private_scripts:
        copy2(f,privatedir)

    for m in private_modules:
        tgt = os.path.join(privatedir,os.path.basename(m))
        copy_tree(m,tgt)

