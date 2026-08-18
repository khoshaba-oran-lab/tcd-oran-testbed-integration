#ifndef TCD_KPM_COLLECTOR_LIFECYCLE_H
#define TCD_KPM_COLLECTOR_LIFECYCLE_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    TCD_KPM_LIFECYCLE_CREATED = 0,
    TCD_KPM_LIFECYCLE_API_INITIALISED,
    TCD_KPM_LIFECYCLE_RIC_CONNECTED,
    TCD_KPM_LIFECYCLE_NODE_DISCOVERED,
    TCD_KPM_LIFECYCLE_NODE_SELECTED,
    TCD_KPM_LIFECYCLE_SUBSCRIPTION_ACTIVE,
    TCD_KPM_LIFECYCLE_RECEIVING,
    TCD_KPM_LIFECYCLE_STOP_REQUESTED,
    TCD_KPM_LIFECYCLE_SUBSCRIPTION_REMOVED,
    TCD_KPM_LIFECYCLE_FAILED,
    TCD_KPM_LIFECYCLE_STOPPED
} tcd_kpm_lifecycle_state_t;

typedef struct {
    tcd_kpm_lifecycle_state_t state;
    bool subscription_active;
    uint64_t logical_subscription_id;
} tcd_kpm_lifecycle_t;

void tcd_kpm_lifecycle_init(
    tcd_kpm_lifecycle_t *lifecycle
);

bool tcd_kpm_lifecycle_can_transition(
    const tcd_kpm_lifecycle_t *lifecycle,
    tcd_kpm_lifecycle_state_t next
);

bool tcd_kpm_lifecycle_transition(
    tcd_kpm_lifecycle_t *lifecycle,
    tcd_kpm_lifecycle_state_t next
);

const char *tcd_kpm_lifecycle_state_string(
    tcd_kpm_lifecycle_state_t state
);

#endif
