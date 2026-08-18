#ifndef TCD_KPM_COLLECTOR_COUNTERS_H
#define TCD_KPM_COLLECTOR_COUNTERS_H

#include <stdatomic.h>
#include <stdint.h>

typedef struct {
    atomic_uint_fast64_t nodes_discovered;
    atomic_uint_fast64_t subscriptions_created;
    atomic_uint_fast64_t subscriptions_removed;
    atomic_uint_fast64_t indications_received;
    atomic_uint_fast64_t records_created;
    atomic_uint_fast64_t length_mismatch_records;
    atomic_uint_fast64_t no_value_records;
    atomic_uint_fast64_t unsupported_records;
    atomic_uint_fast64_t callback_errors;
} tcd_kpm_counters_t;

typedef struct {
    uint64_t nodes_discovered;
    uint64_t subscriptions_created;
    uint64_t subscriptions_removed;
    uint64_t indications_received;
    uint64_t records_created;
    uint64_t length_mismatch_records;
    uint64_t no_value_records;
    uint64_t unsupported_records;
    uint64_t callback_errors;
} tcd_kpm_counter_snapshot_t;

void tcd_kpm_counters_init(
    tcd_kpm_counters_t *counters
);

void tcd_kpm_counters_snapshot(
    const tcd_kpm_counters_t *counters,
    tcd_kpm_counter_snapshot_t *snapshot
);

#endif
