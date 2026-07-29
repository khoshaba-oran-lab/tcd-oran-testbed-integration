#ifndef TCD_KPM_COLLECTOR_KPM_SUBSCRIPTION_H
#define TCD_KPM_COLLECTOR_KPM_SUBSCRIPTION_H

#include "tcd_kpm_collector/config.h"
#include "tcd_kpm_collector/flexric_discovery.h"

#include "sm/kpm_sm/kpm_sm_id_wrapper.h"
#include "util/conf_file.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct {
    kpm_sub_data_t data;
    uint32_t action_format;
    uint32_t profile_period_ms;
    size_t measurement_count;
    bool initialised;
} tcd_kpm_subscription_request_t;

void tcd_kpm_subscription_request_init(
    tcd_kpm_subscription_request_t *request
);

bool tcd_kpm_subscription_request_build(
    tcd_kpm_subscription_request_t *request,
    const fr_args_t *args,
    const tcd_kpm_selected_node_t *selected,
    const tcd_kpm_collector_config_t *config,
    char *error,
    size_t error_capacity
);

void tcd_kpm_subscription_request_destroy(
    tcd_kpm_subscription_request_t *request
);

#endif
