/* Jacobians */
static _index_t one_dim[1] = { 1 };
static modelica_real nominal_data[1] = { 1.0 };
static modelica_real start_data[1]   = { 0.0 };
static modelica_real min_data[1]   = { -DBL_MAX };
static modelica_real max_data[1]   = { DBL_MAX };
static const REAL_ATTRIBUTE dummyREAL_ATTRIBUTE = {
  .unit = NULL,
  .displayUnit = NULL,
  .min = {
    .ndims     = 1,
    .dim_size  = one_dim,
    .data      = (void*) min_data,
    .flexible  = FALSE
  },
  .max = {
    .ndims     = 1,
    .dim_size  = one_dim,
    .data      = (void*) max_data,
    .flexible  = FALSE
  },
  .fixed = FALSE,
  .useNominal = FALSE,
  .nominal = {
    .ndims     = 1,
    .dim_size  = one_dim,
    .data      = (void*) nominal_data,
    .flexible  = FALSE
  },
  .start = {
    .ndims     = 1,
    .dim_size  = one_dim,
    .data      = (void*) start_data,
    .flexible  = FALSE
  }
};

#if defined(__cplusplus)
extern "C" {
#endif

/* Jacobian Variables */
#define RideThroughCore_INDEX_JAC_NLSJac0 0
int RideThroughCore_functionJacNLSJac0_column(DATA* data, threadData_t *threadData, JACOBIAN *thisJacobian, JACOBIAN *parentJacobian);
int RideThroughCore_initialAnalyticJacobianNLSJac0(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);
void RideThroughCore_JacNLSJac0_DAG(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);


#define RideThroughCore_INDEX_JAC_NLSJac1 1
int RideThroughCore_functionJacNLSJac1_column(DATA* data, threadData_t *threadData, JACOBIAN *thisJacobian, JACOBIAN *parentJacobian);
int RideThroughCore_initialAnalyticJacobianNLSJac1(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);
void RideThroughCore_JacNLSJac1_DAG(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);


#define RideThroughCore_INDEX_JAC_ADJ 2
int RideThroughCore_functionJacADJ_column(DATA* data, threadData_t *threadData, JACOBIAN *thisJacobian, JACOBIAN *parentJacobian);
int RideThroughCore_initialAnalyticJacobianADJ(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);
void RideThroughCore_JacADJ_DAG(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);


#define RideThroughCore_INDEX_JAC_H 3
int RideThroughCore_functionJacH_column(DATA* data, threadData_t *threadData, JACOBIAN *thisJacobian, JACOBIAN *parentJacobian);
int RideThroughCore_initialAnalyticJacobianH(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);
void RideThroughCore_JacH_DAG(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);


#define RideThroughCore_INDEX_JAC_F 4
int RideThroughCore_functionJacF_column(DATA* data, threadData_t *threadData, JACOBIAN *thisJacobian, JACOBIAN *parentJacobian);
int RideThroughCore_initialAnalyticJacobianF(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);
void RideThroughCore_JacF_DAG(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);


#define RideThroughCore_INDEX_JAC_D 5
int RideThroughCore_functionJacD_column(DATA* data, threadData_t *threadData, JACOBIAN *thisJacobian, JACOBIAN *parentJacobian);
int RideThroughCore_initialAnalyticJacobianD(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);
void RideThroughCore_JacD_DAG(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);


#define RideThroughCore_INDEX_JAC_C 6
int RideThroughCore_functionJacC_column(DATA* data, threadData_t *threadData, JACOBIAN *thisJacobian, JACOBIAN *parentJacobian);
int RideThroughCore_initialAnalyticJacobianC(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);
void RideThroughCore_JacC_DAG(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);


#define RideThroughCore_INDEX_JAC_B 7
int RideThroughCore_functionJacB_column(DATA* data, threadData_t *threadData, JACOBIAN *thisJacobian, JACOBIAN *parentJacobian);
int RideThroughCore_initialAnalyticJacobianB(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);
void RideThroughCore_JacB_DAG(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);


#define RideThroughCore_INDEX_JAC_A 8
int RideThroughCore_functionJacA_column(DATA* data, threadData_t *threadData, JACOBIAN *thisJacobian, JACOBIAN *parentJacobian);
int RideThroughCore_initialAnalyticJacobianA(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);
void RideThroughCore_JacA_DAG(DATA* data, threadData_t *threadData, JACOBIAN *jacobian);

#if defined(__cplusplus)
}
#endif
