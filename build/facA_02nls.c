/* Non Linear Systems */
#include "facA_model.h"
#include "facA_12jac.h"
#include "simulation/jacobian_util.h"
#include "simulation/arrayIndex.h"

#if defined(__cplusplus)
extern "C" {
#endif

/* inner equations */

/*
equation index: 29
type: SIMPLE_ASSIGN
p_psu_w = if psu_enabled then min(p_server_w, n_psu * 3000.0 * max(v_sdp_pu, 0.0)) else 0.0
*/
void facA_eqFunction_29(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,29};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[31]] /* p_psu_w variable */) = ((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */)?fmin((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */),(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[16]] /* n_psu PARAM */)) * (3000.0)) * (fmax((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */),0.0))):0.0);
  threadData->lastEquationSolved = 29;
}
/*
equation index: 30
type: SIMPLE_ASSIGN
p_grid_w = 1.0362694300518136 * p_psu_w + p_cooling_w
*/
void facA_eqFunction_30(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,30};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[30]] /* p_grid_w variable */) = (1.0362694300518136) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[31]] /* p_psu_w variable */)) + (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[29]] /* p_cooling_w variable */);
  threadData->lastEquationSolved = 30;
}
/*
equation index: 31
type: SIMPLE_ASSIGN
i_grid_pu = if v_sdp_pu > 0.01 then p_grid_w / (p_total_rated_w * v_sdp_pu) else 0.0
*/
void facA_eqFunction_31(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,31};
  modelica_boolean tmp0;
  tmp0 = Greater((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */),0.01);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[27]] /* i_grid_pu variable */) = (tmp0?DIVISION_SIM((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[30]] /* p_grid_w variable */),((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[20]] /* p_total_rated_w PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */)),"p_total_rated_w * v_sdp_pu",equationIndexes):0.0);
  threadData->lastEquationSolved = 31;
}

void residualFunc37(RESIDUAL_USERDATA* userData, const double* xloc, double* res, const int* iflag)
{
  DATA *data = userData->data;
  threadData_t *threadData = userData->threadData;
  const int equationIndexes[2] = {1,37};
  int i,j;
  /* iteration variables */
  for (i=0; i<1; i++) {
    if (isinf(xloc[i]) || isnan(xloc[i])) {
      errorStreamPrint(OMC_LOG_NLS, 0, "residualFunc37: Iteration variable `%s` is inf or nan.",
        modelInfoGetEquation(&data->modelData->modelDataXml, 37).vars[i]);
      for (j=0; j<1; j++) {
        res[j] = NAN;
      }
      throwStreamPrintWithEquationIndexes(threadData, omc_dummyFileInfo, equationIndexes, "residualFunc37 failed at time=%.15g.\nFor more information please use -lv LOG_NLS.", data->localData[0]->timeValue);
      return;
    }
  }
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */) = xloc[0];
  /* backup outputs */
  /* pre body */
  /* local constraints */
  facA_eqFunction_29(data, threadData);
  /* local constraints */
  facA_eqFunction_30(data, threadData);
  /* local constraints */
  facA_eqFunction_31(data, threadData);
  /* body */
  res[0] = (-0.523) * (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[28]] /* z_total_pu PARAM */)) * ((-1.0 + (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[27]] /* i_grid_pu variable */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[37]] /* v_source_pu variable */)))) + (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[37]] /* v_source_pu variable */) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */);
  threadData->lastEquationSolved = 32;
  /* restore known outputs */
  threadData->lastEquationSolved = 37;
}

OMC_DISABLE_OPT
void initializeSparsePatternNLS37(NONLINEAR_SYSTEM_DATA* inSysData)
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

void freeSparsePatternNLS37(NONLINEAR_SYSTEM_DATA* inSysData)
{
  if (inSysData->isPatternAvailable) {
    freeSparsePattern(inSysData->sparsePattern);
    free(inSysData->sparsePattern);
    inSysData->sparsePattern = NULL;
    inSysData->isPatternAvailable = FALSE;
  }
}
OMC_DISABLE_OPT
void initializeNonlinearPatternNLS37(NONLINEAR_SYSTEM_DATA* inSysData)
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
void initializeStaticDataNLS37(DATA* data, threadData_t *threadData, NONLINEAR_SYSTEM_DATA *sysData, modelica_boolean initSparsePattern, modelica_boolean initNonlinearPattern)
{
  int i=0;
  /* static nls data for v_sdp_pu */
  sysData->nominal[i] = getNominalFromScalarIdx(data->simulationInfo, data->modelData, VAR_KIND_VARIABLE, 36 /* v_sdp_pu */);
  sysData->min[i]     = getMinFromScalarIdx(data->simulationInfo, data->modelData, VAR_TYPE_REAL, VAR_KIND_VARIABLE, 36 /* v_sdp_pu */);
  sysData->max[i++]   = getMaxFromScalarIdx(data->simulationInfo, data->modelData, VAR_TYPE_REAL, VAR_KIND_VARIABLE, 36 /* v_sdp_pu */);
  /* initial sparse pattern */
  if (initSparsePattern) {
    initializeSparsePatternNLS37(sysData);
  }
  if (initNonlinearPattern) {
    initializeNonlinearPatternNLS37(sysData);
  }
}

OMC_DISABLE_OPT
void freeStaticDataNLS37(DATA* data, threadData_t *threadData, NONLINEAR_SYSTEM_DATA *sysData)
{
  freeSparsePatternNLS37(sysData);
}

OMC_DISABLE_OPT
void getIterationVarsNLS37(DATA* data, double *array)
{
  array[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */);
}


/* inner equations */

/*
equation index: 101
type: SIMPLE_ASSIGN
$cse1 = max(v_sdp_pu, 0.0)
*/
void facA_eqFunction_101(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,101};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[20]] /* $cse1 variable */) = fmax((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */),0.0);
  threadData->lastEquationSolved = 101;
}
/*
equation index: 102
type: SIMPLE_ASSIGN
p_psu_w = if psu_enabled then min(p_server_w, n_psu * 3000.0 * $cse1) else 0.0
*/
void facA_eqFunction_102(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,102};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[31]] /* p_psu_w variable */) = ((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */)?fmin((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */),(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[16]] /* n_psu PARAM */)) * (3000.0)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[20]] /* $cse1 variable */))):0.0);
  threadData->lastEquationSolved = 102;
}
/*
equation index: 103
type: SIMPLE_ASSIGN
p_grid_w = 1.0362694300518136 * p_psu_w + p_cooling_w
*/
void facA_eqFunction_103(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,103};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[30]] /* p_grid_w variable */) = (1.0362694300518136) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[31]] /* p_psu_w variable */)) + (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[29]] /* p_cooling_w variable */);
  threadData->lastEquationSolved = 103;
}
/*
equation index: 104
type: SIMPLE_ASSIGN
i_grid_pu = if v_sdp_pu > 0.01 then p_grid_w / (p_total_rated_w * v_sdp_pu) else 0.0
*/
void facA_eqFunction_104(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,104};
  modelica_boolean tmp0;
  modelica_real tmp1;
  modelica_real tmp2;
  tmp1 = 1.0;
  tmp2 = 0.01;
  relationhysteresis(data, &tmp0, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */), 0.01, tmp1, tmp2, 13, Greater, GreaterZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[27]] /* i_grid_pu variable */) = (tmp0?DIVISION_SIM((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[30]] /* p_grid_w variable */),((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[20]] /* p_total_rated_w PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */)),"p_total_rated_w * v_sdp_pu",equationIndexes):0.0);
  threadData->lastEquationSolved = 104;
}

void residualFunc111(RESIDUAL_USERDATA* userData, const double* xloc, double* res, const int* iflag)
{
  DATA *data = userData->data;
  threadData_t *threadData = userData->threadData;
  const int equationIndexes[2] = {1,111};
  int i,j;
  /* iteration variables */
  for (i=0; i<1; i++) {
    if (isinf(xloc[i]) || isnan(xloc[i])) {
      errorStreamPrint(OMC_LOG_NLS, 0, "residualFunc111: Iteration variable `%s` is inf or nan.",
        modelInfoGetEquation(&data->modelData->modelDataXml, 111).vars[i]);
      for (j=0; j<1; j++) {
        res[j] = NAN;
      }
      throwStreamPrintWithEquationIndexes(threadData, omc_dummyFileInfo, equationIndexes, "residualFunc111 failed at time=%.15g.\nFor more information please use -lv LOG_NLS.", data->localData[0]->timeValue);
      return;
    }
  }
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */) = xloc[0];
  /* backup outputs */
  /* pre body */
  /* local constraints */
  facA_eqFunction_101(data, threadData);
  /* local constraints */
  facA_eqFunction_102(data, threadData);
  /* local constraints */
  facA_eqFunction_103(data, threadData);
  /* local constraints */
  facA_eqFunction_104(data, threadData);
  /* body */
  res[0] = (-0.523) * (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[28]] /* z_total_pu PARAM */)) * ((-1.0 + (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[27]] /* i_grid_pu variable */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[37]] /* v_source_pu variable */)))) + (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[37]] /* v_source_pu variable */) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */);
  threadData->lastEquationSolved = 105;
  /* restore known outputs */
  threadData->lastEquationSolved = 111;
}

OMC_DISABLE_OPT
void initializeSparsePatternNLS111(NONLINEAR_SYSTEM_DATA* inSysData)
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

void freeSparsePatternNLS111(NONLINEAR_SYSTEM_DATA* inSysData)
{
  if (inSysData->isPatternAvailable) {
    freeSparsePattern(inSysData->sparsePattern);
    free(inSysData->sparsePattern);
    inSysData->sparsePattern = NULL;
    inSysData->isPatternAvailable = FALSE;
  }
}
OMC_DISABLE_OPT
void initializeNonlinearPatternNLS111(NONLINEAR_SYSTEM_DATA* inSysData)
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
void initializeStaticDataNLS111(DATA* data, threadData_t *threadData, NONLINEAR_SYSTEM_DATA *sysData, modelica_boolean initSparsePattern, modelica_boolean initNonlinearPattern)
{
  int i=0;
  /* static nls data for v_sdp_pu */
  sysData->nominal[i] = getNominalFromScalarIdx(data->simulationInfo, data->modelData, VAR_KIND_VARIABLE, 36 /* v_sdp_pu */);
  sysData->min[i]     = getMinFromScalarIdx(data->simulationInfo, data->modelData, VAR_TYPE_REAL, VAR_KIND_VARIABLE, 36 /* v_sdp_pu */);
  sysData->max[i++]   = getMaxFromScalarIdx(data->simulationInfo, data->modelData, VAR_TYPE_REAL, VAR_KIND_VARIABLE, 36 /* v_sdp_pu */);
  /* initial sparse pattern */
  if (initSparsePattern) {
    initializeSparsePatternNLS111(sysData);
  }
  if (initNonlinearPattern) {
    initializeNonlinearPatternNLS111(sysData);
  }
}

OMC_DISABLE_OPT
void freeStaticDataNLS111(DATA* data, threadData_t *threadData, NONLINEAR_SYSTEM_DATA *sysData)
{
  freeSparsePatternNLS111(sysData);
}

OMC_DISABLE_OPT
void getIterationVarsNLS111(DATA* data, double *array)
{
  array[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */);
}

/* Prototypes for the strict sets (Dynamic Tearing) */

/* Global constraints for the casual sets */
/* function initialize non-linear systems */
void facA_initialNonLinearSystem(int nNonLinearSystems, NONLINEAR_SYSTEM_DATA* nonLinearSystemData)
{
  
  nonLinearSystemData[1].equationIndex = 111;
  nonLinearSystemData[1].size = 1;
  nonLinearSystemData[1].homotopySupport = 0 /* false */;
  nonLinearSystemData[1].mixedSystem = 1 /* true */;
  nonLinearSystemData[1].residualFunc = residualFunc111;
  nonLinearSystemData[1].strictTearingFunctionCall = NULL;
  nonLinearSystemData[1].analyticalJacobianColumn = facA_functionJacNLSJac1_column;
  nonLinearSystemData[1].initialAnalyticalJacobian = facA_initialAnalyticJacobianNLSJac1;
  nonLinearSystemData[1].jacobianIndex = 1 /*jacInx*/;
  nonLinearSystemData[1].initializeStaticNLSData = initializeStaticDataNLS111;
  nonLinearSystemData[1].freeStaticNLSData = freeStaticDataNLS111;
  nonLinearSystemData[1].getIterationVars = getIterationVarsNLS111;
  nonLinearSystemData[1].checkConstraints = NULL;
  
  const int tmp_eqn_indices_1[5] = {101, 102, 103, 104, 105};
  nonLinearSystemData[1].eqn_simcode_indices = malloc(5 * sizeof(int));
  memcpy(nonLinearSystemData[1].eqn_simcode_indices, tmp_eqn_indices_1, 5 * sizeof(int));
  nonLinearSystemData[1].torn_plus_residual_size = 5;
  
  
  nonLinearSystemData[0].equationIndex = 37;
  nonLinearSystemData[0].size = 1;
  nonLinearSystemData[0].homotopySupport = 0 /* false */;
  nonLinearSystemData[0].mixedSystem = 1 /* true */;
  nonLinearSystemData[0].residualFunc = residualFunc37;
  nonLinearSystemData[0].strictTearingFunctionCall = NULL;
  nonLinearSystemData[0].analyticalJacobianColumn = facA_functionJacNLSJac0_column;
  nonLinearSystemData[0].initialAnalyticalJacobian = facA_initialAnalyticJacobianNLSJac0;
  nonLinearSystemData[0].jacobianIndex = 0 /*jacInx*/;
  nonLinearSystemData[0].initializeStaticNLSData = initializeStaticDataNLS37;
  nonLinearSystemData[0].freeStaticNLSData = freeStaticDataNLS37;
  nonLinearSystemData[0].getIterationVars = getIterationVarsNLS37;
  nonLinearSystemData[0].checkConstraints = NULL;
  
  const int tmp_eqn_indices_0[4] = {29, 30, 31, 32};
  nonLinearSystemData[0].eqn_simcode_indices = malloc(4 * sizeof(int));
  memcpy(nonLinearSystemData[0].eqn_simcode_indices, tmp_eqn_indices_0, 4 * sizeof(int));
  nonLinearSystemData[0].torn_plus_residual_size = 4;
}

#if defined(__cplusplus)
}
#endif
