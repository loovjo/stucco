// #ifdef beans
#include "helloboi.h"
#define S_(x) #x
#define S(x) S_(x)
#define dprintf(...) printf(__FILE__ ":" S(__LINE__) ": " __VA_ARGS__)
#define E 2.71

dprintf(E);

#undef E
// #else
// #error "no beans"
// #endif

