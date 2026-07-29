#ifndef TCD_KPM_COLLECTOR_CONFIG_H
#define TCD_KPM_COLLECTOR_CONFIG_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define TCD_KPM_NODE_TYPE_CAPACITY 64U
#define TCD_KPM_NODE_SELECTOR_CAPACITY 128U

typedef struct {
    char node_type[TCD_KPM_NODE_TYPE_CAPACITY];
    char node_id[TCD_KPM_NODE_SELECTOR_CAPACITY];

    bool require_exactly_one_match;

    uint32_t discovery_timeout_seconds;
    uint32_t discovery_poll_ms;

    uint32_t subscription_period_ms;
    uint64_t max_indications;
    uint32_t duration_seconds;

    bool structured_debug_stderr;
} tcd_kpm_collector_config_t;

void tcd_kpm_collector_config_defaults(
    tcd_kpm_collector_config_t *config
);

bool tcd_kpm_collector_config_load_environment(
    tcd_kpm_collector_config_t *config,
    char *error,
    size_t error_capacity
);

bool tcd_kpm_collector_config_has_finite_limit(
    const tcd_kpm_collector_config_t *config
);

#endif
