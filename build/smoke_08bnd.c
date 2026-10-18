/* update bound parameters and variable attributes (start, nominal, min, max) */
#include "smoke_model.h"
#if defined(__cplusplus)
extern "C" {
#endif


/*
equation index: 20
type: SIMPLE_ASSIGN
$START.terminal_V = ocv_full_V
*/
static void smoke_eqFunction_20(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,20};
  ((modelica_real *)((data->modelData->realVarsData[5] /* terminal_V variable */).attribute .start.data))[0] = (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[3]] /* ocv_full_V PARAM */);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */) = ((modelica_real *)((data->modelData->realVarsData[5] /* terminal_V variable */).attribute .start.data))[0];
  infoStreamPrint(OMC_LOG_INIT_V, 0,
                  "updated start value: %s(start=%g)",
                  data->modelData->realVarsData[5] /* terminal_V */ .info.name,
                  (modelica_real) (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */));
  threadData->lastEquationSolved = 20;
}

/*
equation index: 21
type: SIMPLE_ASSIGN
$START.soc = soc_start
*/
static void smoke_eqFunction_21(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,21};
  ((modelica_real *)((data->modelData->realVarsData[0] /* soc STATE(1) */).attribute .start.data))[0] = (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[5]] /* soc_start PARAM */);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* soc STATE(1) */) = ((modelica_real *)((data->modelData->realVarsData[0] /* soc STATE(1) */).attribute .start.data))[0];
  infoStreamPrint(OMC_LOG_INIT_V, 0,
                  "updated start value: %s(start=%g)",
                  data->modelData->realVarsData[0] /* soc */ .info.name,
                  (modelica_real) (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* soc STATE(1) */));
  threadData->lastEquationSolved = 21;
}
OMC_DISABLE_OPT
int smoke_updateBoundVariableAttributes(DATA *data, threadData_t *threadData)
{
  /* min ******************************************************** */
  infoStreamPrint(OMC_LOG_INIT, 1, "updating min-values");
  messageClose(OMC_LOG_INIT);
  
  /* max ******************************************************** */
  infoStreamPrint(OMC_LOG_INIT, 1, "updating max-values");
  messageClose(OMC_LOG_INIT);
  
  /* nominal **************************************************** */
  infoStreamPrint(OMC_LOG_INIT, 1, "updating nominal-values");
  messageClose(OMC_LOG_INIT);
  
  /* start ****************************************************** */
  infoStreamPrint(OMC_LOG_INIT, 1, "updating primary start-values");
  smoke_eqFunction_20(data, threadData);
  smoke_eqFunction_21(data, threadData);
  messageClose(OMC_LOG_INIT);
  
  return 0;
}

OMC_DISABLE_OPT
int smoke_updateBoundParameters(DATA *data, threadData_t *threadData)
{
  return 0;
}

#if defined(__cplusplus)
}
#endif
