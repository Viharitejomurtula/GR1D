#if defined(__cplusplus)
  extern "C" {
#endif
  int RideThroughCore_mayer(DATA* data, modelica_real** res, short*);
  int RideThroughCore_lagrange(DATA* data, modelica_real** res, short *, short *);
  int RideThroughCore_getInputVarIndicesInOptimization(DATA* data, int* input_var_indices);
  int RideThroughCore_pickUpBoundsForInputsInOptimization(DATA* data, modelica_real* min, modelica_real* max, modelica_real*nominal, modelica_boolean *useNominal, char ** name, modelica_real * start, modelica_real * startTimeOpt);
  int RideThroughCore_setInputData(DATA *data, const modelica_boolean file);
  int RideThroughCore_getTimeGrid(DATA *data, modelica_integer * nsi, modelica_real**t);
#if defined(__cplusplus)
}
#endif
