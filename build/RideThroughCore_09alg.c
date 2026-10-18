/* Algebraic */
#include "RideThroughCore_model.h"

#ifdef __cplusplus
extern "C" {
#endif

/* forwarded equations */
extern void RideThroughCore_eqFunction_65(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_66(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_67(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_68(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_80(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_88(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_112(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_117(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_118(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_119(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_120(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_121(DATA* data, threadData_t *threadData);
extern void RideThroughCore_eqFunction_122(DATA* data, threadData_t *threadData);

static void functionAlg_system0(DATA *data, threadData_t *threadData)
{
  static void (*const eqFunctions[13])(DATA*, threadData_t*) = {
    RideThroughCore_eqFunction_65,
    RideThroughCore_eqFunction_66,
    RideThroughCore_eqFunction_67,
    RideThroughCore_eqFunction_68,
    RideThroughCore_eqFunction_80,
    RideThroughCore_eqFunction_88,
    RideThroughCore_eqFunction_112,
    RideThroughCore_eqFunction_117,
    RideThroughCore_eqFunction_118,
    RideThroughCore_eqFunction_119,
    RideThroughCore_eqFunction_120,
    RideThroughCore_eqFunction_121,
    RideThroughCore_eqFunction_122
  };
  
  if (data->simulationInfo->evalSelection) {
    for (int i = 0; i < data->simulationInfo->evalSelection->n; i++) {
      int id = data->simulationInfo->evalSelection->idx[i];
      eqFunctions[id](data, threadData);
    }
  } else {
    for (int id = 0; id < 13; id++) {
      eqFunctions[id](data, threadData);
    }
  }
}
/* for continuous time variables */
int RideThroughCore_functionAlgebraics(DATA *data, threadData_t *threadData)
{

#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_tick(SIM_TIMER_ALGEBRAICS);
#endif
  data->simulationInfo->callStatistics.functionAlgebraics++;

  RideThroughCore_function_savePreSynchronous(data, threadData);
  
  functionAlg_system0(data, threadData);

#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_accumulate(SIM_TIMER_ALGEBRAICS);
#endif

  return 0;
}

#ifdef __cplusplus
}
#endif
