#include "tcd_kpm_collector/lifecycle.h"

#include <stddef.h>

void tcd_kpm_lifecycle_init(
    tcd_kpm_lifecycle_t *lifecycle
)
{
    if (lifecycle == NULL) {
        return;
    }

    lifecycle->state = TCD_KPM_LIFECYCLE_CREATED;
    lifecycle->subscription_active = false;
    lifecycle->logical_subscription_id = 0U;
}

bool tcd_kpm_lifecycle_can_transition(
    const tcd_kpm_lifecycle_t *lifecycle,
    tcd_kpm_lifecycle_state_t next
)
{
    if (lifecycle == NULL) {
        return false;
    }

    switch (lifecycle->state) {
    case TCD_KPM_LIFECYCLE_CREATED:
        return next == TCD_KPM_LIFECYCLE_API_INITIALISED ||
               next == TCD_KPM_LIFECYCLE_FAILED;

    case TCD_KPM_LIFECYCLE_API_INITIALISED:
        return next == TCD_KPM_LIFECYCLE_RIC_CONNECTED ||
               next == TCD_KPM_LIFECYCLE_STOP_REQUESTED ||
               next == TCD_KPM_LIFECYCLE_FAILED;

    case TCD_KPM_LIFECYCLE_RIC_CONNECTED:
        return next == TCD_KPM_LIFECYCLE_NODE_DISCOVERED ||
               next == TCD_KPM_LIFECYCLE_STOP_REQUESTED ||
               next == TCD_KPM_LIFECYCLE_FAILED;

    case TCD_KPM_LIFECYCLE_NODE_DISCOVERED:
        return next == TCD_KPM_LIFECYCLE_NODE_SELECTED ||
               next == TCD_KPM_LIFECYCLE_STOP_REQUESTED ||
               next == TCD_KPM_LIFECYCLE_FAILED;

    case TCD_KPM_LIFECYCLE_NODE_SELECTED:
        return next == TCD_KPM_LIFECYCLE_SUBSCRIPTION_ACTIVE ||
               next == TCD_KPM_LIFECYCLE_STOP_REQUESTED ||
               next == TCD_KPM_LIFECYCLE_FAILED;

    case TCD_KPM_LIFECYCLE_SUBSCRIPTION_ACTIVE:
        return next == TCD_KPM_LIFECYCLE_RECEIVING ||
               next == TCD_KPM_LIFECYCLE_STOP_REQUESTED ||
               next == TCD_KPM_LIFECYCLE_FAILED;

    case TCD_KPM_LIFECYCLE_RECEIVING:
        return next == TCD_KPM_LIFECYCLE_STOP_REQUESTED ||
               next == TCD_KPM_LIFECYCLE_FAILED;

    case TCD_KPM_LIFECYCLE_STOP_REQUESTED:
        if (next == TCD_KPM_LIFECYCLE_SUBSCRIPTION_REMOVED) {
            return lifecycle->subscription_active;
        }

        if (next == TCD_KPM_LIFECYCLE_STOPPED) {
            return !lifecycle->subscription_active;
        }

        return next == TCD_KPM_LIFECYCLE_FAILED;

    case TCD_KPM_LIFECYCLE_FAILED:
        if (next == TCD_KPM_LIFECYCLE_SUBSCRIPTION_REMOVED) {
            return lifecycle->subscription_active;
        }

        if (next == TCD_KPM_LIFECYCLE_STOPPED) {
            return !lifecycle->subscription_active;
        }

        return false;

    case TCD_KPM_LIFECYCLE_SUBSCRIPTION_REMOVED:
        return next == TCD_KPM_LIFECYCLE_STOPPED;

    case TCD_KPM_LIFECYCLE_STOPPED:
        return false;
    }

    return false;
}

bool tcd_kpm_lifecycle_transition(
    tcd_kpm_lifecycle_t *lifecycle,
    tcd_kpm_lifecycle_state_t next
)
{
    if (!tcd_kpm_lifecycle_can_transition(lifecycle, next)) {
        return false;
    }

    if (next == TCD_KPM_LIFECYCLE_SUBSCRIPTION_ACTIVE) {
        lifecycle->subscription_active = true;
    } else if (next == TCD_KPM_LIFECYCLE_SUBSCRIPTION_REMOVED) {
        lifecycle->subscription_active = false;
    }

    lifecycle->state = next;
    return true;
}

const char *tcd_kpm_lifecycle_state_string(
    tcd_kpm_lifecycle_state_t state
)
{
    switch (state) {
    case TCD_KPM_LIFECYCLE_CREATED:
        return "created";
    case TCD_KPM_LIFECYCLE_API_INITIALISED:
        return "api_initialised";
    case TCD_KPM_LIFECYCLE_RIC_CONNECTED:
        return "ric_connected";
    case TCD_KPM_LIFECYCLE_NODE_DISCOVERED:
        return "node_discovered";
    case TCD_KPM_LIFECYCLE_NODE_SELECTED:
        return "node_selected";
    case TCD_KPM_LIFECYCLE_SUBSCRIPTION_ACTIVE:
        return "subscription_active";
    case TCD_KPM_LIFECYCLE_RECEIVING:
        return "receiving";
    case TCD_KPM_LIFECYCLE_STOP_REQUESTED:
        return "stop_requested";
    case TCD_KPM_LIFECYCLE_SUBSCRIPTION_REMOVED:
        return "subscription_removed";
    case TCD_KPM_LIFECYCLE_FAILED:
        return "failed";
    case TCD_KPM_LIFECYCLE_STOPPED:
        return "stopped";
    }

    return "invalid_lifecycle_state";
}
