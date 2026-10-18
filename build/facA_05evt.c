/* Events: Sample, Zero Crossings, Relations, Discrete Changes */
#include "facA_model.h"
#if defined(__cplusplus)
extern "C" {
#endif

/* Initializes the raw time events of the simulation using the now
   calcualted parameters. */
void facA_function_initSample(DATA *data, threadData_t *threadData)
{
  long i=0;
}

const char *facA_zeroCrossingDescription(int i, int **out_EquationIndexes)
{
  static const char *res[] = {"time >= dip_start_s and time < dip_start_s + dip_duration_s",
  "second_dip and time >= dip_start_s + dip_duration_s + reclose_gap_s and time < dip_start_s + 2.0 * dip_duration_s + reclose_gap_s",
  "$cse3 >= 0.0",
  "v_sense_pu < 0.7",
  "v_sense_pu < 0.6",
  "v_sense_pu > 0.5",
  "cool_s2_tripped and t_cool_ok < 0.25",
  "t_cool_ok < 0.25",
  "psu_enabled and p_psu_w >= p_server_w",
  "bbu_active and soc > 0.0",
  "e_frac < 0.625",
  "psu_enabled and e_frac > 0.625",
  "soc > 0.0",
  "v_sdp_pu > 0.01",
  "e_frac < 0.20833333333333337 and not bbu_active",
  "e_frac > 0.625",
  "t_bus_low > 0.002",
  "t_bus_ok > handback_delay_s",
  "supply_voltage_v * v_sense_pu < 172.0",
  "supply_voltage_v * v_sense_pu > 178.0 and t_psu_down > 1.0 + psu_restart_delay_s",
  "t_cool_s2 > 0.02",
  "t_cool_s1 > 0.05",
  "e_frac <= 0.625 or not psu_enabled",
  "e_frac >= 0.625",
  "v_sense_pu <= 0.5",
  "v_sense_pu >= 0.6",
  "v_sense_pu >= 0.7"};
  static const int occurEqs0[] = {1,100};
  static const int occurEqs1[] = {1,100};
  static const int occurEqs2[] = {1,96};
  static const int occurEqs3[] = {1,94};
  static const int occurEqs4[] = {1,93};
  static const int occurEqs5[] = {1,92};
  static const int occurEqs6[] = {1,90};
  static const int occurEqs7[] = {1,90};
  static const int occurEqs8[] = {1,115};
  static const int occurEqs9[] = {1,88};
  static const int occurEqs10[] = {1,87};
  static const int occurEqs11[] = {1,86};
  static const int occurEqs12[] = {1,114};
  static const int occurEqs13[] = {1,-1};
  static const int occurEqs14[] = {1,83};
  static const int occurEqs15[] = {1,79};
  static const int occurEqs16[] = {1,74};
  static const int occurEqs17[] = {1,73};
  static const int occurEqs18[] = {1,72};
  static const int occurEqs19[] = {1,71};
  static const int occurEqs20[] = {1,70};
  static const int occurEqs21[] = {1,69};
  static const int occurEqs22[] = {1,80};
  static const int occurEqs23[] = {1,68};
  static const int occurEqs24[] = {1,67};
  static const int occurEqs25[] = {1,66};
  static const int occurEqs26[] = {1,65};
  static const int *occurEqs[] = {occurEqs0,occurEqs1,occurEqs2,occurEqs3,occurEqs4,occurEqs5,occurEqs6,occurEqs7,occurEqs8,occurEqs9,occurEqs10,occurEqs11,occurEqs12,occurEqs13,occurEqs14,occurEqs15,occurEqs16,occurEqs17,occurEqs18,occurEqs19,occurEqs20,occurEqs21,occurEqs22,occurEqs23,occurEqs24,occurEqs25,occurEqs26};
  *out_EquationIndexes = (int*) occurEqs[i];
  return res[i];
}

/* forwarded equations */
extern void facA_eqFunction_62(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_63(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_64(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_69(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_70(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_71(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_72(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_73(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_74(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_79(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_83(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_86(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_87(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_89(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_90(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_91(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_92(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_93(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_94(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_95(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_96(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_97(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_98(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_99(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_100(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_111(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_113(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_114(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_115(DATA* data, threadData_t *threadData);
extern void facA_eqFunction_116(DATA* data, threadData_t *threadData);

int facA_function_ZeroCrossingsEquations(DATA *data, threadData_t *threadData)
{
  data->simulationInfo->callStatistics.functionZeroCrossingsEquations++;

  static void (*const eqFunctions[30])(DATA*, threadData_t*) = {
    facA_eqFunction_62,
    facA_eqFunction_63,
    facA_eqFunction_64,
    facA_eqFunction_69,
    facA_eqFunction_70,
    facA_eqFunction_71,
    facA_eqFunction_72,
    facA_eqFunction_73,
    facA_eqFunction_74,
    facA_eqFunction_79,
    facA_eqFunction_83,
    facA_eqFunction_86,
    facA_eqFunction_87,
    facA_eqFunction_89,
    facA_eqFunction_90,
    facA_eqFunction_91,
    facA_eqFunction_92,
    facA_eqFunction_93,
    facA_eqFunction_94,
    facA_eqFunction_95,
    facA_eqFunction_96,
    facA_eqFunction_97,
    facA_eqFunction_98,
    facA_eqFunction_99,
    facA_eqFunction_100,
    facA_eqFunction_111,
    facA_eqFunction_113,
    facA_eqFunction_114,
    facA_eqFunction_115,
    facA_eqFunction_116
  };
  
  for (int id = 0; id < 30; id++) {
    eqFunctions[id](data, threadData);
  }
  
  return 0;
}

int facA_function_ZeroCrossings(DATA *data, threadData_t *threadData, double *gout)
{
  const int *equationIndexes = NULL;

  modelica_boolean tmp0;
  modelica_real tmp1;
  modelica_real tmp2;
  modelica_boolean tmp3;
  modelica_real tmp4;
  modelica_real tmp5;
  modelica_boolean tmp6;
  modelica_real tmp7;
  modelica_real tmp8;
  modelica_boolean tmp9;
  modelica_real tmp10;
  modelica_real tmp11;
  modelica_boolean tmp12;
  modelica_real tmp13;
  modelica_real tmp14;
  modelica_boolean tmp15;
  modelica_real tmp16;
  modelica_real tmp17;
  modelica_boolean tmp18;
  modelica_real tmp19;
  modelica_real tmp20;
  modelica_boolean tmp21;
  modelica_real tmp22;
  modelica_real tmp23;
  modelica_boolean tmp24;
  modelica_real tmp25;
  modelica_real tmp26;
  modelica_boolean tmp27;
  modelica_real tmp28;
  modelica_real tmp29;
  modelica_boolean tmp30;
  modelica_real tmp31;
  modelica_real tmp32;
  modelica_boolean tmp33;
  modelica_real tmp34;
  modelica_real tmp35;
  modelica_boolean tmp36;
  modelica_real tmp37;
  modelica_real tmp38;
  modelica_boolean tmp39;
  modelica_real tmp40;
  modelica_real tmp41;
  modelica_boolean tmp42;
  modelica_real tmp43;
  modelica_real tmp44;
  modelica_boolean tmp45;
  modelica_real tmp46;
  modelica_real tmp47;
  modelica_boolean tmp48;
  modelica_real tmp49;
  modelica_real tmp50;
  modelica_boolean tmp51;
  modelica_real tmp52;
  modelica_real tmp53;
  modelica_boolean tmp54;
  modelica_real tmp55;
  modelica_real tmp56;
  modelica_boolean tmp57;
  modelica_real tmp58;
  modelica_real tmp59;
  modelica_boolean tmp60;
  modelica_real tmp61;
  modelica_real tmp62;
  modelica_boolean tmp63;
  modelica_real tmp64;
  modelica_real tmp65;
  modelica_boolean tmp66;
  modelica_real tmp67;
  modelica_real tmp68;
  modelica_boolean tmp69;
  modelica_real tmp70;
  modelica_real tmp71;
  modelica_boolean tmp72;
  modelica_real tmp73;
  modelica_real tmp74;
  modelica_boolean tmp75;
  modelica_real tmp76;
  modelica_real tmp77;
  modelica_boolean tmp78;
  modelica_real tmp79;
  modelica_real tmp80;
  modelica_boolean tmp81;
  modelica_real tmp82;
  modelica_real tmp83;
  modelica_boolean tmp84;
  modelica_real tmp85;
  modelica_real tmp86;
  modelica_boolean tmp87;
  modelica_real tmp88;
  modelica_real tmp89;
  modelica_integer current_index = 0;
  modelica_integer start_index;
  
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_tick(SIM_TIMER_ZC);
#endif
  data->simulationInfo->callStatistics.functionZeroCrossings++;

  start_index = current_index;
  tmp1 = 1.0;
  tmp2 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */));
  tmp0 = GreaterEqZC(data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */), tmp1, tmp2, data->simulationInfo->storedRelations[0]);
  tmp4 = 1.0;
  tmp5 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */)) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */));
  tmp3 = LessZC(data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */), tmp4, tmp5, data->simulationInfo->storedRelations[1]);
  gout[start_index] = ((tmp0 && tmp3)) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp7 = 1.0;
  tmp8 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */)) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */)) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */));
  tmp6 = GreaterEqZC(data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */), tmp7, tmp8, data->simulationInfo->storedRelations[2]);
  tmp10 = 1.0;
  tmp11 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */)) + (2.0) * (fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */))) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */));
  tmp9 = LessZC(data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (2.0) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */)) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */), tmp10, tmp11, data->simulationInfo->storedRelations[3]);
  gout[start_index] = ((((data->simulationInfo->booleanParameter[data->simulationInfo->booleanParamsIndex[0]] /* second_dip PARAM */) && tmp6) && tmp9)) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp13 = 1.0;
  tmp14 = 0.0;
  tmp12 = GreaterEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[22]] /* $cse3 variable */), 0.0, tmp13, tmp14, data->simulationInfo->storedRelations[4]);
  gout[start_index] = (tmp12) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp16 = 1.0;
  tmp17 = 0.7;
  tmp15 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.7, tmp16, tmp17, data->simulationInfo->storedRelations[5]);
  gout[start_index] = (tmp15) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp19 = 1.0;
  tmp20 = 0.6;
  tmp18 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.6, tmp19, tmp20, data->simulationInfo->storedRelations[6]);
  gout[start_index] = (tmp18) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp22 = 1.0;
  tmp23 = 0.5;
  tmp21 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.5, tmp22, tmp23, data->simulationInfo->storedRelations[7]);
  gout[start_index] = (tmp21) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp25 = 1.0;
  tmp26 = 0.25;
  tmp24 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* t_cool_ok STATE(1) */), 0.25, tmp25, tmp26, data->simulationInfo->storedRelations[8]);
  gout[start_index] = (((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[15]] /* cool_s2_tripped DISCRETE */) && tmp24)) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp28 = 1.0;
  tmp29 = 0.25;
  tmp27 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* t_cool_ok STATE(1) */), 0.25, tmp28, tmp29, data->simulationInfo->storedRelations[8]);
  gout[start_index] = (tmp27) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp31 = 1.0;
  tmp32 = 1.0;
  tmp30 = GreaterEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[31]] /* p_psu_w variable */), (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */), tmp31, tmp32, data->simulationInfo->storedRelations[9]);
  gout[start_index] = (((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */) && tmp30)) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp34 = 1.0;
  tmp35 = 0.0;
  tmp33 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* soc STATE(1) */), 0.0, tmp34, tmp35, data->simulationInfo->storedRelations[10]);
  gout[start_index] = (((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[13]] /* bbu_active DISCRETE */) && tmp33)) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp37 = 1.0;
  tmp38 = 0.625;
  tmp36 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp37, tmp38, data->simulationInfo->storedRelations[11]);
  gout[start_index] = (tmp36) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp40 = 1.0;
  tmp41 = 0.625;
  tmp39 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp40, tmp41, data->simulationInfo->storedRelations[12]);
  gout[start_index] = (((data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */) && tmp39)) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp43 = 1.0;
  tmp44 = 0.0;
  tmp42 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* soc STATE(1) */), 0.0, tmp43, tmp44, data->simulationInfo->storedRelations[10]);
  gout[start_index] = (tmp42) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp46 = 1.0;
  tmp47 = 0.01;
  tmp45 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */), 0.01, tmp46, tmp47, data->simulationInfo->storedRelations[13]);
  gout[start_index] = (tmp45) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp49 = 1.0;
  tmp50 = 0.20833333333333337;
  tmp48 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.20833333333333337, tmp49, tmp50, data->simulationInfo->storedRelations[14]);
  gout[start_index] = ((tmp48 && (!(data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[13]] /* bbu_active DISCRETE */)))) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp52 = 1.0;
  tmp53 = 0.625;
  tmp51 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp52, tmp53, data->simulationInfo->storedRelations[12]);
  gout[start_index] = (tmp51) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp55 = 1.0;
  tmp56 = 0.002;
  tmp54 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* t_bus_low STATE(1) */), 0.002, tmp55, tmp56, data->simulationInfo->storedRelations[15]);
  gout[start_index] = (tmp54) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp58 = 1.0;
  tmp59 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[15]] /* handback_delay_s PARAM */));
  tmp57 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* t_bus_ok STATE(1) */), (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[15]] /* handback_delay_s PARAM */), tmp58, tmp59, data->simulationInfo->storedRelations[16]);
  gout[start_index] = (tmp57) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp61 = (fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */))) * (1.0);
  tmp62 = 172.0;
  tmp60 = LessZC(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */)), 172.0, tmp61, tmp62, data->simulationInfo->storedRelations[17]);
  gout[start_index] = (tmp60) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp64 = (fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */))) * (1.0);
  tmp65 = 178.0;
  tmp63 = GreaterZC(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */)), 178.0, tmp64, tmp65, data->simulationInfo->storedRelations[18]);
  tmp67 = 1.0;
  tmp68 = 1.0 + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[21]] /* psu_restart_delay_s PARAM */));
  tmp66 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[8]] /* t_psu_down STATE(1) */), 1.0 + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[21]] /* psu_restart_delay_s PARAM */), tmp67, tmp68, data->simulationInfo->storedRelations[19]);
  gout[start_index] = ((tmp63 && tmp66)) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp70 = 1.0;
  tmp71 = 0.02;
  tmp69 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[7]] /* t_cool_s2 STATE(1) */), 0.02, tmp70, tmp71, data->simulationInfo->storedRelations[20]);
  gout[start_index] = (tmp69) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp73 = 1.0;
  tmp74 = 0.05;
  tmp72 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[6]] /* t_cool_s1 STATE(1) */), 0.05, tmp73, tmp74, data->simulationInfo->storedRelations[21]);
  gout[start_index] = (tmp72) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp76 = 1.0;
  tmp77 = 0.625;
  tmp75 = LessEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp76, tmp77, data->simulationInfo->storedRelations[22]);
  gout[start_index] = ((tmp75 || (!(data->localData[0]->booleanVars[data->simulationInfo->booleanVarsIndex[16]] /* psu_enabled DISCRETE */)))) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp79 = 1.0;
  tmp80 = 0.625;
  tmp78 = GreaterEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp79, tmp80, data->simulationInfo->storedRelations[23]);
  gout[start_index] = (tmp78) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp82 = 1.0;
  tmp83 = 0.5;
  tmp81 = LessEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.5, tmp82, tmp83, data->simulationInfo->storedRelations[24]);
  gout[start_index] = (tmp81) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp85 = 1.0;
  tmp86 = 0.6;
  tmp84 = GreaterEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.6, tmp85, tmp86, data->simulationInfo->storedRelations[25]);
  gout[start_index] = (tmp84) ? 1 : -1;
  current_index++;

  start_index = current_index;
  tmp88 = 1.0;
  tmp89 = 0.7;
  tmp87 = GreaterEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.7, tmp88, tmp89, data->simulationInfo->storedRelations[26]);
  gout[start_index] = (tmp87) ? 1 : -1;
  current_index++;

#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_accumulate(SIM_TIMER_ZC);
#endif

  return 0;
}

const char *facA_relationDescription(int i)
{
  const char *res[] = {"time >= dip_start_s",
  "time < dip_start_s + dip_duration_s",
  "time >= dip_start_s + dip_duration_s + reclose_gap_s",
  "time < dip_start_s + 2.0 * dip_duration_s + reclose_gap_s",
  "$cse3 >= 0.0",
  "v_sense_pu < 0.7",
  "v_sense_pu < 0.6",
  "v_sense_pu > 0.5",
  "t_cool_ok < 0.25",
  "p_psu_w >= p_server_w",
  "soc > 0.0",
  "e_frac < 0.625",
  "e_frac > 0.625",
  "v_sdp_pu > 0.01",
  "e_frac < 0.20833333333333337",
  "t_bus_low > 0.002",
  "t_bus_ok > handback_delay_s",
  "supply_voltage_v * v_sense_pu < 172.0",
  "supply_voltage_v * v_sense_pu > 178.0",
  "t_psu_down > 1.0 + psu_restart_delay_s",
  "t_cool_s2 > 0.02",
  "t_cool_s1 > 0.05",
  "e_frac <= 0.625",
  "e_frac >= 0.625",
  "v_sense_pu <= 0.5",
  "v_sense_pu >= 0.6",
  "v_sense_pu >= 0.7"};
  return res[i];
}

int facA_function_updateRelations(DATA *data, threadData_t *threadData, int evalforZeroCross)
{
  const int *equationIndexes = NULL;

  modelica_boolean tmp90;
  modelica_real tmp91;
  modelica_real tmp92;
  modelica_boolean tmp93;
  modelica_real tmp94;
  modelica_real tmp95;
  modelica_boolean tmp96;
  modelica_real tmp97;
  modelica_real tmp98;
  modelica_boolean tmp99;
  modelica_real tmp100;
  modelica_real tmp101;
  modelica_boolean tmp102;
  modelica_real tmp103;
  modelica_real tmp104;
  modelica_boolean tmp105;
  modelica_real tmp106;
  modelica_real tmp107;
  modelica_boolean tmp108;
  modelica_real tmp109;
  modelica_real tmp110;
  modelica_boolean tmp111;
  modelica_real tmp112;
  modelica_real tmp113;
  modelica_boolean tmp114;
  modelica_real tmp115;
  modelica_real tmp116;
  modelica_boolean tmp117;
  modelica_real tmp118;
  modelica_real tmp119;
  modelica_boolean tmp120;
  modelica_real tmp121;
  modelica_real tmp122;
  modelica_boolean tmp123;
  modelica_real tmp124;
  modelica_real tmp125;
  modelica_boolean tmp126;
  modelica_real tmp127;
  modelica_real tmp128;
  modelica_boolean tmp129;
  modelica_real tmp130;
  modelica_real tmp131;
  modelica_boolean tmp132;
  modelica_real tmp133;
  modelica_real tmp134;
  modelica_boolean tmp135;
  modelica_real tmp136;
  modelica_real tmp137;
  modelica_boolean tmp138;
  modelica_real tmp139;
  modelica_real tmp140;
  modelica_boolean tmp141;
  modelica_real tmp142;
  modelica_real tmp143;
  modelica_boolean tmp144;
  modelica_real tmp145;
  modelica_real tmp146;
  modelica_boolean tmp147;
  modelica_real tmp148;
  modelica_real tmp149;
  modelica_boolean tmp150;
  modelica_real tmp151;
  modelica_real tmp152;
  modelica_boolean tmp153;
  modelica_real tmp154;
  modelica_real tmp155;
  modelica_boolean tmp156;
  modelica_real tmp157;
  modelica_real tmp158;
  modelica_boolean tmp159;
  modelica_real tmp160;
  modelica_real tmp161;
  modelica_boolean tmp162;
  modelica_real tmp163;
  modelica_real tmp164;
  modelica_boolean tmp165;
  modelica_real tmp166;
  modelica_real tmp167;
  modelica_boolean tmp168;
  modelica_real tmp169;
  modelica_real tmp170;
  modelica_integer current_index = 0;
  modelica_integer start_index;
  
  if(evalforZeroCross) {
    start_index = current_index;
    tmp91 = 1.0;
    tmp92 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */));
    tmp90 = GreaterEqZC(data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */), tmp91, tmp92, data->simulationInfo->storedRelations[0]);
    data->simulationInfo->relations[start_index] = tmp90;
    current_index++;

    start_index = current_index;
    tmp94 = 1.0;
    tmp95 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */)) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */));
    tmp93 = LessZC(data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */), tmp94, tmp95, data->simulationInfo->storedRelations[1]);
    data->simulationInfo->relations[start_index] = tmp93;
    current_index++;

    start_index = current_index;
    tmp97 = 1.0;
    tmp98 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */)) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */)) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */));
    tmp96 = GreaterEqZC(data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */), tmp97, tmp98, data->simulationInfo->storedRelations[2]);
    data->simulationInfo->relations[start_index] = tmp96;
    current_index++;

    start_index = current_index;
    tmp100 = 1.0;
    tmp101 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */)) + (2.0) * (fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */))) + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */));
    tmp99 = LessZC(data->localData[0]->timeValue, (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (2.0) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */)) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */), tmp100, tmp101, data->simulationInfo->storedRelations[3]);
    data->simulationInfo->relations[start_index] = tmp99;
    current_index++;

    start_index = current_index;
    tmp103 = 1.0;
    tmp104 = 0.0;
    tmp102 = GreaterEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[22]] /* $cse3 variable */), 0.0, tmp103, tmp104, data->simulationInfo->storedRelations[4]);
    data->simulationInfo->relations[start_index] = tmp102;
    current_index++;

    start_index = current_index;
    tmp106 = 1.0;
    tmp107 = 0.7;
    tmp105 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.7, tmp106, tmp107, data->simulationInfo->storedRelations[5]);
    data->simulationInfo->relations[start_index] = tmp105;
    current_index++;

    start_index = current_index;
    tmp109 = 1.0;
    tmp110 = 0.6;
    tmp108 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.6, tmp109, tmp110, data->simulationInfo->storedRelations[6]);
    data->simulationInfo->relations[start_index] = tmp108;
    current_index++;

    start_index = current_index;
    tmp112 = 1.0;
    tmp113 = 0.5;
    tmp111 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.5, tmp112, tmp113, data->simulationInfo->storedRelations[7]);
    data->simulationInfo->relations[start_index] = tmp111;
    current_index++;

    start_index = current_index;
    tmp115 = 1.0;
    tmp116 = 0.25;
    tmp114 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* t_cool_ok STATE(1) */), 0.25, tmp115, tmp116, data->simulationInfo->storedRelations[8]);
    data->simulationInfo->relations[start_index] = tmp114;
    current_index++;

    start_index = current_index;
    tmp118 = 1.0;
    tmp119 = 1.0;
    tmp117 = GreaterEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[31]] /* p_psu_w variable */), (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */), tmp118, tmp119, data->simulationInfo->storedRelations[9]);
    data->simulationInfo->relations[start_index] = tmp117;
    current_index++;

    start_index = current_index;
    tmp121 = 1.0;
    tmp122 = 0.0;
    tmp120 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* soc STATE(1) */), 0.0, tmp121, tmp122, data->simulationInfo->storedRelations[10]);
    data->simulationInfo->relations[start_index] = tmp120;
    current_index++;

    start_index = current_index;
    tmp124 = 1.0;
    tmp125 = 0.625;
    tmp123 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp124, tmp125, data->simulationInfo->storedRelations[11]);
    data->simulationInfo->relations[start_index] = tmp123;
    current_index++;

    start_index = current_index;
    tmp127 = 1.0;
    tmp128 = 0.625;
    tmp126 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp127, tmp128, data->simulationInfo->storedRelations[12]);
    data->simulationInfo->relations[start_index] = tmp126;
    current_index++;

    start_index = current_index;
    tmp130 = 1.0;
    tmp131 = 0.01;
    tmp129 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */), 0.01, tmp130, tmp131, data->simulationInfo->storedRelations[13]);
    data->simulationInfo->relations[start_index] = tmp129;
    current_index++;

    start_index = current_index;
    tmp133 = 1.0;
    tmp134 = 0.20833333333333337;
    tmp132 = LessZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.20833333333333337, tmp133, tmp134, data->simulationInfo->storedRelations[14]);
    data->simulationInfo->relations[start_index] = tmp132;
    current_index++;

    start_index = current_index;
    tmp136 = 1.0;
    tmp137 = 0.002;
    tmp135 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* t_bus_low STATE(1) */), 0.002, tmp136, tmp137, data->simulationInfo->storedRelations[15]);
    data->simulationInfo->relations[start_index] = tmp135;
    current_index++;

    start_index = current_index;
    tmp139 = 1.0;
    tmp140 = fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[15]] /* handback_delay_s PARAM */));
    tmp138 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* t_bus_ok STATE(1) */), (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[15]] /* handback_delay_s PARAM */), tmp139, tmp140, data->simulationInfo->storedRelations[16]);
    data->simulationInfo->relations[start_index] = tmp138;
    current_index++;

    start_index = current_index;
    tmp142 = (fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */))) * (1.0);
    tmp143 = 172.0;
    tmp141 = LessZC(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */)), 172.0, tmp142, tmp143, data->simulationInfo->storedRelations[17]);
    data->simulationInfo->relations[start_index] = tmp141;
    current_index++;

    start_index = current_index;
    tmp145 = (fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */))) * (1.0);
    tmp146 = 178.0;
    tmp144 = GreaterZC(((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */)), 178.0, tmp145, tmp146, data->simulationInfo->storedRelations[18]);
    data->simulationInfo->relations[start_index] = tmp144;
    current_index++;

    start_index = current_index;
    tmp148 = 1.0;
    tmp149 = 1.0 + fabs((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[21]] /* psu_restart_delay_s PARAM */));
    tmp147 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[8]] /* t_psu_down STATE(1) */), 1.0 + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[21]] /* psu_restart_delay_s PARAM */), tmp148, tmp149, data->simulationInfo->storedRelations[19]);
    data->simulationInfo->relations[start_index] = tmp147;
    current_index++;

    start_index = current_index;
    tmp151 = 1.0;
    tmp152 = 0.02;
    tmp150 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[7]] /* t_cool_s2 STATE(1) */), 0.02, tmp151, tmp152, data->simulationInfo->storedRelations[20]);
    data->simulationInfo->relations[start_index] = tmp150;
    current_index++;

    start_index = current_index;
    tmp154 = 1.0;
    tmp155 = 0.05;
    tmp153 = GreaterZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[6]] /* t_cool_s1 STATE(1) */), 0.05, tmp154, tmp155, data->simulationInfo->storedRelations[21]);
    data->simulationInfo->relations[start_index] = tmp153;
    current_index++;

    start_index = current_index;
    tmp157 = 1.0;
    tmp158 = 0.625;
    tmp156 = LessEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp157, tmp158, data->simulationInfo->storedRelations[22]);
    data->simulationInfo->relations[start_index] = tmp156;
    current_index++;

    start_index = current_index;
    tmp160 = 1.0;
    tmp161 = 0.625;
    tmp159 = GreaterEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */), 0.625, tmp160, tmp161, data->simulationInfo->storedRelations[23]);
    data->simulationInfo->relations[start_index] = tmp159;
    current_index++;

    start_index = current_index;
    tmp163 = 1.0;
    tmp164 = 0.5;
    tmp162 = LessEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.5, tmp163, tmp164, data->simulationInfo->storedRelations[24]);
    data->simulationInfo->relations[start_index] = tmp162;
    current_index++;

    start_index = current_index;
    tmp166 = 1.0;
    tmp167 = 0.6;
    tmp165 = GreaterEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.6, tmp166, tmp167, data->simulationInfo->storedRelations[25]);
    data->simulationInfo->relations[start_index] = tmp165;
    current_index++;

    start_index = current_index;
    tmp169 = 1.0;
    tmp170 = 0.7;
    tmp168 = GreaterEqZC((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */), 0.7, tmp169, tmp170, data->simulationInfo->storedRelations[26]);
    data->simulationInfo->relations[start_index] = tmp168;
    current_index++;
  } else {
    start_index = current_index;
    data->simulationInfo->relations[start_index] = (data->localData[0]->timeValue >= (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */));
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = (data->localData[0]->timeValue < (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */));
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = (data->localData[0]->timeValue >= (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */));
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = (data->localData[0]->timeValue < (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[13]] /* dip_start_s PARAM */) + (2.0) * ((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[12]] /* dip_duration_s PARAM */)) + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[22]] /* reclose_gap_s PARAM */));
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[22]] /* $cse3 variable */) >= 0.0);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */) < 0.7);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */) < 0.6);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */) > 0.5);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* t_cool_ok STATE(1) */) < 0.25);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[31]] /* p_psu_w variable */) >= (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[32]] /* p_server_w variable */));
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* soc STATE(1) */) > 0.0);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */) < 0.625);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */) > 0.625);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[36]] /* v_sdp_pu variable */) > 0.01);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */) < 0.20833333333333337);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* t_bus_low STATE(1) */) > 0.002);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* t_bus_ok STATE(1) */) > (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[15]] /* handback_delay_s PARAM */));
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */)) < 172.0);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = (((data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[23]] /* supply_voltage_v PARAM */)) * ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */)) > 178.0);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[8]] /* t_psu_down STATE(1) */) > 1.0 + (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[21]] /* psu_restart_delay_s PARAM */));
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[7]] /* t_cool_s2 STATE(1) */) > 0.02);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[6]] /* t_cool_s1 STATE(1) */) > 0.05);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */) <= 0.625);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[26]] /* e_frac variable */) >= 0.625);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */) <= 0.5);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */) >= 0.6);
    current_index++;

    start_index = current_index;
    data->simulationInfo->relations[start_index] = ((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[9]] /* v_sense_pu STATE(1) */) >= 0.7);
    current_index++;
  }
  
  return 0;
}

#if defined(__cplusplus)
}
#endif
