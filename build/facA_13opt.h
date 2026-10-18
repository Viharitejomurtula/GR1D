#if defined(__cplusplus)
  extern "C" {
#endif
  int facA_mayer(DATA* data, modelica_real** res, short*);
  int facA_lagrange(DATA* data, modelica_real** res, short *, short *);
  int facA_getInputVarIndicesInOptimization(DATA* data, int* input_var_indices);
  int facA_pickUpBoundsForInputsInOptimization(DATA* data, modelica_real* min, modelica_real* max, modelica_real*nominal, modelica_boolean *useNominal, char ** name, modelica_real * start, modelica_real * startTimeOpt);
  int facA_setInputData(DATA *data, const modelica_boolean file);
  int facA_getTimeGrid(DATA *data, modelica_integer * nsi, modelica_real**t);
#if defined(__cplusplus)
}
#endif
