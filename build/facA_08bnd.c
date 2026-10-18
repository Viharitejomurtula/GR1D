/* update bound parameters and variable attributes (start, nominal, min, max) */
#include "facA_model.h"
#if defined(__cplusplus)
extern "C" {
#endif


/*
equation index: 123
type: SIMPLE_ASSIGN
$START.soc = battery_soc0
*/
static void facA_eqFunction_123(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,123};
  ((modelica_real *)((data->modelData->realVarsData[2] /* soc STATE(1) */).attribute .start.data))[0] = (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[3]] /* battery_soc0 PARAM */);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* soc STATE(1) */) = ((modelica_real *)((data->modelData->realVarsData[2] /* soc STATE(1) */).attribute .start.data))[0];
  infoStreamPrint(OMC_LOG_INIT_V, 0,
                  "updated start value: %s(start=%g)",
                  data->modelData->realVarsData[2] /* soc */ .info.name,
                  (modelica_real) (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* soc STATE(1) */));
  threadData->lastEquationSolved = 123;
}
OMC_DISABLE_OPT
int facA_updateBoundVariableAttributes(DATA *data, threadData_t *threadData)
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
  facA_eqFunction_123(data, threadData);
  messageClose(OMC_LOG_INIT);
  
  return 0;
}

void facA_updateBoundParameters_0(DATA *data, threadData_t *threadData);

/*
equation index: 126
type: SIMPLE_ASSIGN
cooling_pump_frac = max(0.0, 1.0 - cooling_compressor_frac - cooling_fan_frac)
*/
OMC_DISABLE_OPT
static void facA_eqFunction_126(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,126};
  (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[8]] /* cooling_pump_frac PARAM */) = fmax(0.0,1.0 - (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[6]] /* cooling_compressor_frac PARAM */) - (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[7]] /* cooling_fan_frac PARAM */));
  threadData->lastEquationSolved = 126;
}

/*
equation index: 127
type: SIMPLE_ASSIGN
bbu_energy_j = p_it_rated_w * bbu_backup_s * max(0.5, 1.0 - 0.025 * battery_age_yr)
*/
OMC_DISABLE_OPT
static void facA_eqFunction_127(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,127};
  (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[5]] /* bbu_energy_j PARAM */) = ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */)) * (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[4]] /* bbu_backup_s PARAM */)) * (fmax(0.5,1.0 - ((0.025) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[2]] /* battery_age_yr PARAM */))))));
  threadData->lastEquationSolved = 127;
}

/*
equation index: 128
type: SIMPLE_ASSIGN
n_psu = 3.333333333333333e-4 * p_it_rated_w
*/
OMC_DISABLE_OPT
static void facA_eqFunction_128(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,128};
  (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[16]] /* n_psu PARAM */) = (3.333333333333333e-4) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */));
  threadData->lastEquationSolved = 128;
}

/*
equation index: 129
type: SIMPLE_ASSIGN
e_holdup_max_j = 60.0 * n_psu
*/
OMC_DISABLE_OPT
static void facA_eqFunction_129(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,129};
  (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[14]] /* e_holdup_max_j PARAM */) = (60.0) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[16]] /* n_psu PARAM */));
  threadData->lastEquationSolved = 129;
}

/*
equation index: 130
type: SIMPLE_ASSIGN
cooling_share = max(0.4 * cooling_share_25c, cooling_share_25c * (1.0 + 0.04 * (outdoor_temp_c - 25.0)))
*/
OMC_DISABLE_OPT
static void facA_eqFunction_130(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,130};
  (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[9]] /* cooling_share PARAM */) = fmax((0.4) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[10]] /* cooling_share_25c PARAM */)),((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[10]] /* cooling_share_25c PARAM */)) * (1.0 + (0.04) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[17]] /* outdoor_temp_c PARAM */) - 25.0)));
  threadData->lastEquationSolved = 130;
}

/*
equation index: 131
type: SIMPLE_ASSIGN
p_cooling_rated_w = cooling_share * p_it_rated_w
*/
OMC_DISABLE_OPT
static void facA_eqFunction_131(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,131};
  (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[18]] /* p_cooling_rated_w PARAM */) = ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[9]] /* cooling_share PARAM */)) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */));
  threadData->lastEquationSolved = 131;
}

/*
equation index: 132
type: SIMPLE_ASSIGN
p_total_rated_w = p_it_rated_w * workload + p_cooling_rated_w
*/
OMC_DISABLE_OPT
static void facA_eqFunction_132(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,132};
  (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[20]] /* p_total_rated_w PARAM */) = ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */)) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[27]] /* workload PARAM */)) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[18]] /* p_cooling_rated_w PARAM */);
  threadData->lastEquationSolved = 132;
}
OMC_DISABLE_OPT
void facA_updateBoundParameters_0(DATA *data, threadData_t *threadData)
{
  static void (*const eqFunctions[7])(DATA*, threadData_t*) = {
    facA_eqFunction_126,
    facA_eqFunction_127,
    facA_eqFunction_128,
    facA_eqFunction_129,
    facA_eqFunction_130,
    facA_eqFunction_131,
    facA_eqFunction_132
  };
  
  for (int id = 0; id < 7; id++) {
    eqFunctions[id](data, threadData);
  }
}
OMC_DISABLE_OPT
int facA_updateBoundParameters(DATA *data, threadData_t *threadData)
{
  (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[0]] /* E_FRAC_BBU PARAM */) = 0.625;
  data->modelData->realParameterData[0].time_unvarying = 1;
  (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[1]] /* E_FRAC_IT_FLOOR PARAM */) = 0.20833333333333337;
  data->modelData->realParameterData[1].time_unvarying = 1;
  facA_updateBoundParameters_0(data, threadData);
  return 0;
}

#if defined(__cplusplus)
}
#endif
