/* Non Linear Systems */
#include "smoke_model.h"
#include "smoke_12jac.h"
#include "simulation/jacobian_util.h"
#include "simulation/arrayIndex.h"

#if defined(__cplusplus)
extern "C" {
#endif

/* inner equations */

/*
equation index: 6
type: SIMPLE_ASSIGN
current_A = if power_W <= 0.0 then 0.0 else power_W / terminal_V
*/
void smoke_eqFunction_6(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,6};
  modelica_boolean tmp0;
  tmp0 = LessEq((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power_W variable */),0.0);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* current_A variable */) = (tmp0?0.0:DIVISION_SIM((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power_W variable */),(data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */),"terminal_V",equationIndexes));
  threadData->lastEquationSolved = 6;
}

void residualFunc10(RESIDUAL_USERDATA* userData, const double* xloc, double* res, const int* iflag)
{
  DATA *data = userData->data;
  threadData_t *threadData = userData->threadData;
  const int equationIndexes[2] = {1,10};
  int i,j;
  /* iteration variables */
  for (i=0; i<1; i++) {
    if (isinf(xloc[i]) || isnan(xloc[i])) {
      errorStreamPrint(OMC_LOG_NLS, 0, "residualFunc10: Iteration variable `%s` is inf or nan.",
        modelInfoGetEquation(&data->modelData->modelDataXml, 10).vars[i]);
      for (j=0; j<1; j++) {
        res[j] = NAN;
      }
      throwStreamPrintWithEquationIndexes(threadData, omc_dummyFileInfo, equationIndexes, "residualFunc10 failed at time=%.15g.\nFor more information please use -lv LOG_NLS.", data->localData[0]->timeValue);
      return;
    }
  }
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */) = xloc[0];
  /* backup outputs */
  /* pre body */
  /* local constraints */
  smoke_eqFunction_6(data, threadData);
  /* body */
  res[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* ocv_V variable */) + ((-(data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* current_A variable */))) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[4]] /* r0_Ohm PARAM */)) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */);
  threadData->lastEquationSolved = 7;
  /* restore known outputs */
  threadData->lastEquationSolved = 10;
}

OMC_DISABLE_OPT
void initializeSparsePatternNLS10(NONLINEAR_SYSTEM_DATA* inSysData)
{
  int i=0;
  const int colPtrIndex[1+1] = {0,1};
  const int rowIndex[1] = {0};
  /* sparsity pattern available */
  inSysData->isPatternAvailable = TRUE;
  inSysData->sparsePattern = allocSparsePattern(1, 1, 1);
  
  /* write lead index of compressed sparse column */
  memcpy(inSysData->sparsePattern->leadindex, colPtrIndex, (1+1)*sizeof(unsigned int));
  
  for(i=2;i<1+1;++i)
    inSysData->sparsePattern->leadindex[i] += inSysData->sparsePattern->leadindex[i-1];
  
  /* call sparse index */
  memcpy(inSysData->sparsePattern->index, rowIndex, 1*sizeof(unsigned int));
  
  /* write color array */
  /* color 1 with 1 columns */
  const int indices_1[1] = {0};
  for(i=0; i<1; i++)
    inSysData->sparsePattern->colorCols[indices_1[i]] = 1;
}

void freeSparsePatternNLS10(NONLINEAR_SYSTEM_DATA* inSysData)
{
  if (inSysData->isPatternAvailable) {
    freeSparsePattern(inSysData->sparsePattern);
    free(inSysData->sparsePattern);
    inSysData->sparsePattern = NULL;
    inSysData->isPatternAvailable = FALSE;
  }
}
OMC_DISABLE_OPT
void initializeNonlinearPatternNLS10(NONLINEAR_SYSTEM_DATA* inSysData)
{
  int i=0;
  inSysData->nonlinearPattern = (NONLINEAR_PATTERN*) malloc(sizeof(NONLINEAR_PATTERN));
  inSysData->nonlinearPattern->numberOfVars = 1;
  inSysData->nonlinearPattern->numberOfEqns = 1;
  inSysData->nonlinearPattern->numberOfNonlinear = 1;
  inSysData->nonlinearPattern->indexVar = (unsigned int*) malloc((1+1)*sizeof(unsigned int));
  inSysData->nonlinearPattern->indexEqn = (unsigned int*) malloc((1+1)*sizeof(unsigned int));
  inSysData->nonlinearPattern->columns = (unsigned int*) malloc(1*sizeof(unsigned int));
  inSysData->nonlinearPattern->rows = (unsigned int*) malloc(1*sizeof(unsigned int));
  /* initialize and accumulate index vectors */
  const int index_var[1+1] = {0,1};
  const int index_eqn[1+1] = {0,1};
  memcpy(inSysData->nonlinearPattern->indexVar, index_var, (1+1)*sizeof(unsigned int));
  memcpy(inSysData->nonlinearPattern->indexEqn, index_eqn, (1+1)*sizeof(unsigned int));
  for(i=2;i<1+1;++i)
    inSysData->nonlinearPattern->indexVar[i] += inSysData->nonlinearPattern->indexVar[i-1];
  for(i=2;i<1+1;++i)
    inSysData->nonlinearPattern->indexEqn[i] += inSysData->nonlinearPattern->indexEqn[i-1];
  /* initialize columns and rows */
  const int columns[1] = {0};
  const int rows[1] = {0};
  memcpy(inSysData->nonlinearPattern->columns, columns, 1*sizeof(unsigned int));
  memcpy(inSysData->nonlinearPattern->rows, rows, 1*sizeof(unsigned int));
}

OMC_DISABLE_OPT
void initializeStaticDataNLS10(DATA* data, threadData_t *threadData, NONLINEAR_SYSTEM_DATA *sysData, modelica_boolean initSparsePattern, modelica_boolean initNonlinearPattern)
{
  int i=0;
  /* static nls data for terminal_V */
  sysData->nominal[i] = getNominalFromScalarIdx(data->simulationInfo, data->modelData, VAR_KIND_VARIABLE, 5 /* terminal_V */);
  sysData->min[i]     = getMinFromScalarIdx(data->simulationInfo, data->modelData, VAR_TYPE_REAL, VAR_KIND_VARIABLE, 5 /* terminal_V */);
  sysData->max[i++]   = getMaxFromScalarIdx(data->simulationInfo, data->modelData, VAR_TYPE_REAL, VAR_KIND_VARIABLE, 5 /* terminal_V */);
  /* initial sparse pattern */
  if (initSparsePattern) {
    initializeSparsePatternNLS10(sysData);
  }
  if (initNonlinearPattern) {
    initializeNonlinearPatternNLS10(sysData);
  }
}

OMC_DISABLE_OPT
void freeStaticDataNLS10(DATA* data, threadData_t *threadData, NONLINEAR_SYSTEM_DATA *sysData)
{
  freeSparsePatternNLS10(sysData);
}

OMC_DISABLE_OPT
void getIterationVarsNLS10(DATA* data, double *array)
{
  array[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */);
}


/* inner equations */

/*
equation index: 14
type: ALGORITHM

  tripped := pre(tripped);
  $whenCondition1 := pre($whenCondition1);
  $whenCondition1 := terminal_V < trip_V;
  when $whenCondition1 then
    tripped := true;
  end when;
*/
void smoke_eqFunction_14(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,14};
  modelica_boolean tmp0;
  modelica_real tmp1;
  modelica_real tmp2;
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[1]] /* tripped DISCRETE */) = (data->simulationInfo->booleanVarsPre[1] /* tripped DISCRETE */);

  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[0]] /* $whenCondition1 DISCRETE */) = (data->simulationInfo->booleanVarsPre[0] /* $whenCondition1 DISCRETE */);

  tmp1 = 1.0;
  tmp2 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[6]] /* trip_V PARAM */));
  relationhysteresis(data, &tmp0, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */), (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[6]] /* trip_V PARAM */), tmp1, tmp2, 0, Less, LessZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[0]] /* $whenCondition1 DISCRETE */) = tmp0;

  if(data->simulationInfo->discreteCall == 1)
  {
    if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[0]] /* $whenCondition1 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[0] /* $whenCondition1 DISCRETE */) /* edge */))
    {
      (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[1]] /* tripped DISCRETE */) = 1 /* true */;
    }
  }
  threadData->lastEquationSolved = 14;
}
/*
equation index: 15
type: SIMPLE_ASSIGN
power_W = if tripped then 0.0 else load_W
*/
void smoke_eqFunction_15(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,15};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power_W variable */) = ((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[1]] /* tripped DISCRETE */)?0.0:(data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[1]] /* load_W PARAM */));
  threadData->lastEquationSolved = 15;
}
/*
equation index: 16
type: SIMPLE_ASSIGN
current_A = if power_W <= 0.0 then 0.0 else power_W / terminal_V
*/
void smoke_eqFunction_16(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,16};
  modelica_boolean tmp0;
  modelica_real tmp1;
  modelica_real tmp2;
  tmp1 = 1.0;
  tmp2 = 0.0;
  relationhysteresis(data, &tmp0, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power_W variable */), 0.0, tmp1, tmp2, 1, LessEq, LessEqZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* current_A variable */) = (tmp0?0.0:DIVISION_SIM((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power_W variable */),(data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */),"terminal_V",equationIndexes));
  threadData->lastEquationSolved = 16;
}

void residualFunc18(RESIDUAL_USERDATA* userData, const double* xloc, double* res, const int* iflag)
{
  DATA *data = userData->data;
  threadData_t *threadData = userData->threadData;
  const int equationIndexes[2] = {1,18};
  int i,j;
  /* iteration variables */
  for (i=0; i<1; i++) {
    if (isinf(xloc[i]) || isnan(xloc[i])) {
      errorStreamPrint(OMC_LOG_NLS, 0, "residualFunc18: Iteration variable `%s` is inf or nan.",
        modelInfoGetEquation(&data->modelData->modelDataXml, 18).vars[i]);
      for (j=0; j<1; j++) {
        res[j] = NAN;
      }
      throwStreamPrintWithEquationIndexes(threadData, omc_dummyFileInfo, equationIndexes, "residualFunc18 failed at time=%.15g.\nFor more information please use -lv LOG_NLS.", data->localData[0]->timeValue);
      return;
    }
  }
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */) = xloc[0];
  /* backup outputs */
  /* pre body */
  /* local constraints */
  smoke_eqFunction_14(data, threadData);
  /* local constraints */
  smoke_eqFunction_15(data, threadData);
  /* local constraints */
  smoke_eqFunction_16(data, threadData);
  /* body */
  res[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* ocv_V variable */) + ((-(data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* current_A variable */))) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[4]] /* r0_Ohm PARAM */)) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */);
  threadData->lastEquationSolved = 17;
  /* restore known outputs */
  threadData->lastEquationSolved = 18;
}

OMC_DISABLE_OPT
void initializeSparsePatternNLS18(NONLINEAR_SYSTEM_DATA* inSysData)
{
  int i=0;
  const int colPtrIndex[1+1] = {0,1};
  const int rowIndex[1] = {0};
  /* sparsity pattern available */
  inSysData->isPatternAvailable = TRUE;
  inSysData->sparsePattern = allocSparsePattern(1, 1, 1);
  
  /* write lead index of compressed sparse column */
  memcpy(inSysData->sparsePattern->leadindex, colPtrIndex, (1+1)*sizeof(unsigned int));
  
  for(i=2;i<1+1;++i)
    inSysData->sparsePattern->leadindex[i] += inSysData->sparsePattern->leadindex[i-1];
  
  /* call sparse index */
  memcpy(inSysData->sparsePattern->index, rowIndex, 1*sizeof(unsigned int));
  
  /* write color array */
  /* color 1 with 1 columns */
  const int indices_1[1] = {0};
  for(i=0; i<1; i++)
    inSysData->sparsePattern->colorCols[indices_1[i]] = 1;
}

void freeSparsePatternNLS18(NONLINEAR_SYSTEM_DATA* inSysData)
{
  if (inSysData->isPatternAvailable) {
    freeSparsePattern(inSysData->sparsePattern);
    free(inSysData->sparsePattern);
    inSysData->sparsePattern = NULL;
    inSysData->isPatternAvailable = FALSE;
  }
}
void initializeNonlinearPatternNLS18(NONLINEAR_SYSTEM_DATA* inSysData)
{
  /* no nonlinear pattern available */
}

OMC_DISABLE_OPT
void initializeStaticDataNLS18(DATA* data, threadData_t *threadData, NONLINEAR_SYSTEM_DATA *sysData, modelica_boolean initSparsePattern, modelica_boolean initNonlinearPattern)
{
  int i=0;
  /* static nls data for terminal_V */
  sysData->nominal[i] = getNominalFromScalarIdx(data->simulationInfo, data->modelData, VAR_KIND_VARIABLE, 5 /* terminal_V */);
  sysData->min[i]     = getMinFromScalarIdx(data->simulationInfo, data->modelData, VAR_TYPE_REAL, VAR_KIND_VARIABLE, 5 /* terminal_V */);
  sysData->max[i++]   = getMaxFromScalarIdx(data->simulationInfo, data->modelData, VAR_TYPE_REAL, VAR_KIND_VARIABLE, 5 /* terminal_V */);
  /* initial sparse pattern */
  if (initSparsePattern) {
    initializeSparsePatternNLS18(sysData);
  }
  if (initNonlinearPattern) {
    initializeNonlinearPatternNLS18(sysData);
  }
}

OMC_DISABLE_OPT
void freeStaticDataNLS18(DATA* data, threadData_t *threadData, NONLINEAR_SYSTEM_DATA *sysData)
{
  freeSparsePatternNLS18(sysData);
}

OMC_DISABLE_OPT
void getIterationVarsNLS18(DATA* data, double *array)
{
  array[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */);
}

/* Prototypes for the strict sets (Dynamic Tearing) */

/* Global constraints for the casual sets */
/* function initialize non-linear systems */
void smoke_initialNonLinearSystem(int nNonLinearSystems, NONLINEAR_SYSTEM_DATA* nonLinearSystemData)
{
  
  nonLinearSystemData[1].equationIndex = 18;
  nonLinearSystemData[1].size = 1;
  nonLinearSystemData[1].homotopySupport = 0 /* false */;
  nonLinearSystemData[1].mixedSystem = 1 /* true */;
  nonLinearSystemData[1].residualFunc = residualFunc18;
  nonLinearSystemData[1].strictTearingFunctionCall = NULL;
  nonLinearSystemData[1].analyticalJacobianColumn = NULL;
  nonLinearSystemData[1].initialAnalyticalJacobian = NULL;
  nonLinearSystemData[1].jacobianIndex = -1;
  nonLinearSystemData[1].initializeStaticNLSData = initializeStaticDataNLS18;
  nonLinearSystemData[1].freeStaticNLSData = freeStaticDataNLS18;
  nonLinearSystemData[1].getIterationVars = getIterationVarsNLS18;
  nonLinearSystemData[1].checkConstraints = NULL;
  
  const int tmp_eqn_indices_1[4] = {14, 15, 16, 17};
  nonLinearSystemData[1].eqn_simcode_indices = malloc(4 * sizeof(int));
  memcpy(nonLinearSystemData[1].eqn_simcode_indices, tmp_eqn_indices_1, 4 * sizeof(int));
  nonLinearSystemData[1].torn_plus_residual_size = 4;
  
  
  nonLinearSystemData[0].equationIndex = 10;
  nonLinearSystemData[0].size = 1;
  nonLinearSystemData[0].homotopySupport = 0 /* false */;
  nonLinearSystemData[0].mixedSystem = 0 /* false */;
  nonLinearSystemData[0].residualFunc = residualFunc10;
  nonLinearSystemData[0].strictTearingFunctionCall = NULL;
  nonLinearSystemData[0].analyticalJacobianColumn = smoke_functionJacNLSJac0_column;
  nonLinearSystemData[0].initialAnalyticalJacobian = smoke_initialAnalyticJacobianNLSJac0;
  nonLinearSystemData[0].jacobianIndex = 0 /*jacInx*/;
  nonLinearSystemData[0].initializeStaticNLSData = initializeStaticDataNLS10;
  nonLinearSystemData[0].freeStaticNLSData = freeStaticDataNLS10;
  nonLinearSystemData[0].getIterationVars = getIterationVarsNLS10;
  nonLinearSystemData[0].checkConstraints = NULL;
  
  const int tmp_eqn_indices_0[2] = {6, 7};
  nonLinearSystemData[0].eqn_simcode_indices = malloc(2 * sizeof(int));
  memcpy(nonLinearSystemData[0].eqn_simcode_indices, tmp_eqn_indices_0, 2 * sizeof(int));
  nonLinearSystemData[0].torn_plus_residual_size = 2;
}

#if defined(__cplusplus)
}
#endif
