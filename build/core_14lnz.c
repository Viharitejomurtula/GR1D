/* Linearization */
#include "core_model.h"
#if defined(__cplusplus)
extern "C" {
#endif

const char *core_linear_model_frame()
{
  errorStreamPrint(OMC_LOG_STDOUT, 0, "Linearization disabled. Use compiler flag `--linearizationDumpLanguage` to change target language.");
  return "";
}
const char *core_linear_model_datarecovery_frame()
{
  errorStreamPrint(OMC_LOG_STDOUT, 0, "Linearization disabled. Use compiler flag `--linearizationDumpLanguage` to change target language.");
  return "";
}

#if defined(__cplusplus)
}
#endif
