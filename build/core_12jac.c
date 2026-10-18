/* Jacobians 9 */
#include "core_model.h"
#include "core_12jac.h"
#include "simulation/jacobian_util.h"
#include "util/omc_file.h"
/* constant equations */
/* dynamic equations */

/*
equation index: 33
type: SIMPLE_ASSIGN
p_psu_w.$pDERNLSJac0.dummyVarNLSJac0 = if psu_enabled then if noEvent(p_server_w < n_psu * 3000.0 * max(v_sdp_pu, 0.0)) then 0.0 else n_psu * 3000.0 * (if noEvent(v_sdp_pu > 0.0) then v_sdp_pu.SeedNLSJac0 else 0.0) else 0.0
*/
void core_eqFunction_33(DATA *data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  const int baseClockIndex = 0;
  const int subClockIndex = 0;
  const int equationIndexes[2] = {1,33};
  modelica_boolean tmp0;
  modelica_boolean tmp1;
  modelica_boolean tmp2;
  modelica_real tmp3;
  modelica_boolean tmp4;
  modelica_real tmp5;
  tmp4 = (modelica_boolean)(data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */);
  if(tmp4)
  {
    tmp0 = Less((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */),(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[16]] /* n_psu PARAM */)) * (3000.0)) * (fmax((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */),0.0)));
    tmp2 = (modelica_boolean)tmp0;
    if(tmp2)
    {
      tmp3 = 0.0;
    }
    else
    {
      tmp1 = Greater((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */),0.0);
      tmp3 = (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[16]] /* n_psu PARAM */)) * (3000.0)) * ((tmp1?jacobian->seedVars[0] /* v_sdp_pu.SeedNLSJac0 SEED_VAR */:0.0));
    }
    tmp5 = tmp3;
  }
  else
  {
    tmp5 = 0.0;
  }
  jacobian->tmpVars[0] /* p_psu_w.$pDERNLSJac0.dummyVarNLSJac0 JACOBIAN_TMP_VAR */ = tmp5;
  threadData->lastEquationSolved = 33;
}

/*
equation index: 34
type: SIMPLE_ASSIGN
p_grid_w.$pDERNLSJac0.dummyVarNLSJac0 = 1.0362694300518136 * p_psu_w.$pDERNLSJac0.dummyVarNLSJac0
*/
void core_eqFunction_34(DATA *data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  const int baseClockIndex = 0;
  const int subClockIndex = 1;
  const int equationIndexes[2] = {1,34};
  jacobian->tmpVars[1] /* p_grid_w.$pDERNLSJac0.dummyVarNLSJac0 JACOBIAN_TMP_VAR */ = (1.0362694300518136) * (jacobian->tmpVars[0] /* p_psu_w.$pDERNLSJac0.dummyVarNLSJac0 JACOBIAN_TMP_VAR */);
  threadData->lastEquationSolved = 34;
}

/*
equation index: 35
type: SIMPLE_ASSIGN
i_grid_pu.$pDERNLSJac0.dummyVarNLSJac0 = if v_sdp_pu > 0.01 then p_total_rated_w * (p_grid_w.$pDERNLSJac0.dummyVarNLSJac0 * v_sdp_pu - p_grid_w * v_sdp_pu.SeedNLSJac0) / (p_total_rated_w * v_sdp_pu) ^ 2.0 else 0.0
*/
void core_eqFunction_35(DATA *data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  const int baseClockIndex = 0;
  const int subClockIndex = 2;
  const int equationIndexes[2] = {1,35};
  modelica_boolean tmp6;
  modelica_real tmp7;
  modelica_boolean tmp8;
  modelica_real tmp9;
  tmp6 = Greater((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */),0.01);
  tmp8 = (modelica_boolean)tmp6;
  if(tmp8)
  {
    tmp7 = ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[20]] /* p_total_rated_w PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */));
    tmp9 = DIVISION(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[20]] /* p_total_rated_w PARAM */)) * ((jacobian->tmpVars[1] /* p_grid_w.$pDERNLSJac0.dummyVarNLSJac0 JACOBIAN_TMP_VAR */) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */)) - (((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[30]] /* p_grid_w variable */)) * (jacobian->seedVars[0] /* v_sdp_pu.SeedNLSJac0 SEED_VAR */))),(tmp7 * tmp7),"(p_total_rated_w * v_sdp_pu) ^ 2.0");
  }
  else
  {
    tmp9 = 0.0;
  }
  jacobian->tmpVars[2] /* i_grid_pu.$pDERNLSJac0.dummyVarNLSJac0 JACOBIAN_TMP_VAR */ = tmp9;
  threadData->lastEquationSolved = 35;
}

/*
equation index: 36
type: SIMPLE_ASSIGN
$res_NLSJac0_1.$pDERNLSJac0.dummyVarNLSJac0 = (-0.523) * z_total_pu * i_grid_pu.$pDERNLSJac0.dummyVarNLSJac0 * v_source_pu - v_sdp_pu.SeedNLSJac0
*/
void core_eqFunction_36(DATA *data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  const int baseClockIndex = 0;
  const int subClockIndex = 3;
  const int equationIndexes[2] = {1,36};
  jacobian->resultVars[0] /* $res_NLSJac0_1.$pDERNLSJac0.dummyVarNLSJac0 JACOBIAN_VAR */ = (-0.523) * (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[28]] /* z_total_pu PARAM */)) * ((jacobian->tmpVars[2] /* i_grid_pu.$pDERNLSJac0.dummyVarNLSJac0 JACOBIAN_TMP_VAR */) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[37]] /* v_source_pu variable */)))) - jacobian->seedVars[0] /* v_sdp_pu.SeedNLSJac0 SEED_VAR */;
  threadData->lastEquationSolved = 36;
}

OMC_DISABLE_OPT
int core_functionJacNLSJac0_constantEqns(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  int index = core_INDEX_JAC_NLSJac0;
  
  
  return 0;
}

int core_functionJacNLSJac0_column(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  int index = core_INDEX_JAC_NLSJac0;
  
  static void (*const eqFunctions[4])(DATA*, threadData_t*, JACOBIAN*, JACOBIAN*) = {
    core_eqFunction_33,
    core_eqFunction_34,
    core_eqFunction_35,
    core_eqFunction_36
  };
  
  if (jacobian->evalSelection) {
    for (int i = 0; i < jacobian->evalSelection->n; i++) {
      int id = jacobian->evalSelection->idx[i];
      eqFunctions[id](data, threadData, jacobian, parentJacobian);
    }
  } else {
    for (int id = 0; id < 4; id++) {
      eqFunctions[id](data, threadData, jacobian, parentJacobian);
    }
  }
  
  return 0;
}

void core_JacNLSJac0_DAG(DATA* data, threadData_t* threadData, JACOBIAN* jacobian)
{
  const size_t eqMap[] = {33, 34, 35, 36};
  buildEvalDAG_Jac(jacobian, data->modelData, sizeof(eqMap)/sizeof(size_t), eqMap);
}

/* constant equations */
/* dynamic equations */

/*
equation index: 106
type: SIMPLE_ASSIGN
$cse1.$pDERNLSJac1.dummyVarNLSJac1 = if noEvent(v_sdp_pu > 0.0) then v_sdp_pu.SeedNLSJac1 else 0.0
*/
void core_eqFunction_106(DATA *data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  const int baseClockIndex = 0;
  const int subClockIndex = 0;
  const int equationIndexes[2] = {1,106};
  modelica_boolean tmp10;
  tmp10 = Greater((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */),0.0);
  jacobian->tmpVars[0] /* $cse1.$pDERNLSJac1.dummyVarNLSJac1 JACOBIAN_TMP_VAR */ = (tmp10?jacobian->seedVars[0] /* v_sdp_pu.SeedNLSJac1 SEED_VAR */:0.0);
  threadData->lastEquationSolved = 106;
}

/*
equation index: 107
type: SIMPLE_ASSIGN
p_psu_w.$pDERNLSJac1.dummyVarNLSJac1 = if psu_enabled then if noEvent(p_server_w < n_psu * 3000.0 * $cse1) then 0.0 else n_psu * 3000.0 * $cse1.$pDERNLSJac1.dummyVarNLSJac1 else 0.0
*/
void core_eqFunction_107(DATA *data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  const int baseClockIndex = 0;
  const int subClockIndex = 1;
  const int equationIndexes[2] = {1,107};
  modelica_boolean tmp11;
  modelica_boolean tmp12;
  modelica_real tmp13;
  tmp12 = (modelica_boolean)(data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */);
  if(tmp12)
  {
    tmp11 = Less((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */),(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[16]] /* n_psu PARAM */)) * (3000.0)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[20]] /* $cse1 variable */)));
    tmp13 = (tmp11?0.0:(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[16]] /* n_psu PARAM */)) * (3000.0)) * (jacobian->tmpVars[0] /* $cse1.$pDERNLSJac1.dummyVarNLSJac1 JACOBIAN_TMP_VAR */));
  }
  else
  {
    tmp13 = 0.0;
  }
  jacobian->tmpVars[1] /* p_psu_w.$pDERNLSJac1.dummyVarNLSJac1 JACOBIAN_TMP_VAR */ = tmp13;
  threadData->lastEquationSolved = 107;
}

/*
equation index: 108
type: SIMPLE_ASSIGN
p_grid_w.$pDERNLSJac1.dummyVarNLSJac1 = 1.0362694300518136 * p_psu_w.$pDERNLSJac1.dummyVarNLSJac1
*/
void core_eqFunction_108(DATA *data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  const int baseClockIndex = 0;
  const int subClockIndex = 2;
  const int equationIndexes[2] = {1,108};
  jacobian->tmpVars[2] /* p_grid_w.$pDERNLSJac1.dummyVarNLSJac1 JACOBIAN_TMP_VAR */ = (1.0362694300518136) * (jacobian->tmpVars[1] /* p_psu_w.$pDERNLSJac1.dummyVarNLSJac1 JACOBIAN_TMP_VAR */);
  threadData->lastEquationSolved = 108;
}

/*
equation index: 109
type: SIMPLE_ASSIGN
i_grid_pu.$pDERNLSJac1.dummyVarNLSJac1 = if v_sdp_pu > 0.01 then p_total_rated_w * (p_grid_w.$pDERNLSJac1.dummyVarNLSJac1 * v_sdp_pu - p_grid_w * v_sdp_pu.SeedNLSJac1) / (p_total_rated_w * v_sdp_pu) ^ 2.0 else 0.0
*/
void core_eqFunction_109(DATA *data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  const int baseClockIndex = 0;
  const int subClockIndex = 3;
  const int equationIndexes[2] = {1,109};
  modelica_boolean tmp14;
  modelica_real tmp15;
  modelica_real tmp16;
  modelica_real tmp17;
  modelica_boolean tmp18;
  modelica_real tmp19;
  tmp15 = 1.0;
  tmp16 = 0.01;
  relationhysteresis(data, &tmp14, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */), 0.01, tmp15, tmp16, 13, Greater, GreaterZC);
  tmp18 = (modelica_boolean)tmp14;
  if(tmp18)
  {
    tmp17 = ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[20]] /* p_total_rated_w PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */));
    tmp19 = DIVISION(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[20]] /* p_total_rated_w PARAM */)) * ((jacobian->tmpVars[2] /* p_grid_w.$pDERNLSJac1.dummyVarNLSJac1 JACOBIAN_TMP_VAR */) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */)) - (((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[30]] /* p_grid_w variable */)) * (jacobian->seedVars[0] /* v_sdp_pu.SeedNLSJac1 SEED_VAR */))),(tmp17 * tmp17),"(p_total_rated_w * v_sdp_pu) ^ 2.0");
  }
  else
  {
    tmp19 = 0.0;
  }
  jacobian->tmpVars[3] /* i_grid_pu.$pDERNLSJac1.dummyVarNLSJac1 JACOBIAN_TMP_VAR */ = tmp19;
  threadData->lastEquationSolved = 109;
}

/*
equation index: 110
type: SIMPLE_ASSIGN
$res_NLSJac1_1.$pDERNLSJac1.dummyVarNLSJac1 = (-0.523) * z_total_pu * i_grid_pu.$pDERNLSJac1.dummyVarNLSJac1 * v_source_pu - v_sdp_pu.SeedNLSJac1
*/
void core_eqFunction_110(DATA *data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  const int baseClockIndex = 0;
  const int subClockIndex = 4;
  const int equationIndexes[2] = {1,110};
  jacobian->resultVars[0] /* $res_NLSJac1_1.$pDERNLSJac1.dummyVarNLSJac1 JACOBIAN_VAR */ = (-0.523) * (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[28]] /* z_total_pu PARAM */)) * ((jacobian->tmpVars[3] /* i_grid_pu.$pDERNLSJac1.dummyVarNLSJac1 JACOBIAN_TMP_VAR */) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[37]] /* v_source_pu variable */)))) - jacobian->seedVars[0] /* v_sdp_pu.SeedNLSJac1 SEED_VAR */;
  threadData->lastEquationSolved = 110;
}

OMC_DISABLE_OPT
int core_functionJacNLSJac1_constantEqns(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  int index = core_INDEX_JAC_NLSJac1;
  
  
  return 0;
}

int core_functionJacNLSJac1_column(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  int index = core_INDEX_JAC_NLSJac1;
  
  static void (*const eqFunctions[5])(DATA*, threadData_t*, JACOBIAN*, JACOBIAN*) = {
    core_eqFunction_106,
    core_eqFunction_107,
    core_eqFunction_108,
    core_eqFunction_109,
    core_eqFunction_110
  };
  
  if (jacobian->evalSelection) {
    for (int i = 0; i < jacobian->evalSelection->n; i++) {
      int id = jacobian->evalSelection->idx[i];
      eqFunctions[id](data, threadData, jacobian, parentJacobian);
    }
  } else {
    for (int id = 0; id < 5; id++) {
      eqFunctions[id](data, threadData, jacobian, parentJacobian);
    }
  }
  
  return 0;
}

void core_JacNLSJac1_DAG(DATA* data, threadData_t* threadData, JACOBIAN* jacobian)
{
  const size_t eqMap[] = {106, 107, 108, 109, 110};
  buildEvalDAG_Jac(jacobian, data->modelData, sizeof(eqMap)/sizeof(size_t), eqMap);
}

int core_functionJacADJ_column(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  return 0;
}

void core_JacADJ_DAG(DATA* data, threadData_t* threadData, JACOBIAN* jacobian) { /* empty */ }

int core_functionJacH_column(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  return 0;
}

void core_JacH_DAG(DATA* data, threadData_t* threadData, JACOBIAN* jacobian) { /* empty */ }

int core_functionJacF_column(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  return 0;
}

void core_JacF_DAG(DATA* data, threadData_t* threadData, JACOBIAN* jacobian) { /* empty */ }

int core_functionJacD_column(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  return 0;
}

void core_JacD_DAG(DATA* data, threadData_t* threadData, JACOBIAN* jacobian) { /* empty */ }

int core_functionJacC_column(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  return 0;
}

void core_JacC_DAG(DATA* data, threadData_t* threadData, JACOBIAN* jacobian) { /* empty */ }

int core_functionJacB_column(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  return 0;
}

void core_JacB_DAG(DATA* data, threadData_t* threadData, JACOBIAN* jacobian) { /* empty */ }

/* constant equations */
/* dynamic equations */

OMC_DISABLE_OPT
int core_functionJacA_constantEqns(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  int index = core_INDEX_JAC_A;
  
  
  return 0;
}

int core_functionJacA_column(DATA* data, threadData_t *threadData, JACOBIAN *jacobian, JACOBIAN *parentJacobian)
{
  int index = core_INDEX_JAC_A;
  
  
  return 0;
}

void core_JacA_DAG(DATA* data, threadData_t* threadData, JACOBIAN* jacobian)
{
  const size_t eqMap[] = {};
  buildEvalDAG_Jac(jacobian, data->modelData, sizeof(eqMap)/sizeof(size_t), eqMap);
}

OMC_DISABLE_OPT
int core_initialAnalyticJacobianNLSJac0(DATA* data, threadData_t *threadData, JACOBIAN *jacobian)
{
  size_t count;

  FILE* pFile = openSparsePatternFile(data, threadData, "core_JacNLSJac0.bin");
  
  initJacobian(jacobian, 1, 1, 4, NULL, core_functionJacNLSJac0_column, NULL, NULL);
  jacobian->sparsePattern = allocSparsePattern(1, 1, 1);
  jacobian->availability = JACOBIAN_AVAILABLE;
  jacobian->isRowEval = 0 /* false */;
  
  /* read lead index of compressed sparse column */
  count = omc_fread(jacobian->sparsePattern->leadindex, sizeof(unsigned int), 1+1, pFile, FALSE);
  if (count != 1+1) {
    throwStreamPrint(threadData, "Error while reading lead index list of sparsity pattern. Expected %d, got %zu", 1+1, count);
  }
  
  /* read sparse index */
  count = omc_fread(jacobian->sparsePattern->index, sizeof(unsigned int), 1, pFile, FALSE);
  if (count != 1) {
    throwStreamPrint(threadData, "Error while reading row index list of sparsity pattern. Expected %d, got %zu", 1, count);
  }
  
  /* write color array */
  /* color 1 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 1, 1, 1);
  
  omc_fclose(pFile);
  
  return 0;
}
OMC_DISABLE_OPT
int core_initialAnalyticJacobianNLSJac1(DATA* data, threadData_t *threadData, JACOBIAN *jacobian)
{
  size_t count;

  FILE* pFile = openSparsePatternFile(data, threadData, "core_JacNLSJac1.bin");
  
  initJacobian(jacobian, 1, 1, 5, NULL, core_functionJacNLSJac1_column, NULL, NULL);
  jacobian->sparsePattern = allocSparsePattern(1, 1, 1);
  jacobian->availability = JACOBIAN_AVAILABLE;
  jacobian->isRowEval = 0 /* false */;
  
  /* read lead index of compressed sparse column */
  count = omc_fread(jacobian->sparsePattern->leadindex, sizeof(unsigned int), 1+1, pFile, FALSE);
  if (count != 1+1) {
    throwStreamPrint(threadData, "Error while reading lead index list of sparsity pattern. Expected %d, got %zu", 1+1, count);
  }
  
  /* read sparse index */
  count = omc_fread(jacobian->sparsePattern->index, sizeof(unsigned int), 1, pFile, FALSE);
  if (count != 1) {
    throwStreamPrint(threadData, "Error while reading row index list of sparsity pattern. Expected %d, got %zu", 1, count);
  }
  
  /* write color array */
  /* color 1 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 1, 1, 1);
  
  omc_fclose(pFile);
  
  return 0;
}
int core_initialAnalyticJacobianADJ(DATA* data, threadData_t *threadData, JACOBIAN *jacobian)
{
  jacobian->availability = JACOBIAN_NOT_AVAILABLE;
  return 1;
}
int core_initialAnalyticJacobianH(DATA* data, threadData_t *threadData, JACOBIAN *jacobian)
{
  jacobian->availability = JACOBIAN_NOT_AVAILABLE;
  return 1;
}
int core_initialAnalyticJacobianF(DATA* data, threadData_t *threadData, JACOBIAN *jacobian)
{
  jacobian->availability = JACOBIAN_NOT_AVAILABLE;
  return 1;
}
int core_initialAnalyticJacobianD(DATA* data, threadData_t *threadData, JACOBIAN *jacobian)
{
  jacobian->availability = JACOBIAN_NOT_AVAILABLE;
  return 1;
}
int core_initialAnalyticJacobianC(DATA* data, threadData_t *threadData, JACOBIAN *jacobian)
{
  jacobian->availability = JACOBIAN_NOT_AVAILABLE;
  return 1;
}
int core_initialAnalyticJacobianB(DATA* data, threadData_t *threadData, JACOBIAN *jacobian)
{
  jacobian->availability = JACOBIAN_NOT_AVAILABLE;
  return 1;
}
OMC_DISABLE_OPT
int core_initialAnalyticJacobianA(DATA* data, threadData_t *threadData, JACOBIAN *jacobian)
{
  size_t count;

  FILE* pFile = openSparsePatternFile(data, threadData, "core_JacA.bin");
  
  initJacobian(jacobian, 10, 10, 0, NULL, core_functionJacA_column, NULL, NULL);
  jacobian->sparsePattern = allocSparsePattern(10, 39, 10);
  jacobian->availability = JACOBIAN_ONLY_SPARSITY;
  jacobian->isRowEval = 0 /* false */;
  
  /* read lead index of compressed sparse column */
  count = omc_fread(jacobian->sparsePattern->leadindex, sizeof(unsigned int), 10+1, pFile, FALSE);
  if (count != 10+1) {
    throwStreamPrint(threadData, "Error while reading lead index list of sparsity pattern. Expected %d, got %zu", 10+1, count);
  }
  
  /* read sparse index */
  count = omc_fread(jacobian->sparsePattern->index, sizeof(unsigned int), 39, pFile, FALSE);
  if (count != 39) {
    throwStreamPrint(threadData, "Error while reading row index list of sparsity pattern. Expected %d, got %zu", 39, count);
  }
  
  /* write color array */
  /* color 1 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 1, 1, 10);
  /* color 2 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 2, 1, 10);
  /* color 3 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 3, 1, 10);
  /* color 4 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 4, 1, 10);
  /* color 5 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 5, 1, 10);
  /* color 6 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 6, 1, 10);
  /* color 7 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 7, 1, 10);
  /* color 8 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 8, 1, 10);
  /* color 9 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 9, 1, 10);
  /* color 10 with 1 columns */
  readSparsePatternColor(threadData, pFile, jacobian->sparsePattern->colorCols, 10, 1, 10);
  
  omc_fclose(pFile);
  
  return 0;
}


