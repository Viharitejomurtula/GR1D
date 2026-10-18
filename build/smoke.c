/* Main Simulation File */

#if defined(__cplusplus)
extern "C" {
#endif

#include "smoke_model.h"
#include "simulation/solver/events.h"
#include "simulation/arrayIndex.h"

/* FIXME these defines are ugly and hard to read, why not use direct function pointers instead? */
#define prefixedName_performSimulation smoke_performSimulation
#define prefixedName_updateContinuousSystem smoke_updateContinuousSystem
#include <simulation/solver/perform_simulation.c.inc>

#define prefixedName_performQSSSimulation smoke_performQSSSimulation
#include <simulation/solver/perform_qss_simulation.c.inc>


/* dummy VARINFO and FILEINFO */
const VAR_INFO dummyVAR_INFO = omc_dummyVarInfo;

int smoke_input_function(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int smoke_input_function_init(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int smoke_input_function_updateStartValues(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int smoke_inputNames(DATA *data, char ** names){
  
  return 0;
}

int smoke_data_function(DATA *data, threadData_t *threadData)
{
  return 0;
}

int smoke_dataReconciliationInputNames(DATA *data, char ** names){
  
  return 0;
}

int smoke_dataReconciliationUnmeasuredVariables(DATA *data, char ** names)
{
  
  return 0;
}

int smoke_output_function(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int smoke_setc_function(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int smoke_setb_function(DATA *data, threadData_t *threadData)
{
  
  return 0;
}


/*
equation index: 13
type: SIMPLE_ASSIGN
ocv_V = ocv_empty_V + (ocv_full_V - ocv_empty_V) * soc
*/
void smoke_eqFunction_13(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,13};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* ocv_V variable */) = (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[2]] /* ocv_empty_V PARAM */) + ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[3]] /* ocv_full_V PARAM */) - (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[2]] /* ocv_empty_V PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* soc STATE(1) */));
  threadData->lastEquationSolved = 13;
}

void smoke_eqFunction_14(DATA*, threadData_t*);
void smoke_eqFunction_15(DATA*, threadData_t*);
void smoke_eqFunction_16(DATA*, threadData_t*);
void smoke_eqFunction_17(DATA*, threadData_t*);
/*
equation index: 18
indexNonlinear: 1
type: NONLINEAR

vars: {terminal_V}
eqns: {14, 15, 16, 17}
*/
void smoke_eqFunction_18(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,18};
  int retValue;
  infoStreamPrint(OMC_LOG_DT, 0, "Solving nonlinear system 18 (STRICT TEARING SET if tearing enabled) at time = %18.10e", data->localData[0]->timeValue);
  /* get old value */
  data->simulationInfo->nonlinearSystemData[1].nlsxOld[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */);
  retValue = solve_nonlinear_system(data, threadData, 1);
  /* check if solution process was successful */
  if (retValue > 0){
    const int indexes[2] = {1,18};
    throwStreamPrintWithEquationIndexes(threadData, omc_dummyFileInfo, indexes, "Solving non-linear system 18 failed at time=%.15g.\nFor more information please use -lv LOG_NLS.", data->localData[0]->timeValue);
  }
  /* write solution */
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */) = data->simulationInfo->nonlinearSystemData[1].nlsx[0];
  threadData->lastEquationSolved = 18;
}

/*
equation index: 19
type: SIMPLE_ASSIGN
$DER.soc = (-2.777777777777778e-4) * current_A / capacity_Ah
*/
void smoke_eqFunction_19(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,19};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[1]] /* der(soc) STATE_DER */) = DIVISION_SIM((-2.777777777777778e-4) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* current_A variable */)),(data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[0]] /* capacity_Ah PARAM */),"capacity_Ah",equationIndexes);
  threadData->lastEquationSolved = 19;
}

OMC_DISABLE_OPT
int smoke_functionDAE(DATA *data, threadData_t *threadData)
{
  int equationIndexes[1] = {0};
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_tick(SIM_TIMER_DAE);
#endif

  data->simulationInfo->needToIterate = 0;
  data->simulationInfo->discreteCall = 1;
  smoke_functionLocalKnownVars(data, threadData);
  static void (*const eqFunctions[3])(DATA*, threadData_t*) = {
    smoke_eqFunction_13,
    smoke_eqFunction_18,
    smoke_eqFunction_19
  };
  
  for (int id = 0; id < 3; id++) {
    eqFunctions[id](data, threadData);
  }
  data->simulationInfo->discreteCall = 0;
  
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_accumulate(SIM_TIMER_DAE);
#endif
  return 0;
}


int smoke_functionLocalKnownVars(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

/* forwarded equations */
extern void smoke_eqFunction_13(DATA* data, threadData_t *threadData);
extern void smoke_eqFunction_18(DATA* data, threadData_t *threadData);
extern void smoke_eqFunction_19(DATA* data, threadData_t *threadData);

static void functionODE_system0(DATA *data, threadData_t *threadData)
{
  static void (*const eqFunctions[3])(DATA*, threadData_t*) = {
    smoke_eqFunction_13,
    smoke_eqFunction_18,
    smoke_eqFunction_19
  };
  
  if (data->simulationInfo->evalSelection) {
    for (int i = 0; i < data->simulationInfo->evalSelection->n; i++) {
      int id = data->simulationInfo->evalSelection->idx[i];
      eqFunctions[id](data, threadData);
    }
  } else {
    for (int id = 0; id < 3; id++) {
      eqFunctions[id](data, threadData);
    }
  }
}

int smoke_functionODE(DATA *data, threadData_t *threadData)
{
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_tick(SIM_TIMER_FUNCTION_ODE);
#endif

  
  data->simulationInfo->callStatistics.functionODE++;
  
  smoke_functionLocalKnownVars(data, threadData);
  functionODE_system0(data, threadData);

#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_accumulate(SIM_TIMER_FUNCTION_ODE);
#endif

  return 0;
}

void smoke_ODE_DAG(DATA* data, threadData_t* threadData)
{
  const size_t eqMap[] = {13, 18, 19};
  buildEvalDAG_ODE(data->modelData, sizeof(eqMap)/sizeof(size_t), eqMap);
}

/* forward the main in the simulation runtime */
extern int _main_SimulationRuntime(int argc, char **argv, DATA *data, threadData_t *threadData);
extern int _main_OptimizationRuntime(int argc, char **argv, DATA *data, threadData_t *threadData);

#include "smoke_12jac.h"
#include "smoke_13opt.h"

struct OpenModelicaGeneratedFunctionCallbacks smoke_callback = {
  (int (*)(DATA *, threadData_t *, void *)) smoke_performSimulation,    /* performSimulation */
  (int (*)(DATA *, threadData_t *, void *)) smoke_performQSSSimulation,    /* performQSSSimulation */
  smoke_updateContinuousSystem,    /* updateContinuousSystem */
  smoke_callExternalObjectDestructors,    /* callExternalObjectDestructors */
  smoke_initialNonLinearSystem,    /* initialNonLinearSystem */
  NULL,    /* initialLinearSystem */
  NULL,    /* initialMixedSystem */
  #if !defined(OMC_NO_STATESELECTION)
  smoke_initializeStateSets,
  #else
  NULL,
  #endif    /* initializeStateSets */
  smoke_initializeDAEmodeData,
  smoke_ODE_DAG,
  smoke_functionODE,
  smoke_functionAlgebraics,
  smoke_functionDAE,
  smoke_functionLocalKnownVars,
  smoke_input_function,
  smoke_input_function_init,
  smoke_input_function_updateStartValues,
  smoke_data_function,
  smoke_output_function,
  smoke_setc_function,
  smoke_setb_function,
  smoke_function_storeDelayed,
  smoke_function_storeSpatialDistribution,
  smoke_function_initSpatialDistribution,
  smoke_updateBoundVariableAttributes,
  smoke_functionInitialEquations,
  GLOBAL_EQUIDISTANT_HOMOTOPY,
  NULL,
  smoke_functionRemovedInitialEquations,
  smoke_updateBoundParameters,
  smoke_checkForAsserts,
  smoke_function_ZeroCrossingsEquations,
  smoke_function_ZeroCrossings,
  smoke_function_updateRelations,
  smoke_zeroCrossingDescription,
  smoke_relationDescription,
  smoke_function_initSample,
  smoke_INDEX_JAC_A,
  smoke_INDEX_JAC_ADJ,
  smoke_INDEX_JAC_B,
  smoke_INDEX_JAC_C,
  smoke_INDEX_JAC_D,
  smoke_INDEX_JAC_F,
  smoke_INDEX_JAC_H,
  smoke_initialAnalyticJacobianA,
  smoke_initialAnalyticJacobianADJ,
  smoke_initialAnalyticJacobianB,
  smoke_initialAnalyticJacobianC,
  smoke_initialAnalyticJacobianD,
  smoke_initialAnalyticJacobianF,
  smoke_initialAnalyticJacobianH,
  smoke_functionJacA_column,
  smoke_functionJacADJ_column,
  smoke_functionJacB_column,
  smoke_functionJacC_column,
  smoke_functionJacD_column,
  smoke_functionJacF_column,
  smoke_functionJacH_column,
  smoke_JacA_DAG,
  smoke_linear_model_frame,
  smoke_linear_model_datarecovery_frame,
  smoke_mayer,
  smoke_lagrange,
  smoke_getInputVarIndicesInOptimization,
  smoke_pickUpBoundsForInputsInOptimization,
  smoke_setInputData,
  smoke_getTimeGrid,
  smoke_symbolicInlineSystem,
  smoke_function_initSynchronous,
  smoke_function_updateSynchronous,
  smoke_function_equationsSynchronous,
  smoke_inputNames,
  smoke_dataReconciliationInputNames,
  smoke_dataReconciliationUnmeasuredVariables,
  NULL,
  NULL,
  NULL,
  NULL,
  -1,
  NULL,
  NULL,
  -1

};

#define _OMC_LIT_RESOURCE_0_name_data "ToolchainCheck"
#define _OMC_LIT_RESOURCE_0_dir_data "/work/model"
static const MMC_DEFSTRINGLIT(_OMC_LIT_RESOURCE_0_name,14,_OMC_LIT_RESOURCE_0_name_data);
static const MMC_DEFSTRINGLIT(_OMC_LIT_RESOURCE_0_dir,11,_OMC_LIT_RESOURCE_0_dir_data);

static const MMC_DEFSTRUCTLIT(_OMC_LIT_RESOURCES,2,MMC_ARRAY_TAG) {MMC_REFSTRINGLIT(_OMC_LIT_RESOURCE_0_name), MMC_REFSTRINGLIT(_OMC_LIT_RESOURCE_0_dir)}};
void smoke_setupDataStruc(DATA *data, threadData_t *threadData)
{
  assertStreamPrint(threadData,0!=data, "Error while initialize Data");
  threadData->localRoots[LOCAL_ROOT_SIMULATION_DATA] = data;
  data->callback = &smoke_callback;
  OpenModelica_updateUriMapping(threadData, MMC_REFSTRUCTLIT(_OMC_LIT_RESOURCES));
  data->modelData->modelName = "ToolchainCheck";
  data->modelData->modelFilePrefix = "smoke";
  data->modelData->modelFileName = "ToolchainCheck.mo";
  data->modelData->resultFileName = NULL;
  data->modelData->modelDir = "/work/model";
  data->modelData->modelGUID = "{cc2860ec-2fbd-4fce-a726-db6961c1e8d4}";
  #if defined(OPENMODELICA_XML_FROM_FILE_AT_RUNTIME)
  data->modelData->initXMLData = NULL;
  data->modelData->modelDataXml.infoXMLData = NULL;
  #else
  #if defined(_MSC_VER) /* handle joke compilers */
  {
  /* for MSVC we encode a string like char x[] = {'a', 'b', 'c', '\0'} */
  /* because the string constant limit is 65535 bytes */
  static const char contents_init[] =
    #include "smoke_init.c"
    ;
  static const char contents_info[] =
    #include "smoke_info.c"
    ;
    data->modelData->initXMLData = contents_init;
    data->modelData->modelDataXml.infoXMLData = contents_info;
  }
  #else /* handle real compilers */
  data->modelData->initXMLData =
  #include "smoke_init.c"
    ;
  data->modelData->modelDataXml.infoXMLData =
  #include "smoke_info.c"
    ;
  #endif /* defined(_MSC_VER) */
  #endif /* defined(OPENMODELICA_XML_FROM_FILE_AT_RUNTIME) */
  data->modelData->modelDataXml.fileName = "smoke_info.json";
  data->modelData->resourcesDir = NULL;
  data->modelData->runTestsuite = 0;
  data->modelData->nStatesArray = 1;
  data->modelData->nDiscreteReal = 0;
  data->modelData->nVariablesRealArray = 6;
  data->modelData->nVariablesIntegerArray = 0;
  data->modelData->nVariablesBooleanArray = 2;
  data->modelData->nVariablesStringArray = 0;
  data->modelData->nParametersRealArray = 7;
  data->modelData->nParametersIntegerArray = 0;
  data->modelData->nParametersBooleanArray = 0;
  data->modelData->nParametersStringArray = 0;
  data->modelData->nParametersReal = 7;
  data->modelData->nParametersInteger = 0;
  data->modelData->nParametersBoolean = 0;
  data->modelData->nParametersString = 0;
  data->modelData->nAliasRealArray = 0;
  data->modelData->nAliasIntegerArray = 0;
  data->modelData->nAliasBooleanArray = 0;
  data->modelData->nAliasStringArray = 0;
  data->modelData->nInputVars = 0;
  data->modelData->nOutputVars = 0;
  data->modelData->nZeroCrossings = 2;
  data->modelData->nSamples = 0;
  data->modelData->nRelations = 2;
  data->modelData->nMathEvents = 0;
  data->modelData->nExtObjs = 0;
  data->modelData->modelDataXml.modelInfoXmlLength = 0;
  data->modelData->modelDataXml.nFunctions = 0;
  data->modelData->modelDataXml.nProfileBlocks = 0;
  data->modelData->modelDataXml.nEquations = 22;
  data->modelData->nMixedSystems = 0;
  data->modelData->nLinearSystems = 0;
  data->modelData->nNonLinearSystems = 2;
  data->modelData->nStateSets = 0;
  data->modelData->nJacobians = 8;
  data->modelData->nOptimizeConstraints = 0;
  data->modelData->nOptimizeFinalConstraints = 0;
  data->modelData->nDelayExpressions = 0;
  data->modelData->nBaseClocks = 0;
  data->modelData->nSpatialDistributions = 0;
  data->modelData->nSensitivityVars = 0;
  data->modelData->nSensitivityParamVars = 0;
  data->modelData->nSetcVars = 0;
  data->modelData->ndataReconVars = 0;
  data->modelData->nSetbVars = 0;
  data->modelData->nRelatedBoundaryConditions = 0;
  data->modelData->linearizationDumpLanguage = OMC_LINEARIZE_DUMP_LANGUAGE_MODELICA;
}

static int rml_execution_failed()
{
  fflush(NULL);
  fprintf(stderr, "Execution failed!\n");
  fflush(NULL);
  return 1;
}


#if defined(__MINGW32__) || defined(_MSC_VER)

#if !defined(_UNICODE)
#define _UNICODE
#endif
#if !defined(UNICODE)
#define UNICODE
#endif

#include <windows.h>
char** omc_fixWindowsArgv(int argc, wchar_t **wargv)
{
  char** newargv;
  /* Support for non-ASCII characters
  * Read the unicode command line arguments and translate it to char*
  */
  newargv = (char**)malloc(argc*sizeof(char*));
  for (int i = 0; i < argc; i++) {
    newargv[i] = omc_wchar_to_multibyte_str(wargv[i]);
  }
  return newargv;
}

#define OMC_MAIN wmain
#define OMC_CHAR wchar_t
#define OMC_EXPORT __declspec(dllexport) extern

#else
#define omc_fixWindowsArgv(N, A) (A)
#define OMC_MAIN main
#define OMC_CHAR char
#define OMC_EXPORT extern
#endif

#if defined(threadData)
#undef threadData
#endif
/* call the simulation runtime main from our main! */
#if defined(OMC_DLL_MAIN_DEFINE)
OMC_EXPORT int omcDllMain(int argc, OMC_CHAR **argv)
#else
int OMC_MAIN(int argc, OMC_CHAR** argv)
#endif
{
  char** newargv = omc_fixWindowsArgv(argc, argv);
  /*
    Set the error functions to be used for simulation.
    The default value for them is 'functions' version. Change it here to 'simulation' versions
  */
  omc_assert = omc_assert_simulation;
  omc_assert_withEquationIndexes = omc_assert_simulation_withEquationIndexes;

  omc_assert_warning_withEquationIndexes = omc_assert_warning_simulation_withEquationIndexes;
  omc_assert_warning = omc_assert_warning_simulation;
  omc_terminate = omc_terminate_simulation;
  omc_throw = omc_throw_simulation;

  int res;
  DATA data;
  MODEL_DATA modelData;
  SIMULATION_INFO simInfo;
  data.modelData = &modelData;
  data.simulationInfo = &simInfo;
  measure_time_flag = 0;
  compiledInDAEMode = 0;
  compiledWithSymSolver = 0;
  MMC_INIT(0);
  omc_alloc_interface.init();
  {
    MMC_TRY_TOP()
  
    MMC_TRY_STACK()
  
    smoke_setupDataStruc(&data, threadData);
    res = _main_initRuntimeAndSimulation(argc, newargv, &data, threadData);
    if(res == 0) {
      if (omc_flag[FLAG_MOO_OPTIMIZATION]) {
        res = _main_OptimizationRuntime(argc, newargv, &data, threadData);
      } else {
        res = _main_SimulationRuntime(argc, newargv, &data, threadData);
      }
    }
    
    MMC_ELSE()
    rml_execution_failed();
    fprintf(stderr, "Stack overflow detected and was not caught.\nSend us a bug report at https://trac.openmodelica.org/OpenModelica/newticket\n    Include the following trace:\n");
    printStacktraceMessages();
    fflush(NULL);
    return 1;
    MMC_CATCH_STACK()
    
    MMC_CATCH_TOP(return rml_execution_failed());
  }

  fflush(NULL);
  return res;
}

#ifdef __cplusplus
}
#endif


