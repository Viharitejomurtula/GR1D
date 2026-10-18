/* Events: Sample, Zero Crossings, Relations, Discrete Changes */
#include "smoke_model.h"
#if defined(__cplusplus)
extern "C" {
#endif

/* Initializes the raw time events of the simulation using the now
   calcualted parameters. */
void smoke_function_initSample(DATA *data, threadData_t *threadData)
{
  long i=0;
}

const char *smoke_zeroCrossingDescription(int i, int **out_EquationIndexes)
{
  static const char *res[] = {"terminal_V < trip_V",
  "power_W <= 0.0"};
  static const int occurEqs0[] = {1,-1};
  static const int occurEqs1[] = {1,-1};
  static const int *occurEqs[] = {occurEqs0,occurEqs1};
  *out_EquationIndexes = (int*) occurEqs[i];
  return res[i];
}

/* forwarded equations */
extern void smoke_eqFunction_13(DATA* data, threadData_t *threadData);
extern void smoke_eqFunction_18(DATA* data, threadData_t *threadData);
extern void smoke_eqFunction_19(DATA* data, threadData_t *threadData);

int smoke_function_ZeroCrossingsEquations(DATA *data, threadData_t *threadData)
{
  data->simulationInfo->callStatistics.functionZeroCrossingsEquations++;

  static void (*const eqFunctions[3])(DATA*, threadData_t*) = {
    smoke_eqFunction_13,
    smoke_eqFunction_18,
    smoke_eqFunction_19
  };
  
  for (int id = 0; id < 3; id++) {
    eqFunctions[id](data, threadData);
  }
  
  return 0;
}

int smoke_function_ZeroCrossings(DATA *data, threadData_t *threadData, double *gout)
{
  const int *equationIndexes = NULL;

  modelica_boolean tmp0;
  modelica_real tmp1;
  modelica_real tmp2;
  modelica_boolean tmp3;
  modelica_real tmp4;
  modelica_real tmp5;
  modelica_integer current_index = 0;
  modelica_integer start_index;
  
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_tick(SIM_TIMER_ZC);
#endif
  data->simulationInfo->callStatistics.functionZeroCrossings++;

  start_index = current_index;
  tmp1 = 1.0;
  tmp2 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[6]] /* trip_V PARAM */));
  tmp0 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */), (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[6]] /* trip_V PARAM */), tmp1, tmp2, data->simulationInfo->storedRelations[0]);
  gout[start_index] = (tmp0) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp4 = 1.0;
  tmp5 = 0.0;
  tmp3 = LessEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power_W variable */), 0.0, tmp4, tmp5, data->simulationInfo->storedRelations[1]);
  gout[start_index] = (tmp3) ? 1 : -1;
  current_index++;

#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_accumulate(SIM_TIMER_ZC);
#endif

  return 0;
}

const char *smoke_relationDescription(int i)
{
  const char *res[] = {"terminal_V < trip_V",
  "power_W <= 0.0"};
  return res[i];
}

int smoke_function_updateRelations(DATA *data, threadData_t *threadData, int evalforZeroCross)
{
  const int *equationIndexes = NULL;

  modelica_boolean tmp6;
  modelica_real tmp7;
  modelica_real tmp8;
  modelica_boolean tmp9;
  modelica_real tmp10;
  modelica_real tmp11;
  modelica_integer current_index = 0;
  modelica_integer start_index;
  
  if(evalforZeroCross) {
    start_index = current_index;
    tmp7 = 1.0;
    tmp8 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[6]] /* trip_V PARAM */));
    tmp6 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */), (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[6]] /* trip_V PARAM */), tmp7, tmp8, data->simulationInfo->storedRelations[0]);
    data->simulationInfo->relations[start_index] = tmp6;
    current_index++;

    start_index = current_index;
    tmp10 = 1.0;
    tmp11 = 0.0;
    tmp9 = LessEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power_W variable */), 0.0, tmp10, tmp11, data->simulationInfo->storedRelations[1]);
    data->simulationInfo->relations[start_index] = tmp9;
    current_index++;
  } else {
    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* terminal_V variable */) < (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[6]] /* trip_V PARAM */));
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power_W variable */) <= 0.0);
    current_index++;
  }
  
  return 0;
}

#if defined(__cplusplus)
}
#endif
