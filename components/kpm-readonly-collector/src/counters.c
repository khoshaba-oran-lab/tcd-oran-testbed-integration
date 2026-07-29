#include "tcd_kpm_collector/counters.h"

#include <stddef.h>

void tcd_kpm_counters_init(
    tcd_kpm_counters_t *counters
)
{
    if (counters == NULL) {
        return;
    }

    atomic_init(&counters->nodes_discovered, 0U);
    atomic_init(&counters->subscriptions_created, 0U);
    atomic_init(&counters->subscriptions_removed, 0U);
    atomic_init(&counters->indications_received, 0U);
    atomic_init(&counters->records_created, 0U);
    atomic_init(&counters->length_mismatch_records, 0U);
    atomic_init(&counters->no_value_records, 0U);
    atomic_init(&counters->unsupported_records, 0U);
    atomic_init(&counters->callback_errors, 0U);
}

void tcd_kpm_counters_snapshot(
    const tcd_kpm_counters_t *counters,
    tcd_kpm_counter_snapshot_t *snapshot
)
{
    if (counters == NULL || snapshot == NULL) {
        return;
    }

    snapshot->nodes_discovered = atomic_load_explicit(
        &counters->nodes_discovered,
        memory_order_relaxed
    );

    snapshot->subscriptions_created = atomic_load_explicit(
        &counters->subscriptions_created,
        memory_order_relaxed
    );

    snapshot->subscriptions_removed = atomic_load_explicit(
        &counters->subscriptions_removed,
        memory_order_relaxed
    );

    snapshot->indications_received = atomic_load_explicit(
        &counters->indications_received,
        memory_order_relaxed
    );

    snapshot->records_created = atomic_load_explicit(
        &counters->records_created,
        memory_order_relaxed
    );

    snapshot->length_mismatch_records = atomic_load_explicit(
        &counters->length_mismatch_records,
        memory_order_relaxed
    );

    snapshot->no_value_records = atomic_load_explicit(
        &counters->no_value_records,
        memory_order_relaxed
    );

    snapshot->unsupported_records = atomic_load_explicit(
        &counters->unsupported_records,
        memory_order_relaxed
    );

    snapshot->callback_errors = atomic_load_explicit(
        &counters->callback_errors,
        memory_order_relaxed
    );
}
