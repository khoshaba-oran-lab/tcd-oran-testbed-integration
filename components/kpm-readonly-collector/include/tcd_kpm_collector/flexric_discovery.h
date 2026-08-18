#ifndef TCD_KPM_COLLECTOR_FLEXRIC_DISCOVERY_H
#define TCD_KPM_COLLECTOR_FLEXRIC_DISCOVERY_H

#include "tcd_kpm_collector/config.h"
#include "tcd_kpm_collector/counters.h"

#include "xApp/e42_xapp_api.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct {
    size_t source_index;

    uint32_t node_type_raw;
    char node_type[TCD_KPM_NODE_TYPE_CAPACITY];

    uint64_t nb_id;

    bool cu_du_id_present;
    uint64_t cu_du_id;

    char node_id[TCD_KPM_NODE_SELECTOR_CAPACITY];
} tcd_kpm_selected_node_t;

bool tcd_kpm_format_node_id(
    const global_e2_node_id_t *node_id,
    char *destination,
    size_t destination_capacity
);

bool tcd_kpm_select_flexric_node(
    const e2_node_arr_xapp_t *nodes,
    const tcd_kpm_collector_config_t *config,
    tcd_kpm_counters_t *counters,
    tcd_kpm_selected_node_t *selected,
    size_t *match_count,
    char *error,
    size_t error_capacity
);

#endif
