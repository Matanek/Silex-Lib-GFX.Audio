/* Test-only macOS phase counter. No installed provider or public audio API. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sys/mman.h>

static atomic_int active;
static atomic_uintptr_t owner;
static uint64_t allocations, bytes, copies, copy_bytes;
static int counted(void) {
    return atomic_load(&active) && atomic_load(&owner) == (uintptr_t)pthread_self();
}
static void allocated(size_t size) { if (counted()) { allocations++; bytes += size; } }
static void *probe_malloc(size_t size) { allocated(size); return malloc(size); }
static void *probe_calloc(size_t count, size_t size) { allocated(count*size); return calloc(count,size); }
static void *probe_realloc(void *pointer, size_t size) { allocated(size); return realloc(pointer,size); }
static void *probe_mmap(void *address, size_t length, int protection, int flags, int fd, off_t offset) {
    allocated(length); return mmap(address,length,protection,flags,fd,offset);
}
static void *probe_memcpy(void *to, const void *from, size_t size) {
    if (counted()) { copies++; copy_bytes += size; } return memcpy(to,from,size);
}
static void *probe_memmove(void *to, const void *from, size_t size) {
    if (counted()) { copies++; copy_bytes += size; } return memmove(to,from,size);
}
static pid_t probe_getppid(void) {
    if (!active) {
        atomic_store(&owner,(uintptr_t)pthread_self());
        allocations=bytes=copies=copy_bytes=0; atomic_store(&active,1);
    } else {
        atomic_store(&active,0);
        char line[256];
        int size=snprintf(line,sizeof line,"AUDIO_HEAP allocations=%llu bytes=%llu copies=%llu copy_bytes=%llu\n",
            (unsigned long long)allocations,(unsigned long long)bytes,
            (unsigned long long)copies,(unsigned long long)copy_bytes);
        write(STDERR_FILENO,line,(size_t)size);
    }
    return getppid();
}
#define INTERPOSE(replacement, original) \
    __attribute__((used)) static const struct { const void *new_function; const void *old_function; } \
    interpose_##original __attribute__((section("__DATA,__interpose"))) = {(const void *)&replacement,(const void *)&original}
INTERPOSE(probe_malloc,malloc);
INTERPOSE(probe_calloc,calloc);
INTERPOSE(probe_realloc,realloc);
INTERPOSE(probe_mmap,mmap);
INTERPOSE(probe_memcpy,memcpy);
INTERPOSE(probe_memmove,memmove);
INTERPOSE(probe_getppid,getppid);
