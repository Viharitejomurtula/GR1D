/* Initialization */
#include "facA_model.h"
#include "facA_11mix.h"
#include "facA_12jac.h"
#if defined(__cplusplus)
extern "C" {
#endif

void facA_functionInitialEquations_0(DATA *data, threadData_t *threadData);
extern void facA_eqFunction_100(DATA *data, threadData_t *threadData);


/*
equation index: 2
type: SIMPLE_ASSIGN
p_swing_target_w = 0.5 * swing_size_frac * p_it_rated_w * (if sin(6.283185307179586 * swing_freq_hz * time + swing_phase) >= 0.0 then 1.0 else -1.0)
*/
void facA_eqFunction_2(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,2};
  modelica_boolean tmp0;
  tmp0 = GreaterEq(sin(((6.283185307179586) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[24]] /* swing_freq_hz PARAM */))) * (data->localData[0]->timeValue) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[25]] /* swing_phase PARAM */)),0.0);
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[33]] /* p_swing_target_w variable */) = (0.5) * (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[26]] /* swing_size_frac PARAM */)) * (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */)) * ((tmp0?1.0:-1.0))));
  threadData->lastEquationSolved = 2;
}

/*
equation index: 3
type: SIMPLE_ASSIGN
v_sense_pu = $START.v_sense_pu
*/
void facA_eqFunction_3(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,3};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */) = ((modelica_real *)((data->modelData->realVarsData[9] /* v_sense_pu STATE(1) */).attribute .start.data))[0];
  threadData->lastEquationSolved = 3;
}
extern void facA_eqFunction_65(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_66(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_67(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_72(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_92(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_93(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_94(DATA *data, threadData_t *threadData);


/*
equation index: 11
type: SIMPLE_ASSIGN
p_swing_w = $START.p_swing_w
*/
void facA_eqFunction_11(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,11};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[1]] /* p_swing_w STATE(1) */) = ((modelica_real *)((data->modelData->realVarsData[1] /* p_swing_w STATE(1) */).attribute .start.data))[0];
  threadData->lastEquationSolved = 11;
}

/*
equation index: 12
type: SIMPLE_ASSIGN
$DER.p_swing_w = max((-1.9) * p_it_rated_w, min(1.9 * p_it_rated_w, 1000.0 * (p_swing_target_w - p_swing_w)))
*/
void facA_eqFunction_12(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,12};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[11]] /* der(p_swing_w) STATE_DER */) = fmax((-1.9) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */)),fmin((1.9) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[19]] /* p_it_rated_w PARAM */)),(1000.0) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[33]] /* p_swing_target_w variable */) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[1]] /* p_swing_w STATE(1) */))));
  threadData->lastEquationSolved = 12;
}

/*
equation index: 13
type: SIMPLE_ASSIGN
soc = battery_soc0
*/
void facA_eqFunction_13(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,13};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* soc STATE(1) */) = (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[3]] /* battery_soc0 PARAM */);
  threadData->lastEquationSolved = 13;
}

/*
equation index: 14
type: SIMPLE_ASSIGN
$PRE.psu_enabled = true
*/
void facA_eqFunction_14(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,14};
  (data->simulationInfo->booleanVarsPre[16] /* psu_enabled DISCRETE */) = 1 /* true */;
  threadData->lastEquationSolved = 14;
}

/*
equation index: 15
type: SIMPLE_ASSIGN
psu_enabled = $PRE.psu_enabled
*/
void facA_eqFunction_15(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,15};
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */) = (data->simulationInfo->booleanVarsPre[16] /* psu_enabled DISCRETE */);
  threadData->lastEquationSolved = 15;
}
extern void facA_eqFunction_89(DATA *data, threadData_t *threadData);


/*
equation index: 17
type: SIMPLE_ASSIGN
$PRE.bbu_active = false
*/
void facA_eqFunction_17(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,17};
  (data->simulationInfo->booleanVarsPre[13] /* bbu_active DISCRETE */) = 0 /* false */;
  threadData->lastEquationSolved = 17;
}

/*
equation index: 18
type: SIMPLE_ASSIGN
bbu_active = $PRE.bbu_active
*/
void facA_eqFunction_18(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,18};
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[13]] /* bbu_active DISCRETE */) = (data->simulationInfo->booleanVarsPre[13] /* bbu_active DISCRETE */);
  threadData->lastEquationSolved = 18;
}

/*
equation index: 19
type: SIMPLE_ASSIGN
$PRE.cool_s1_tripped = false
*/
void facA_eqFunction_19(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,19};
  (data->simulationInfo->booleanVarsPre[14] /* cool_s1_tripped DISCRETE */) = 0 /* false */;
  threadData->lastEquationSolved = 19;
}

/*
equation index: 20
type: SIMPLE_ASSIGN
cool_s1_tripped = $PRE.cool_s1_tripped
*/
void facA_eqFunction_20(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,20};
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[14]] /* cool_s1_tripped DISCRETE */) = (data->simulationInfo->booleanVarsPre[14] /* cool_s1_tripped DISCRETE */);
  threadData->lastEquationSolved = 20;
}

/*
equation index: 21
type: SIMPLE_ASSIGN
$PRE.cool_s2_tripped = false
*/
void facA_eqFunction_21(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,21};
  (data->simulationInfo->booleanVarsPre[15] /* cool_s2_tripped DISCRETE */) = 0 /* false */;
  threadData->lastEquationSolved = 21;
}

/*
equation index: 22
type: SIMPLE_ASSIGN
cool_s2_tripped = $PRE.cool_s2_tripped
*/
void facA_eqFunction_22(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,22};
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[15]] /* cool_s2_tripped DISCRETE */) = (data->simulationInfo->booleanVarsPre[15] /* cool_s2_tripped DISCRETE */);
  threadData->lastEquationSolved = 22;
}

/*
equation index: 23
type: SIMPLE_ASSIGN
$PRE.servers_lost_power = false
*/
void facA_eqFunction_23(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,23};
  (data->simulationInfo->booleanVarsPre[17] /* servers_lost_power DISCRETE */) = 0 /* false */;
  threadData->lastEquationSolved = 23;
}

/*
equation index: 24
type: SIMPLE_ASSIGN
servers_lost_power = $PRE.servers_lost_power
*/
void facA_eqFunction_24(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,24};
  (data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[17]] /* servers_lost_power DISCRETE */) = (data->simulationInfo->booleanVarsPre[17] /* servers_lost_power DISCRETE */);
  threadData->lastEquationSolved = 24;
}
extern void facA_eqFunction_95(DATA *data, threadData_t *threadData);


/*
equation index: 26
type: SIMPLE_ASSIGN
t_cool_ok = $START.t_cool_ok
*/
void facA_eqFunction_26(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,26};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* t_cool_ok STATE(1) */) = ((modelica_real *)((data->modelData->realVarsData[5] /* t_cool_ok STATE(1) */).attribute .start.data))[0];
  threadData->lastEquationSolved = 26;
}
extern void facA_eqFunction_90(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_91(DATA *data, threadData_t *threadData);


void facA_eqFunction_29(DATA*, threadData_t*);
void facA_eqFunction_30(DATA*, threadData_t*);
void facA_eqFunction_31(DATA*, threadData_t*);
void facA_eqFunction_32(DATA*, threadData_t*);
/*
equation index: 37
indexNonlinear: 0
type: NONLINEAR

vars: {v_sdp_pu}
eqns: {29, 30, 31, 32}
*/
void facA_eqFunction_37(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,37};
  int retValue;
  infoStreamPrint(OMC_LOG_DT, 0, "Solving nonlinear system 37 (STRICT TEARING SET if tearing enabled) at time = %18.10e", data->localData[0]->timeValue);
  /* get old value */
  data->simulationInfo->nonlinearSystemData[0].nlsxOld[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */);
  retValue = solve_nonlinear_system(data, threadData, 0);
  /* check if solution process was successful */
  if (retValue > 0){
    const int indexes[2] = {1,37};
    throwStreamPrintWithEquationIndexes(threadData, omc_dummyFileInfo, indexes, "Solving non-linear system 37 failed at time=%.15g.\nFor more information please use -lv LOG_NLS.", data->localData[0]->timeValue);
  }
  /* write solution */
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */) = data->simulationInfo->nonlinearSystemData[0].nlsx[0];
  threadData->lastEquationSolved = 37;
}
extern void facA_eqFunction_114(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_116(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_113(DATA *data, threadData_t *threadData);


/*
equation index: 41
type: SIMPLE_ASSIGN
v_psu_in_v = supply_voltage_v * max(v_sdp_pu, 0.0)
*/
void facA_eqFunction_41(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,41};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[35]] /* v_psu_in_v variable */) = ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */)) * (fmax((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */),0.0));
  threadData->lastEquationSolved = 41;
}

/*
equation index: 42
type: SIMPLE_ASSIGN
t_psu_down = $START.t_psu_down
*/
void facA_eqFunction_42(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,42};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[8]] /* t_psu_down STATE(1) */) = ((modelica_real *)((data->modelData->realVarsData[8] /* t_psu_down STATE(1) */).attribute .start.data))[0];
  threadData->lastEquationSolved = 42;
}
extern void facA_eqFunction_71(DATA *data, threadData_t *threadData);


/*
equation index: 44
type: SIMPLE_ASSIGN
e_holdup_j = e_holdup_max_j
*/
void facA_eqFunction_44(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,44};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* e_holdup_j STATE(1) */) = (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[14]] /* e_holdup_max_j PARAM */);
  threadData->lastEquationSolved = 44;
}
extern void facA_eqFunction_115(DATA *data, threadData_t *threadData);


/*
equation index: 46
type: SIMPLE_ASSIGN
e_frac = max(0.0, min(1.0, e_holdup_j / e_holdup_max_j))
*/
void facA_eqFunction_46(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,46};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */) = fmax(0.0,fmin(1.0,DIVISION_SIM((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* e_holdup_j STATE(1) */),(data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[14]] /* e_holdup_max_j PARAM */),"e_holdup_max_j",equationIndexes)));
  threadData->lastEquationSolved = 46;
}
extern void facA_eqFunction_68(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_80(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_79(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_83(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_86(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_87(DATA *data, threadData_t *threadData);

extern void facA_eqFunction_88(DATA *data, threadData_t *threadData);


/*
equation index: 54
type: SIMPLE_ASSIGN
t_bus_low = $START.t_bus_low
*/
void facA_eqFunction_54(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,54};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* t_bus_low STATE(1) */) = ((modelica_real *)((data->modelData->realVarsData[3] /* t_bus_low STATE(1) */).attribute .start.data))[0];
  threadData->lastEquationSolved = 54;
}
extern void facA_eqFunction_74(DATA *data, threadData_t *threadData);


/*
equation index: 56
type: SIMPLE_ASSIGN
t_bus_ok = $START.t_bus_ok
*/
void facA_eqFunction_56(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,56};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* t_bus_ok STATE(1) */) = ((modelica_real *)((data->modelData->realVarsData[4] /* t_bus_ok STATE(1) */).attribute .start.data))[0];
  threadData->lastEquationSolved = 56;
}
extern void facA_eqFunction_73(DATA *data, threadData_t *threadData);


/*
equation index: 58
type: SIMPLE_ASSIGN
t_cool_s2 = $START.t_cool_s2
*/
void facA_eqFunction_58(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,58};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[7]] /* t_cool_s2 STATE(1) */) = ((modelica_real *)((data->modelData->realVarsData[7] /* t_cool_s2 STATE(1) */).attribute .start.data))[0];
  threadData->lastEquationSolved = 58;
}
extern void facA_eqFunction_70(DATA *data, threadData_t *threadData);


/*
equation index: 60
type: SIMPLE_ASSIGN
t_cool_s1 = $START.t_cool_s1
*/
void facA_eqFunction_60(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,60};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[6]] /* t_cool_s1 STATE(1) */) = ((modelica_real *)((data->modelData->realVarsData[6] /* t_cool_s1 STATE(1) */).attribute .start.data))[0];
  threadData->lastEquationSolved = 60;
}
extern void facA_eqFunction_69(DATA *data, threadData_t *threadData);

OMC_DISABLE_OPT
void facA_functionInitialEquations_0(DATA *data, threadData_t *threadData)
{
  static void (*const eqFunctions[53])(DATA*, threadData_t*) = {
    facA_eqFunction_100,
    facA_eqFunction_2,
    facA_eqFunction_3,
    facA_eqFunction_65,
    facA_eqFunction_66,
    facA_eqFunction_67,
    facA_eqFunction_72,
    facA_eqFunction_92,
    facA_eqFunction_93,
    facA_eqFunction_94,
    facA_eqFunction_11,
    facA_eqFunction_12,
    facA_eqFunction_13,
    facA_eqFunction_14,
    facA_eqFunction_15,
    facA_eqFunction_89,
    facA_eqFunction_17,
    facA_eqFunction_18,
    facA_eqFunction_19,
    facA_eqFunction_20,
    facA_eqFunction_21,
    facA_eqFunction_22,
    facA_eqFunction_23,
    facA_eqFunction_24,
    facA_eqFunction_95,
    facA_eqFunction_26,
    facA_eqFunction_90,
    facA_eqFunction_91,
    facA_eqFunction_37,
    facA_eqFunction_114,
    facA_eqFunction_116,
    facA_eqFunction_113,
    facA_eqFunction_41,
    facA_eqFunction_42,
    facA_eqFunction_71,
    facA_eqFunction_44,
    facA_eqFunction_115,
    facA_eqFunction_46,
    facA_eqFunction_68,
    facA_eqFunction_80,
    facA_eqFunction_79,
    facA_eqFunction_83,
    facA_eqFunction_86,
    facA_eqFunction_87,
    facA_eqFunction_88,
    facA_eqFunction_54,
    facA_eqFunction_74,
    facA_eqFunction_56,
    facA_eqFunction_73,
    facA_eqFunction_58,
    facA_eqFunction_70,
    facA_eqFunction_60,
    facA_eqFunction_69
  };
  
  for (int id = 0; id < 53; id++) {
    eqFunctions[id](data, threadData);
  }
}

int facA_functionInitialEquations(DATA *data, threadData_t *threadData)
{
  data->simulationInfo->discreteCall = 1;
  facA_functionInitialEquations_0(data, threadData);
  data->simulationInfo->discreteCall = 0;
  
  return 0;
}

/* No facA_functionInitialEquations_lambda0 function */

int facA_functionRemovedInitialEquations(DATA *data, threadData_t *threadData)
{
  const int *equationIndexes = NULL;
  double res = 0.0;

  
  return 0;
}


#if defined(__cplusplus)
}
#endif
