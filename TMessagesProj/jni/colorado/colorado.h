#include <stdbool.h>

#ifdef NDEBUG
#define LOG_DISABLED
#endif
#define PACKAGE_NAME "com.sakurartro.sakuragram"_iobfs.c_str()
#define CERT_HASH 0x7794812d
#define CERT_SIZE 0x381

#ifdef __cplusplus
extern "C" {
#endif

bool check_signature();

#ifdef __cplusplus
}
#endif
