#if defined(__cplusplus)
  extern "C" {
#endif
  int smoke_mayer(DATA* data, modelica_real** res, short*);
  int smoke_lagrange(DATA* data, modelica_real** res, short *, short *);
  int smoke_getInputVarIndicesInOptimization(DATA* data, int* input_var_indices);
  int smoke_pickUpBoundsForInputsInOptimization(DATA* data, modelica_real* min, modelica_real* max, modelica_real*nominal, modelica_boolean *useNominal, char ** name, modelica_real * start, modelica_real * startTimeOpt);
  int smoke_setInputData(DATA *data, const modelica_boolean file);
  int smoke_getTimeGrid(DATA *data, modelica_integer * nsi, modelica_real**t);
#if defined(__cplusplus)
}
#endif
