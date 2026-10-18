/* Main Simulation File */

#if defined(__cplusplus)
extern "C" {
#endif

#include "RideThroughCore_model.h"
#include "simulation/solver/events.h"
#include "simulation/arrayIndex.h"

/* FIXME these defines are ugly and hard to read, why not use direct function pointers instead? */
#define prefixedName_performSimulation RideThroughCore_performSimulation
#define prefixedName_updateContinuousSystem RideThroughCore_updateContinuousSystem
#include <simulation/solver/perform_simulation.c.inc>

#define prefixedName_performQSSSimulation RideThroughCore_performQSSSimulation
#include <simulation/solver/perform_qss_simulation.c.inc>


/* dummy VARINFO and FILEINFO */
const VAR_INFO dummyVAR_INFO = omc_dummyVarInfo;

int RideThroughCore_input_function(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int RideThroughCore_input_function_init(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int RideThroughCore_input_function_updateStartValues(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int RideThroughCore_inputNames(DATA *data, char ** names){
  
  return 0;
}

int RideThroughCore_data_function(DATA *data, threadData_t *threadData)
{
  return 0;
}

int RideThroughCore_dataReconciliationInputNames(DATA *data, char ** names){
  
  return 0;
}

int RideThroughCore_dataReconciliationUnmeasuredVariables(DATA *data, char ** names)
{
  
  return 0;
}

int RideThroughCore_output_function(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int RideThroughCore_setc_function(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int RideThroughCore_setb_function(DATA *data, threadData_t *threadData)
{
  
  return 0;
}


/*
equation index: 62
type: SIMPLE_ASSIGN
$cse2 = min(1.0, e_holdup_j / e_holdup_max_j)
*/
void RideThroughCore_eqFunction_62(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,62};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[21]] /* $cse2 variable */) = fmin(1.0,DIVISION_SIM((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* e_holdup_j STATE(1) */),(data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[14]] /* e_holdup_max_j PARAM */),"e_holdup_max_j",equationIndexes));
  threadData->lastEquationSolved = 62;
}

/*
equation index: 63
type: SIMPLE_ASSIGN
e_frac = max(0.0, $cse2)
*/
void RideThroughCore_eqFunction_63(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,63};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */) = fmax(0.0,(data->localData[0]->realVars[data->simulationInfo->realVarsIndex[21]] /* $cse2 variable */));
  threadData->lastEquationSolved = 63;
}

/*
equation index: 64
type: SIMPLE_ASSIGN
$cse3 = sin(6.283185307179586 * swing_freq_hz * time + swing_phase)
*/
void RideThroughCore_eqFunction_64(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,64};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[22]] /* $cse3 variable */) = sin(((6.283185307179586) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[24]] /* swing_freq_hz PARAM */))) * (data->localData[0]->timeValue) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[25]] /* swing_phase PARAM */));
  threadData->lastEquationSolved = 64;
}

/*
equation index: 65
type: SIMPLE_ASSIGN
$whenCondition13 = v_sense_pu >= 0.7
*/
void RideThroughCore_eqFunction_65(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,65};
  modelica_boolean tmp0;
  modelica_real tmp1;
  modelica_real tmp2;
  tmp1 = 1.0;
  tmp2 = 0.7;
  relationhysteresis(data, &tmp0, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.7, tmp1, tmp2, 26, GreaterEq, GreaterEqZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[4]] /* $whenCondition13 DISCRETE */) = tmp0;
  threadData->lastEquationSolved = 65;
}

/*
equation index: 66
type: SIMPLE_ASSIGN
$whenCondition12 = v_sense_pu >= 0.6
*/
void RideThroughCore_eqFunction_66(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,66};
  modelica_boolean tmp3;
  modelica_real tmp4;
  modelica_real tmp5;
  tmp4 = 1.0;
  tmp5 = 0.6;
  relationhysteresis(data, &tmp3, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.6, tmp4, tmp5, 25, GreaterEq, GreaterEqZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[3]] /* $whenCondition12 DISCRETE */) = tmp3;
  threadData->lastEquationSolved = 66;
}

/*
equation index: 67
type: SIMPLE_ASSIGN
$whenCondition11 = v_sense_pu <= 0.5
*/
void RideThroughCore_eqFunction_67(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,67};
  modelica_boolean tmp6;
  modelica_real tmp7;
  modelica_real tmp8;
  tmp7 = 1.0;
  tmp8 = 0.5;
  relationhysteresis(data, &tmp6, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.5, tmp7, tmp8, 24, LessEq, LessEqZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[2]] /* $whenCondition11 DISCRETE */) = tmp6;
  threadData->lastEquationSolved = 67;
}

/*
equation index: 68
type: SIMPLE_ASSIGN
$whenCondition10 = e_frac >= 0.625
*/
void RideThroughCore_eqFunction_68(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,68};
  modelica_boolean tmp9;
  modelica_real tmp10;
  modelica_real tmp11;
  tmp10 = 1.0;
  tmp11 = 0.625;
  relationhysteresis(data, &tmp9, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp10, tmp11, 23, GreaterEq, GreaterEqZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[1]] /* $whenCondition10 DISCRETE */) = tmp9;
  threadData->lastEquationSolved = 68;
}

/*
equation index: 69
type: SIMPLE_ASSIGN
$whenCondition8 = t_cool_s1 > 0.05
*/
void RideThroughCore_eqFunction_69(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,69};
  modelica_boolean tmp12;
  modelica_real tmp13;
  modelica_real tmp14;
  tmp13 = 1.0;
  tmp14 = 0.05;
  relationhysteresis(data, &tmp12, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[6]] /* t_cool_s1 STATE(1) */), 0.05, tmp13, tmp14, 21, Greater, GreaterZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[11]] /* $whenCondition8 DISCRETE */) = tmp12;
  threadData->lastEquationSolved = 69;
}

/*
equation index: 70
type: SIMPLE_ASSIGN
$whenCondition7 = t_cool_s2 > 0.02
*/
void RideThroughCore_eqFunction_70(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,70};
  modelica_boolean tmp15;
  modelica_real tmp16;
  modelica_real tmp17;
  tmp16 = 1.0;
  tmp17 = 0.02;
  relationhysteresis(data, &tmp15, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[7]] /* t_cool_s2 STATE(1) */), 0.02, tmp16, tmp17, 20, Greater, GreaterZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[10]] /* $whenCondition7 DISCRETE */) = tmp15;
  threadData->lastEquationSolved = 70;
}

/*
equation index: 71
type: SIMPLE_ASSIGN
$whenCondition5 = supply_voltage_v * v_sense_pu > 178.0 and t_psu_down > 1.0 + psu_restart_delay_s
*/
void RideThroughCore_eqFunction_71(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,71};
  modelica_boolean tmp18;
  modelica_real tmp19;
  modelica_real tmp20;
  modelica_boolean tmp21;
  modelica_real tmp22;
  modelica_real tmp23;
  tmp19 = (fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */))) * (1.0);
  tmp20 = 178.0;
  relationhysteresis(data, &tmp18, ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */)), 178.0, tmp19, tmp20, 18, Greater, GreaterZC);
  tmp22 = 1.0;
  tmp23 = 1.0 + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[21]] /* psu_restart_delay_s PARAM */));
  relationhysteresis(data, &tmp21, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[8]] /* t_psu_down STATE(1) */), 1.0 + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[21]] /* psu_restart_delay_s PARAM */), tmp22, tmp23, 19, Greater, GreaterZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[8]] /* $whenCondition5 DISCRETE */) = (tmp18 && tmp21);
  threadData->lastEquationSolved = 71;
}

/*
equation index: 72
type: SIMPLE_ASSIGN
$whenCondition6 = supply_voltage_v * v_sense_pu < 172.0
*/
void RideThroughCore_eqFunction_72(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,72};
  modelica_boolean tmp24;
  modelica_real tmp25;
  modelica_real tmp26;
  tmp25 = (fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */))) * (1.0);
  tmp26 = 172.0;
  relationhysteresis(data, &tmp24, ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */)), 172.0, tmp25, tmp26, 17, Less, LessZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[9]] /* $whenCondition6 DISCRETE */) = tmp24;
  threadData->lastEquationSolved = 72;
}

/*
equation index: 73
type: SIMPLE_ASSIGN
$whenCondition3 = t_bus_ok > handback_delay_s
*/
void RideThroughCore_eqFunction_73(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,73};
  modelica_boolean tmp27;
  modelica_real tmp28;
  modelica_real tmp29;
  tmp28 = 1.0;
  tmp29 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[15]] /* handback_delay_s PARAM */));
  relationhysteresis(data, &tmp27, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* t_bus_ok STATE(1) */), (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[15]] /* handback_delay_s PARAM */), tmp28, tmp29, 16, Greater, GreaterZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[6]] /* $whenCondition3 DISCRETE */) = tmp27;
  threadData->lastEquationSolved = 73;
}

/*
equation index: 74
type: SIMPLE_ASSIGN
$whenCondition4 = t_bus_low > 0.002
*/
void RideThroughCore_eqFunction_74(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,74};
  modelica_boolean tmp30;
  modelica_real tmp31;
  modelica_real tmp32;
  tmp31 = 1.0;
  tmp32 = 0.002;
  relationhysteresis(data, &tmp30, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* t_bus_low STATE(1) */), 0.002, tmp31, tmp32, 15, Greater, GreaterZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[7]] /* $whenCondition4 DISCRETE */) = tmp30;
  threadData->lastEquationSolved = 74;
}

/*
equation index: 75
type: WHEN

when {$whenCondition8} then
  cool_s1_tripped = true;
end when;
*/
void RideThroughCore_eqFunction_75(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,75};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[11]] /* $whenCondition8 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[11] /* $whenCondition8 DISCRETE */) /* edge */))
  {
    (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[14]] /* cool_s1_tripped DISCRETE */) = 1 /* true */;
  }
  threadData->lastEquationSolved = 75;
}

/*
equation index: 76
type: WHEN

when {$whenCondition7} then
  cool_s2_tripped = true;
end when;
*/
void RideThroughCore_eqFunction_76(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,76};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[10]] /* $whenCondition7 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[10] /* $whenCondition7 DISCRETE */) /* edge */))
  {
    (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[15]] /* cool_s2_tripped DISCRETE */) = 1 /* true */;
  }
  threadData->lastEquationSolved = 76;
}

/*
equation index: 77
type: WHEN

when {$whenCondition6} then
  psu_enabled = false;
end when;
*/
void RideThroughCore_eqFunction_77(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,77};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[9]] /* $whenCondition6 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[9] /* $whenCondition6 DISCRETE */) /* edge */))
  {
    (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */) = 0 /* false */;
  }
  else if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[8]] /* $whenCondition5 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[8] /* $whenCondition5 DISCRETE */) /* edge */))
  {
    (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */) = 1 /* true */;
  }
  threadData->lastEquationSolved = 77;
}

/*
equation index: 79
type: SIMPLE_ASSIGN
$whenCondition1 = e_frac > 0.625 and psu_enabled
*/
void RideThroughCore_eqFunction_79(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,79};
  modelica_boolean tmp33;
  modelica_real tmp34;
  modelica_real tmp35;
  tmp34 = 1.0;
  tmp35 = 0.625;
  relationhysteresis(data, &tmp33, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp34, tmp35, 12, Greater, GreaterZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[0]] /* $whenCondition1 DISCRETE */) = (tmp33 && (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */));
  threadData->lastEquationSolved = 79;
}

/*
equation index: 80
type: SIMPLE_ASSIGN
$whenCondition9 = e_frac <= 0.625 or not psu_enabled
*/
void RideThroughCore_eqFunction_80(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,80};
  modelica_boolean tmp36;
  modelica_real tmp37;
  modelica_real tmp38;
  tmp37 = 1.0;
  tmp38 = 0.625;
  relationhysteresis(data, &tmp36, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp37, tmp38, 22, LessEq, LessEqZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[12]] /* $whenCondition9 DISCRETE */) = (tmp36 || (!(data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */)));
  threadData->lastEquationSolved = 80;
}

/*
equation index: 81
type: WHEN

when {$whenCondition4} then
  bbu_active = true;
end when;
*/
void RideThroughCore_eqFunction_81(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,81};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[7]] /* $whenCondition4 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[7] /* $whenCondition4 DISCRETE */) /* edge */))
  {
    (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[13]] /* bbu_active DISCRETE */) = 1 /* true */;
  }
  else if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[6]] /* $whenCondition3 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[6] /* $whenCondition3 DISCRETE */) /* edge */))
  {
    (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[13]] /* bbu_active DISCRETE */) = 0 /* false */;
  }
  threadData->lastEquationSolved = 81;
}

/*
equation index: 83
type: SIMPLE_ASSIGN
$whenCondition2 = e_frac < 0.20833333333333337 and not bbu_active
*/
void RideThroughCore_eqFunction_83(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,83};
  modelica_boolean tmp39;
  modelica_real tmp40;
  modelica_real tmp41;
  tmp40 = 1.0;
  tmp41 = 0.20833333333333337;
  relationhysteresis(data, &tmp39, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.20833333333333337, tmp40, tmp41, 14, Less, LessZC);
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[5]] /* $whenCondition2 DISCRETE */) = (tmp39 && (!(data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[13]] /* bbu_active DISCRETE */)));
  threadData->lastEquationSolved = 83;
}

/*
equation index: 84
type: WHEN

when {$whenCondition2} then
  servers_lost_power = true;
end when;
*/
void RideThroughCore_eqFunction_84(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,84};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[5]] /* $whenCondition2 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[5] /* $whenCondition2 DISCRETE */) /* edge */))
  {
    (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[17]] /* servers_lost_power DISCRETE */) = 1 /* true */;
  }
  else if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[0]] /* $whenCondition1 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[0] /* $whenCondition1 DISCRETE */) /* edge */))
  {
    (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[17]] /* servers_lost_power DISCRETE */) = 0 /* false */;
  }
  threadData->lastEquationSolved = 84;
}

/*
equation index: 86
type: SIMPLE_ASSIGN
$DER.t_bus_ok = if psu_enabled and e_frac > 0.625 then 1.0 else 0.0
*/
void RideThroughCore_eqFunction_86(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,86};
  modelica_boolean tmp42;
  modelica_real tmp43;
  modelica_real tmp44;
  tmp43 = 1.0;
  tmp44 = 0.625;
  relationhysteresis(data, &tmp42, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp43, tmp44, 12, Greater, GreaterZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[14]] /* der(t_bus_ok) STATE_DER */) = (((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */) && tmp42)?1.0:0.0);
  threadData->lastEquationSolved = 86;
}

/*
equation index: 87
type: SIMPLE_ASSIGN
$DER.t_bus_low = if e_frac < 0.625 then 1.0 else 0.0
*/
void RideThroughCore_eqFunction_87(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,87};
  modelica_boolean tmp45;
  modelica_real tmp46;
  modelica_real tmp47;
  tmp46 = 1.0;
  tmp47 = 0.625;
  relationhysteresis(data, &tmp45, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp46, tmp47, 11, Less, LessZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[13]] /* der(t_bus_low) STATE_DER */) = (tmp45?1.0:0.0);
  threadData->lastEquationSolved = 87;
}

/*
equation index: 88
type: SIMPLE_ASSIGN
v_bus_v = if bbu_active and soc > 0.0 then 48.0 else 50.75 - 6.0 * (1.0 - e_frac)
*/
void RideThroughCore_eqFunction_88(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,88};
  modelica_boolean tmp48;
  modelica_real tmp49;
  modelica_real tmp50;
  tmp49 = 1.0;
  tmp50 = 0.0;
  relationhysteresis(data, &tmp48, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* soc STATE(1) */), 0.0, tmp49, tmp50, 10, Greater, GreaterZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[34]] /* v_bus_v variable */) = (((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[13]] /* bbu_active DISCRETE */) && tmp48)?48.0:50.75 - ((6.0) * (1.0 - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */))));
  threadData->lastEquationSolved = 88;
}

/*
equation index: 89
type: SIMPLE_ASSIGN
$DER.t_psu_down = if psu_enabled then 0.0 else 1.0
*/
void RideThroughCore_eqFunction_89(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,89};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[18]] /* der(t_psu_down) STATE_DER */) = ((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */)?0.0:1.0);
  threadData->lastEquationSolved = 89;
}

/*
equation index: 90
type: SIMPLE_ASSIGN
cooling_available = (if cool_s2_tripped then 0.30000000000000004 else if cool_s1_tripped then 0.7 else 1.0) * cooling_compressor_frac + (if cool_s2_tripped and t_cool_ok < 0.25 then 0.5 else if cool_s1_tripped and t_cool_ok < 0.25 then 0.7 else 1.0) * (cooling_fan_frac + cooling_pump_frac)
*/
void RideThroughCore_eqFunction_90(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,90};
  modelica_boolean tmp51;
  modelica_real tmp52;
  modelica_real tmp53;
  modelica_boolean tmp54;
  modelica_real tmp55;
  modelica_real tmp56;
  modelica_boolean tmp57;
  modelica_real tmp58;
  tmp52 = 1.0;
  tmp53 = 0.25;
  relationhysteresis(data, &tmp51, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* t_cool_ok STATE(1) */), 0.25, tmp52, tmp53, 8, Less, LessZC);
  tmp57 = (modelica_boolean)((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[15]] /* cool_s2_tripped DISCRETE */) && tmp51);
  if(tmp57)
  {
    tmp58 = 0.5;
  }
  else
  {
    tmp55 = 1.0;
    tmp56 = 0.25;
    relationhysteresis(data, &tmp54, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* t_cool_ok STATE(1) */), 0.25, tmp55, tmp56, 8, Less, LessZC);
    tmp58 = (((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[14]] /* cool_s1_tripped DISCRETE */) && tmp54)?0.7:1.0);
  }
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[25]] /* cooling_available variable */) = (((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[15]] /* cool_s2_tripped DISCRETE */)?0.30000000000000004:((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[14]] /* cool_s1_tripped DISCRETE */)?0.7:1.0))) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[6]] /* cooling_compressor_frac PARAM */)) + (tmp58) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[7]] /* cooling_fan_frac PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[8]] /* cooling_pump_frac PARAM */));
  threadData->lastEquationSolved = 90;
}

/*
equation index: 91
type: SIMPLE_ASSIGN
p_cooling_w = p_cooling_rated_w * cooling_available
*/
void RideThroughCore_eqFunction_91(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,91};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[29]] /* p_cooling_w variable */) = ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[18]] /* p_cooling_rated_w PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[25]] /* cooling_available variable */));
  threadData->lastEquationSolved = 91;
}

/*
equation index: 92
type: SIMPLE_ASSIGN
$DER.t_cool_ok = if v_sense_pu > 0.5 then 1.0 else 0.0
*/
void RideThroughCore_eqFunction_92(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,92};
  modelica_boolean tmp59;
  modelica_real tmp60;
  modelica_real tmp61;
  tmp60 = 1.0;
  tmp61 = 0.5;
  relationhysteresis(data, &tmp59, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.5, tmp60, tmp61, 7, Greater, GreaterZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[15]] /* der(t_cool_ok) STATE_DER */) = (tmp59?1.0:0.0);
  threadData->lastEquationSolved = 92;
}

/*
equation index: 93
type: SIMPLE_ASSIGN
$DER.t_cool_s2 = if v_sense_pu < 0.6 then 1.0 else 0.0
*/
void RideThroughCore_eqFunction_93(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,93};
  modelica_boolean tmp62;
  modelica_real tmp63;
  modelica_real tmp64;
  tmp63 = 1.0;
  tmp64 = 0.6;
  relationhysteresis(data, &tmp62, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.6, tmp63, tmp64, 6, Less, LessZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[17]] /* der(t_cool_s2) STATE_DER */) = (tmp62?1.0:0.0);
  threadData->lastEquationSolved = 93;
}

/*
equation index: 94
type: SIMPLE_ASSIGN
$DER.t_cool_s1 = if v_sense_pu < 0.7 then 1.0 else 0.0
*/
void RideThroughCore_eqFunction_94(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,94};
  modelica_boolean tmp65;
  modelica_real tmp66;
  modelica_real tmp67;
  tmp66 = 1.0;
  tmp67 = 0.7;
  relationhysteresis(data, &tmp65, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.7, tmp66, tmp67, 5, Less, LessZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[16]] /* der(t_cool_s1) STATE_DER */) = (tmp65?1.0:0.0);
  threadData->lastEquationSolved = 94;
}

/*
equation index: 95
type: SIMPLE_ASSIGN
p_server_w = if servers_lost_power then 0.0 else workload * p_it_rated_w + p_swing_w
*/
void RideThroughCore_eqFunction_95(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,95};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */) = ((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[17]] /* servers_lost_power DISCRETE */)?0.0:((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[27]] /* workload PARAM */)) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */)) + (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[1]] /* p_swing_w STATE(1) */));
  threadData->lastEquationSolved = 95;
}

/*
equation index: 96
type: SIMPLE_ASSIGN
p_swing_target_w = 0.5 * swing_size_frac * p_it_rated_w * (if $cse3 >= 0.0 then 1.0 else -1.0)
*/
void RideThroughCore_eqFunction_96(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,96};
  modelica_boolean tmp68;
  modelica_real tmp69;
  modelica_real tmp70;
  tmp69 = 1.0;
  tmp70 = 0.0;
  relationhysteresis(data, &tmp68, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[22]] /* $cse3 variable */), 0.0, tmp69, tmp70, 4, GreaterEq, GreaterEqZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[33]] /* p_swing_target_w variable */) = (0.5) * (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[26]] /* swing_size_frac PARAM */)) * (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */)) * ((tmp68?1.0:-1.0))));
  threadData->lastEquationSolved = 96;
}

/*
equation index: 97
type: SIMPLE_ASSIGN
$cse5 = min(1.9 * p_it_rated_w, 1000.0 * (p_swing_target_w - p_swing_w))
*/
void RideThroughCore_eqFunction_97(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,97};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[24]] /* $cse5 variable */) = fmin((1.9) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */)),(1000.0) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[33]] /* p_swing_target_w variable */) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[1]] /* p_swing_w STATE(1) */)));
  threadData->lastEquationSolved = 97;
}

/*
equation index: 98
type: SIMPLE_ASSIGN
$cse4 = max((-1.9) * p_it_rated_w, $cse5)
*/
void RideThroughCore_eqFunction_98(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,98};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[23]] /* $cse4 variable */) = fmax((-1.9) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */)),(data->localData[0]->realVars[data->simulationInfo->realVarsIndex[24]] /* $cse5 variable */));
  threadData->lastEquationSolved = 98;
}

/*
equation index: 99
type: SIMPLE_ASSIGN
$DER.p_swing_w = $cse4
*/
void RideThroughCore_eqFunction_99(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,99};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[11]] /* der(p_swing_w) STATE_DER */) = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[23]] /* $cse4 variable */);
  threadData->lastEquationSolved = 99;
}

/*
equation index: 100
type: SIMPLE_ASSIGN
v_source_pu = if time >= dip_start_s and time < dip_start_s + dip_duration_s then dip_depth_pu else if second_dip and time >= dip_start_s + dip_duration_s + reclose_gap_s and time < dip_start_s + 2.0 * dip_duration_s + reclose_gap_s then dip_depth_pu else 1.0
*/
void RideThroughCore_eqFunction_100(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,100};
  modelica_boolean tmp71;
  modelica_real tmp72;
  modelica_real tmp73;
  modelica_boolean tmp74;
  modelica_real tmp75;
  modelica_real tmp76;
  modelica_boolean tmp77;
  modelica_real tmp78;
  modelica_real tmp79;
  modelica_boolean tmp80;
  modelica_real tmp81;
  modelica_real tmp82;
  modelica_boolean tmp83;
  modelica_real tmp84;
  tmp72 = 1.0;
  tmp73 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */));
  relationhysteresis(data, &tmp71, data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */), tmp72, tmp73, 0, GreaterEq, GreaterEqZC);
  tmp75 = 1.0;
  tmp76 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */)) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */));
  relationhysteresis(data, &tmp74, data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */), tmp75, tmp76, 1, Less, LessZC);
  tmp83 = (modelica_boolean)(tmp71 && tmp74);
  if(tmp83)
  {
    tmp84 = (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[11]] /* dip_depth_pu PARAM */);
  }
  else
  {
    tmp78 = 1.0;
    tmp79 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */)) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */)) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */));
    relationhysteresis(data, &tmp77, data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */), tmp78, tmp79, 2, GreaterEq, GreaterEqZC);
    tmp81 = 1.0;
    tmp82 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */)) + (2.0) * (fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */))) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */));
    relationhysteresis(data, &tmp80, data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (2.0) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */)) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */), tmp81, tmp82, 3, Less, LessZC);
    tmp84 = ((((data->simulationInfo->booleanParameter[data->simulationInfo->booleanParamsIndex[0]] /* second_dip PARAM */) && tmp77) && tmp80)?(data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[11]] /* dip_depth_pu PARAM */):1.0);
  }
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[37]] /* v_source_pu variable */) = tmp84;
  threadData->lastEquationSolved = 100;
}

void RideThroughCore_eqFunction_101(DATA*, threadData_t*);
void RideThroughCore_eqFunction_102(DATA*, threadData_t*);
void RideThroughCore_eqFunction_103(DATA*, threadData_t*);
void RideThroughCore_eqFunction_104(DATA*, threadData_t*);
void RideThroughCore_eqFunction_105(DATA*, threadData_t*);
/*
equation index: 111
indexNonlinear: 1
type: NONLINEAR

vars: {v_sdp_pu}
eqns: {101, 102, 103, 104, 105}
*/
void RideThroughCore_eqFunction_111(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,111};
  int retValue;
  infoStreamPrint(OMC_LOG_DT, 0, "Solving nonlinear system 111 (STRICT TEARING SET if tearing enabled) at time = %18.10e", data->localData[0]->timeValue);
  /* get old value */
  data->simulationInfo->nonlinearSystemData[1].nlsxOld[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */);
  retValue = solve_nonlinear_system(data, threadData, 1);
  /* check if solution process was successful */
  if (retValue > 0){
    const int indexes[2] = {1,111};
    throwStreamPrintWithEquationIndexes(threadData, omc_dummyFileInfo, indexes, "Solving non-linear system 111 failed at time=%.15g.\nFor more information please use -lv LOG_NLS.", data->localData[0]->timeValue);
  }
  /* write solution */
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */) = data->simulationInfo->nonlinearSystemData[1].nlsx[0];
  threadData->lastEquationSolved = 111;
}

/*
equation index: 112
type: SIMPLE_ASSIGN
v_psu_in_v = supply_voltage_v * $cse1
*/
void RideThroughCore_eqFunction_112(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,112};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[35]] /* v_psu_in_v variable */) = ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[20]] /* $cse1 variable */));
  threadData->lastEquationSolved = 112;
}

/*
equation index: 113
type: SIMPLE_ASSIGN
$DER.v_sense_pu = 1000.0 * (v_sdp_pu - v_sense_pu)
*/
void RideThroughCore_eqFunction_113(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,113};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[19]] /* der(v_sense_pu) STATE_DER */) = (1000.0) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */));
  threadData->lastEquationSolved = 113;
}

/*
equation index: 114
type: SIMPLE_ASSIGN
p_bbu_w = if bbu_active and soc > 0.0 then max(0.0, p_server_w - p_psu_w) else 0.0
*/
void RideThroughCore_eqFunction_114(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,114};
  modelica_boolean tmp85;
  modelica_real tmp86;
  modelica_real tmp87;
  tmp86 = 1.0;
  tmp87 = 0.0;
  relationhysteresis(data, &tmp85, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* soc STATE(1) */), 0.0, tmp86, tmp87, 10, Greater, GreaterZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[28]] /* p_bbu_w variable */) = (((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[13]] /* bbu_active DISCRETE */) && tmp85)?fmax(0.0,(data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[31]] /* p_psu_w variable */)):0.0);
  threadData->lastEquationSolved = 114;
}

/*
equation index: 115
type: SIMPLE_ASSIGN
$DER.e_holdup_j = if psu_enabled and p_psu_w >= p_server_w then max(0.0, 20.0 * (e_holdup_max_j - e_holdup_j)) else p_bbu_w - (p_server_w - p_psu_w)
*/
void RideThroughCore_eqFunction_115(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,115};
  modelica_boolean tmp88;
  modelica_real tmp89;
  modelica_real tmp90;
  tmp89 = 1.0;
  tmp90 = 1.0;
  relationhysteresis(data, &tmp88, (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[31]] /* p_psu_w variable */), (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */), tmp89, tmp90, 9, GreaterEq, GreaterEqZC);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[10]] /* der(e_holdup_j) STATE_DER */) = (((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */) && tmp88)?fmax(0.0,(20.0) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[14]] /* e_holdup_max_j PARAM */) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* e_holdup_j STATE(1) */))):(data->localData[0]->realVars[data->simulationInfo->realVarsIndex[28]] /* p_bbu_w variable */) - ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[31]] /* p_psu_w variable */)));
  threadData->lastEquationSolved = 115;
}

/*
equation index: 116
type: SIMPLE_ASSIGN
$DER.soc = (-p_bbu_w) / bbu_energy_j
*/
void RideThroughCore_eqFunction_116(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,116};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[12]] /* der(soc) STATE_DER */) = DIVISION_SIM((-(data->localData[0]->realVars[data->simulationInfo->realVarsIndex[28]] /* p_bbu_w variable */)),(data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[5]] /* bbu_energy_j PARAM */),"bbu_energy_j",equationIndexes);
  threadData->lastEquationSolved = 116;
}

/*
equation index: 122
type: WHEN

when {$whenCondition13} then
  reinit(t_cool_s1,  0.0);
end when;
*/
void RideThroughCore_eqFunction_122(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,122};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[4]] /* $whenCondition13 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[4] /* $whenCondition13 DISCRETE */) /* edge */))
  {
    (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[6]] /* t_cool_s1 STATE(1) */) = 0.0;
    infoStreamPrint(OMC_LOG_EVENTS, 0, "reinit t_cool_s1 = %g", (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[6]] /* t_cool_s1 STATE(1) */));
    data->simulationInfo->needToIterate = 1;
  }
  threadData->lastEquationSolved = 122;
}

/*
equation index: 121
type: WHEN

when {$whenCondition12} then
  reinit(t_cool_s2,  0.0);
end when;
*/
void RideThroughCore_eqFunction_121(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,121};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[3]] /* $whenCondition12 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[3] /* $whenCondition12 DISCRETE */) /* edge */))
  {
    (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[7]] /* t_cool_s2 STATE(1) */) = 0.0;
    infoStreamPrint(OMC_LOG_EVENTS, 0, "reinit t_cool_s2 = %g", (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[7]] /* t_cool_s2 STATE(1) */));
    data->simulationInfo->needToIterate = 1;
  }
  threadData->lastEquationSolved = 121;
}

/*
equation index: 120
type: WHEN

when {$whenCondition11} then
  reinit(t_cool_ok,  0.0);
end when;
*/
void RideThroughCore_eqFunction_120(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,120};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[2]] /* $whenCondition11 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[2] /* $whenCondition11 DISCRETE */) /* edge */))
  {
    (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* t_cool_ok STATE(1) */) = 0.0;
    infoStreamPrint(OMC_LOG_EVENTS, 0, "reinit t_cool_ok = %g", (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* t_cool_ok STATE(1) */));
    data->simulationInfo->needToIterate = 1;
  }
  threadData->lastEquationSolved = 120;
}

/*
equation index: 119
type: WHEN

when {$whenCondition6} then
  reinit(t_psu_down,  0.0);
end when;
*/
void RideThroughCore_eqFunction_119(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,119};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[9]] /* $whenCondition6 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[9] /* $whenCondition6 DISCRETE */) /* edge */))
  {
    (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[8]] /* t_psu_down STATE(1) */) = 0.0;
    infoStreamPrint(OMC_LOG_EVENTS, 0, "reinit t_psu_down = %g", (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[8]] /* t_psu_down STATE(1) */));
    data->simulationInfo->needToIterate = 1;
  }
  threadData->lastEquationSolved = 119;
}

/*
equation index: 118
type: WHEN

when {$whenCondition10} then
  reinit(t_bus_low,  0.0);
end when;
*/
void RideThroughCore_eqFunction_118(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,118};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[1]] /* $whenCondition10 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[1] /* $whenCondition10 DISCRETE */) /* edge */))
  {
    (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* t_bus_low STATE(1) */) = 0.0;
    infoStreamPrint(OMC_LOG_EVENTS, 0, "reinit t_bus_low = %g", (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* t_bus_low STATE(1) */));
    data->simulationInfo->needToIterate = 1;
  }
  threadData->lastEquationSolved = 118;
}

/*
equation index: 117
type: WHEN

when {$whenCondition9} then
  reinit(t_bus_ok,  0.0);
end when;
*/
void RideThroughCore_eqFunction_117(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,117};
  if(((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[12]] /* $whenCondition9 DISCRETE */) && !(data->simulationInfo->booleanVarsPre[12] /* $whenCondition9 DISCRETE */) /* edge */))
  {
    (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* t_bus_ok STATE(1) */) = 0.0;
    infoStreamPrint(OMC_LOG_EVENTS, 0, "reinit t_bus_ok = %g", (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* t_bus_ok STATE(1) */));
    data->simulationInfo->needToIterate = 1;
  }
  threadData->lastEquationSolved = 117;
}

OMC_DISABLE_OPT
int RideThroughCore_functionDAE(DATA *data, threadData_t *threadData)
{
  int equationIndexes[1] = {0};
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_tick(SIM_TIMER_DAE);
#endif

  data->simulationInfo->needToIterate = 0;
  data->simulationInfo->discreteCall = 1;
  RideThroughCore_functionLocalKnownVars(data, threadData);
  static void (*const eqFunctions[48])(DATA*, threadData_t*) = {
    RideThroughCore_eqFunction_62,
    RideThroughCore_eqFunction_63,
    RideThroughCore_eqFunction_64,
    RideThroughCore_eqFunction_65,
    RideThroughCore_eqFunction_66,
    RideThroughCore_eqFunction_67,
    RideThroughCore_eqFunction_68,
    RideThroughCore_eqFunction_69,
    RideThroughCore_eqFunction_70,
    RideThroughCore_eqFunction_71,
    RideThroughCore_eqFunction_72,
    RideThroughCore_eqFunction_73,
    RideThroughCore_eqFunction_74,
    RideThroughCore_eqFunction_75,
    RideThroughCore_eqFunction_76,
    RideThroughCore_eqFunction_77,
    RideThroughCore_eqFunction_79,
    RideThroughCore_eqFunction_80,
    RideThroughCore_eqFunction_81,
    RideThroughCore_eqFunction_83,
    RideThroughCore_eqFunction_84,
    RideThroughCore_eqFunction_86,
    RideThroughCore_eqFunction_87,
    RideThroughCore_eqFunction_88,
    RideThroughCore_eqFunction_89,
    RideThroughCore_eqFunction_90,
    RideThroughCore_eqFunction_91,
    RideThroughCore_eqFunction_92,
    RideThroughCore_eqFunction_93,
    RideThroughCore_eqFunction_94,
    RideThroughCore_eqFunction_95,
    RideThroughCore_eqFunction_96,
    RideThroughCore_eqFunction_97,
    RideThroughCore_eqFunction_98,
    RideThroughCore_eqFunction_99,
    RideThroughCore_eqFunction_100,
    RideThroughCore_eqFunction_111,
    RideThroughCore_eqFunction_112,
    RideThroughCore_eqFunction_113,
    RideThroughCore_eqFunction_114,
    RideThroughCore_eqFunction_115,
    RideThroughCore_eqFunction_116,
    RideThroughCore_eqFunction_122,
    RideThroughCore_eqFunction_121,
    RideThroughCore_eqFunction_120,
    RideThroughCore_eqFunction_119,
    RideThroughCore_eqFunction_118,
    RideThroughCore_eqFunction_117
  };
  
  for (int id = 0; id < 48; id++) {
    eqFunctions[id](data, threadData);
  }
  data->simulationInfo->discreteCall = 0;
  
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_accumulate(SIM_TIMER_DAE);
#endif
  return 0;
}


int RideThroughCore_functionLocalKnownVars(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

/* forwarded equations */
extern void RideThroughCore_eqFunction_62(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_63(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_64(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_69(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_70(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_71(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_72(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_73(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_74(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_79(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_83(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_86(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_87(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_89(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_90(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_91(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_92(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_93(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_94(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_95(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_96(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_97(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_98(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_99(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_100(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_111(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_113(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_114(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_115(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_116(DATA* data, threadData_t *threadData);

static void functionODE_system0(DATA *data, threadData_t *threadData)
{
  static void (*const eqFunctions[30])(DATA*, threadData_t*) = {
    RideThroughCore_eqFunction_62,
    RideThroughCore_eqFunction_63,
    RideThroughCore_eqFunction_64,
    RideThroughCore_eqFunction_69,
    RideThroughCore_eqFunction_70,
    RideThroughCore_eqFunction_71,
    RideThroughCore_eqFunction_72,
    RideThroughCore_eqFunction_73,
    RideThroughCore_eqFunction_74,
    RideThroughCore_eqFunction_79,
    RideThroughCore_eqFunction_83,
    RideThroughCore_eqFunction_86,
    RideThroughCore_eqFunction_87,
    RideThroughCore_eqFunction_89,
    RideThroughCore_eqFunction_90,
    RideThroughCore_eqFunction_91,
    RideThroughCore_eqFunction_92,
    RideThroughCore_eqFunction_93,
    RideThroughCore_eqFunction_94,
    RideThroughCore_eqFunction_95,
    RideThroughCore_eqFunction_96,
    RideThroughCore_eqFunction_97,
    RideThroughCore_eqFunction_98,
    RideThroughCore_eqFunction_99,
    RideThroughCore_eqFunction_100,
    RideThroughCore_eqFunction_111,
    RideThroughCore_eqFunction_113,
    RideThroughCore_eqFunction_114,
    RideThroughCore_eqFunction_115,
    RideThroughCore_eqFunction_116
  };
  
  if (data->simulationInfo->evalSelection) {
    for (int i = 0; i < data->simulationInfo->evalSelection->n; i++) {
      int id = data->simulationInfo->evalSelection->idx[i];
      eqFunctions[id](data, threadData);
    }
  } else {
    for (int id = 0; id < 30; id++) {
      eqFunctions[id](data, threadData);
    }
  }
}

int RideThroughCore_functionODE(DATA *data, threadData_t *threadData)
{
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_tick(SIM_TIMER_FUNCTION_ODE);
#endif

  
  data->simulationInfo->callStatistics.functionODE++;
  
  RideThroughCore_functionLocalKnownVars(data, threadData);
  functionODE_system0(data, threadData);

#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_accumulate(SIM_TIMER_FUNCTION_ODE);
#endif

  return 0;
}

void RideThroughCore_ODE_DAG(DATA* data, threadData_t* threadData)
{
  const size_t eqMap[] = {62, 63, 64, 69, 70, 71, 72, 73, 74, 79, 83, 86, 87, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 111, 113, 114, 115, 116};
  buildEvalDAG_ODE(data->modelData, sizeof(eqMap)/sizeof(size_t), eqMap);
}

/* forward the main in the simulation runtime */
extern int _main_SimulationRuntime(int argc, char **argv, DATA *data, threadData_t *threadData);
extern int _main_OptimizationRuntime(int argc, char **argv, DATA *data, threadData_t *threadData);

#include "RideThroughCore_12jac.h"
#include "RideThroughCore_13opt.h"

struct OpenModelicaGeneratedFunctionCallbacks RideThroughCore_callback = {
  (int (*)(DATA *, threadData_t *, void *)) RideThroughCore_performSimulation,    /* performSimulation */
  (int (*)(DATA *, threadData_t *, void *)) RideThroughCore_performQSSSimulation,    /* performQSSSimulation */
  RideThroughCore_updateContinuousSystem,    /* updateContinuousSystem */
  RideThroughCore_callExternalObjectDestructors,    /* callExternalObjectDestructors */
  RideThroughCore_initialNonLinearSystem,    /* initialNonLinearSystem */
  NULL,    /* initialLinearSystem */
  NULL,    /* initialMixedSystem */
  #if !defined(OMC_NO_STATESELECTION)
  RideThroughCore_initializeStateSets,
  #else
  NULL,
  #endif    /* initializeStateSets */
  RideThroughCore_initializeDAEmodeData,
  RideThroughCore_ODE_DAG,
  RideThroughCore_functionODE,
  RideThroughCore_functionAlgebraics,
  RideThroughCore_functionDAE,
  RideThroughCore_functionLocalKnownVars,
  RideThroughCore_input_function,
  RideThroughCore_input_function_init,
  RideThroughCore_input_function_updateStartValues,
  RideThroughCore_data_function,
  RideThroughCore_output_function,
  RideThroughCore_setc_function,
  RideThroughCore_setb_function,
  RideThroughCore_function_storeDelayed,
  RideThroughCore_function_storeSpatialDistribution,
  RideThroughCore_function_initSpatialDistribution,
  RideThroughCore_updateBoundVariableAttributes,
  RideThroughCore_functionInitialEquations,
  GLOBAL_EQUIDISTANT_HOMOTOPY,
  NULL,
  RideThroughCore_functionRemovedInitialEquations,
  RideThroughCore_updateBoundParameters,
  RideThroughCore_checkForAsserts,
  RideThroughCore_function_ZeroCrossingsEquations,
  RideThroughCore_function_ZeroCrossings,
  RideThroughCore_function_updateRelations,
  RideThroughCore_zeroCrossingDescription,
  RideThroughCore_relationDescription,
  RideThroughCore_function_initSample,
  RideThroughCore_INDEX_JAC_A,
  RideThroughCore_INDEX_JAC_ADJ,
  RideThroughCore_INDEX_JAC_B,
  RideThroughCore_INDEX_JAC_C,
  RideThroughCore_INDEX_JAC_D,
  RideThroughCore_INDEX_JAC_F,
  RideThroughCore_INDEX_JAC_H,
  RideThroughCore_initialAnalyticJacobianA,
  RideThroughCore_initialAnalyticJacobianADJ,
  RideThroughCore_initialAnalyticJacobianB,
  RideThroughCore_initialAnalyticJacobianC,
  RideThroughCore_initialAnalyticJacobianD,
  RideThroughCore_initialAnalyticJacobianF,
  RideThroughCore_initialAnalyticJacobianH,
  RideThroughCore_functionJacA_column,
  RideThroughCore_functionJacADJ_column,
  RideThroughCore_functionJacB_column,
  RideThroughCore_functionJacC_column,
  RideThroughCore_functionJacD_column,
  RideThroughCore_functionJacF_column,
  RideThroughCore_functionJacH_column,
  RideThroughCore_JacA_DAG,
  RideThroughCore_linear_model_frame,
  RideThroughCore_linear_model_datarecovery_frame,
  RideThroughCore_mayer,
  RideThroughCore_lagrange,
  RideThroughCore_getInputVarIndicesInOptimization,
  RideThroughCore_pickUpBoundsForInputsInOptimization,
  RideThroughCore_setInputData,
  RideThroughCore_getTimeGrid,
  RideThroughCore_symbolicInlineSystem,
  RideThroughCore_function_initSynchronous,
  RideThroughCore_function_updateSynchronous,
  RideThroughCore_function_equationsSynchronous,
  RideThroughCore_inputNames,
  RideThroughCore_dataReconciliationInputNames,
  RideThroughCore_dataReconciliationUnmeasuredVariables,
  NULL,
  NULL,
  NULL,
  NULL,
  -1,
  NULL,
  NULL,
  -1

};

#define _OMC_LIT_RESOURCE_0_name_data "RideThroughCore"
#define _OMC_LIT_RESOURCE_0_dir_data "/work/model"
static const MMC_DEFSTRINGLIT(_OMC_LIT_RESOURCE_0_name,15,_OMC_LIT_RESOURCE_0_name_data);
static const MMC_DEFSTRINGLIT(_OMC_LIT_RESOURCE_0_dir,11,_OMC_LIT_RESOURCE_0_dir_data);

static const MMC_DEFSTRUCTLIT(_OMC_LIT_RESOURCES,2,MMC_ARRAY_TAG) {MMC_REFSTRINGLIT(_OMC_LIT_RESOURCE_0_name), MMC_REFSTRINGLIT(_OMC_LIT_RESOURCE_0_dir)}};
void RideThroughCore_setupDataStruc(DATA *data, threadData_t *threadData)
{
  assertStreamPrint(threadData,0!=data, "Error while initialize Data");
  threadData->localRoots[LOCAL_ROOT_SIMULATION_DATA] = data;
  data->callback = &RideThroughCore_callback;
  OpenModelica_updateUriMapping(threadData, MMC_REFSTRUCTLIT(_OMC_LIT_RESOURCES));
  data->modelData->modelName = "RideThroughCore";
  data->modelData->modelFilePrefix = "RideThroughCore";
  data->modelData->modelFileName = "RideThroughCore.mo";
  data->modelData->resultFileName = NULL;
  data->modelData->modelDir = "/work/model";
  data->modelData->modelGUID = "{a09384a3-3039-449c-a09d-b60386d55ef2}";
  #if defined(OPENMODELICA_XML_FROM_FILE_AT_RUNTIME)
  data->modelData->initXMLData = NULL;
  data->modelData->modelDataXml.infoXMLData = NULL;
  #else
  #if defined(_MSC_VER) /* handle joke compilers */
  {
  /* for MSVC we encode a string like char x[] = {'a', 'b', 'c', '\0'} */
  /* because the string constant limit is 65535 bytes */
  static const char contents_init[] =
    #include "RideThroughCore_init.c"
    ;
  static const char contents_info[] =
    #include "RideThroughCore_info.c"
    ;
    data->modelData->initXMLData = contents_init;
    data->modelData->modelDataXml.infoXMLData = contents_info;
  }
  #else /* handle real compilers */
  data->modelData->initXMLData =
  #include "RideThroughCore_init.c"
    ;
  data->modelData->modelDataXml.infoXMLData =
  #include "RideThroughCore_info.c"
    ;
  #endif /* defined(_MSC_VER) */
  #endif /* defined(OPENMODELICA_XML_FROM_FILE_AT_RUNTIME) */
  data->modelData->modelDataXml.fileName = "RideThroughCore_info.json";
  data->modelData->resourcesDir = NULL;
  data->modelData->runTestsuite = 0;
  data->modelData->nStatesArray = 10;
  data->modelData->nDiscreteReal = 0;
  data->modelData->nVariablesRealArray = 38;
  data->modelData->nVariablesIntegerArray = 0;
  data->modelData->nVariablesBooleanArray = 18;
  data->modelData->nVariablesStringArray = 0;
  data->modelData->nParametersRealArray = 29;
  data->modelData->nParametersIntegerArray = 0;
  data->modelData->nParametersBooleanArray = 1;
  data->modelData->nParametersStringArray = 0;
  data->modelData->nParametersReal = 29;
  data->modelData->nParametersInteger = 0;
  data->modelData->nParametersBoolean = 1;
  data->modelData->nParametersString = 0;
  data->modelData->nAliasRealArray = 0;
  data->modelData->nAliasIntegerArray = 0;
  data->modelData->nAliasBooleanArray = 0;
  data->modelData->nAliasStringArray = 0;
  data->modelData->nInputVars = 0;
  data->modelData->nOutputVars = 0;
  data->modelData->nZeroCrossings = 27;
  data->modelData->nSamples = 0;
  data->modelData->nRelations = 27;
  data->modelData->nMathEvents = 0;
  data->modelData->nExtObjs = 0;
  data->modelData->modelDataXml.modelInfoXmlLength = 0;
  data->modelData->modelDataXml.nFunctions = 0;
  data->modelData->modelDataXml.nProfileBlocks = 0;
  data->modelData->modelDataXml.nEquations = 133;
  data->modelData->nMixedSystems = 0;
  data->modelData->nLinearSystems = 0;
  data->modelData->nNonLinearSystems = 2;
  data->modelData->nStateSets = 0;
  data->modelData->nJacobians = 9;
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
  
    RideThroughCore_setupDataStruc(&data, threadData);
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


