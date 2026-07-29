#ifndef TCD_KPM_COLLECTOR_KPM_CALLBACK_H
#define TCD_KPM_COLLECTOR_KPM_CALLBACK_H

#include "tcd_kpm_collector/config.h"
#include "tcd_kpm_collector/counters.h"
#include "tcd_kpm_collector/record.h"

#include "xApp/e42_xapp_api.h"

#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct {
    tcd_kpm_counters_t *counters;
    uint64_t logical_subscription_id;
    uint64_t max_indications;
    bool structured_debug_stderr;

    atomic_uint_fast64_t next_indication_sequence;
    atomic_bool stop_requested;

    pthread_mutex_t last_record_mutex;
    bool last_record_mutex_initialised;
    bool last_record_present;
    tcd_kpm_measurement_record_t last_record;
} tcd_kpm_callback_context_t;

bool tcd_kpm_callback_context_init(
    tcd_kpm_callback_context_t *context,
    tcd_kpm_counters_t *counters,
    const tcd_kpm_collector_config_t *config,
    uint64_t logical_subscription_id,
    char *error,
    size_t error_capacity
);

void tcd_kpm_callback_context_destroy(
    tcd_kpm_callback_context_t *context
);

bool tcd_kpm_callback_install(
    tcd_kpm_callback_context_t *context,
    char *error,
    size_t error_capacity
);

void tcd_kpm_callback_uninstall(
    tcd_kpm_callback_context_t *context
);

bool tcd_kpm_callback_stop_requested(
    const tcd_kpm_callback_context_t *context
);

bool tcd_kpm_callback_copy_last_record(
    tcd_kpm_callback_context_t *context,
    tcd_kpm_measurement_record_t *record
);

void tcd_kpm_flexric_callback(
    const sm_ag_if_rd_t *rd,
    const global_e2_node_id_t *e2_node
);

#endif
