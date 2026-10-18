/* Initialization */
#include "smoke_model.h"
#include "smoke_11mix.h"
#include "smoke_12jac.h"
#if defined(__cplusplus)
extern "C" {
#endif

void smoke_functionInitialEquations_0(DATA *data, threadData_t *threadData);

/*
equation index: 1
type: SIMPLE_ASSIGN
soc = soc_start
*/
void smoke_eqFunction_1(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,1};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* soc STATE(1) */) = (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[5]] /* soc_start PARAM */);
  threadData->lastEquationSolved = 1;
}
extern void smoke_eqFunction_13(DATA *data, threadData_t *threadData);


/*
equation index: 3
type: SIMPLE_ASSIGN
$PRE.tripped = false
*/
void smoke_eqFunction_3(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,3};
  (data->simulationInfo->booleanVarsPre[1] /* tripped DISCRETE */) = 0 /* false */;
  threadData->lastEquationSolved = 3;
}

/*
equation index: 4
type: SIMPLE_ASSIGN
tripped = $PRE.tripped
*/
void smoke_eqFunction_4(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,4};
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[1]] /* tripped DISCRETE */) = (data->simulationInfo->booleanVarsPre[1] /* tripped DISCRETE */);
  threadData->lastEquationSolved = 4;
}

/*
equation index: 5
type: SIMPLE_ASSIGN
power_W = if tripped then 0.0 else load_W
*/
void smoke_eqFunction_5(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,5};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power_W variable */) = ((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[1]] /* tripped DISCRETE */)?0.0:(data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[1]] /* load_W PARAM */));
  threadData->lastEquationSolved = 5;
}

void smoke_eqFunction_6(DATA*, threadData_t*);
void smoke_eqFunction_7(DATA*, threadData_t*);
/*
equation index: 10
indexNonlinear: 0
type: NONLINEAR

vars: {terminal_V}
eqns: {6, 7}
*/
void smoke_eqFunction_10(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,10};
  int retValue;
  infoStreamPrint(OMC_LOG_DT, 0, "Solving nonlinear system 10 (STRICT TEARING SET if tearing enabled) at time = %18.10e", data->localData[0]->timeValue);
  /* get old value */
  data->simulationInfo->nonlinearSystemData[0].nlsxOld[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */);
  retValue = solve_nonlinear_system(data, threadData, 0);
  /* check if solution process was successful */
  if (retValue > 0){
    const int indexes[2] = {1,10};
    throwStreamPrintWithEquationIndexes(threadData, omc_dummyFileInfo, indexes, "Solving non-linear system 10 failed at time=%.15g.\nFor more information please use -lv LOG_NLS.", data->localData[0]->timeValue);
  }
  /* write solution */
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */) = data->simulationInfo->nonlinearSystemData[0].nlsx[0];
  threadData->lastEquationSolved = 10;
}
extern void smoke_eqFunction_19(DATA *data, threadData_t *threadData);


/*
equation index: 12
type: ALGORITHM

  $whenCondition1 := $START.$whenCondition1;
  $whenCondition1 := terminal_V < trip_V;
*/
void smoke_eqFunction_12(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,12};
  modelica_boolean tmp0;
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[0]] /* $whenCondition1 DISCRETE */) = (data->modelData->booleanVarsData[0] /* $whenCondition1 DISCRETE */).attribute .start;

  tmp0 = Less((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */),(data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[6]] /* trip_V PARAM */));
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[0]] /* $whenCondition1 DISCRETE */) = tmp0;
  threadData->lastEquationSolved = 12;
}
OMC_DISABLE_OPT
void smoke_functionInitialEquations_0(DATA *data, threadData_t *threadData)
{
  static void (*const eqFunctions[8])(DATA*, threadData_t*) = {
    smoke_eqFunction_1,
    smoke_eqFunction_13,
    smoke_eqFunction_3,
    smoke_eqFunction_4,
    smoke_eqFunction_5,
    smoke_eqFunction_10,
    smoke_eqFunction_19,
    smoke_eqFunction_12
  };
  
  for (int id = 0; id < 8; id++) {
    eqFunctions[id](data, threadData);
  }
}

int smoke_functionInitialEquations(DATA *data, threadData_t *threadData)
{
  data->simulationInfo->discreteCall = 1;
  smoke_functionInitialEquations_0(data, threadData);
  data->simulationInfo->discreteCall = 0;
  
  return 0;
}

/* No smoke_functionInitialEquations_lambda0 function */

int smoke_functionRemovedInitialEquations(DATA *data, threadData_t *threadData)
{
  const int *equationIndexes = NULL;
  double res = 0.0;

  
  return 0;
}


#if defined(__cplusplus)
}
#endif
