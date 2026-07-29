#include "tcd_kpm_collector/flexric_discovery.h"

#include "util/e2ap_ngran_types.h"

#include <stdio.h>
#include <string.h>
#include <strings.h>

static void set_error(
    char *error,
    size_t error_capacity,
    const char *message
)
{
    if (error == NULL || error_capacity == 0U) {
        return;
    }

    (void)snprintf(error, error_capacity, "%s", message);
}

static bool node_type_from_string(
    const char *name,
    e2ap_ngran_node_t *node_type
)
{
    if (name == NULL || node_type == NULL) {
        return false;
    }

    struct node_type_mapping {
        const char *name;
        e2ap_ngran_node_t value;
    };

    static const struct node_type_mapping mappings[] = {
        {"eNB", e2ap_ngran_eNB},
        {"ng_eNB", e2ap_ngran_ng_eNB},
        {"gNB", e2ap_ngran_gNB},
        {"eNB_CU", e2ap_ngran_eNB_CU},
        {"ng_eNB_CU", e2ap_ngran_ng_eNB_CU},
        {"gNB_CU", e2ap_ngran_gNB_CU},
        {"eNB_DU", e2ap_ngran_eNB_DU},
        {"gNB_DU", e2ap_ngran_gNB_DU},
        {"gNB_CUCP", e2ap_ngran_gNB_CUCP},
        {"gNB_CUUP", e2ap_ngran_gNB_CUUP}
    };

    const size_t count = sizeof(mappings) / sizeof(mappings[0]);

    for (size_t index = 0U; index < count; ++index) {
        if (strcasecmp(name, mappings[index].name) == 0) {
            *node_type = mappings[index].value;
            return true;
        }
    }

    return false;
}

bool tcd_kpm_format_node_id(
    const global_e2_node_id_t *node_id,
    char *destination,
    size_t destination_capacity
)
{
    if (
        node_id == NULL ||
        destination == NULL ||
        destination_capacity == 0U
    ) {
        return false;
    }

    const unsigned long long nb_id =
        (unsigned long long)node_id->nb_id.nb_id;

    int written = 0;

    if (node_id->cu_du_id != NULL) {
        const unsigned long long cu_du_id =
            (unsigned long long)*node_id->cu_du_id;

        written = snprintf(
            destination,
            destination_capacity,
            "nb_id=%llu;cu_du_id=%llu",
            nb_id,
            cu_du_id
        );
    } else {
        written = snprintf(
            destination,
            destination_capacity,
            "nb_id=%llu",
            nb_id
        );
    }

    return written >= 0 &&
           (size_t)written < destination_capacity;
}

bool tcd_kpm_select_flexric_node(
    const e2_node_arr_xapp_t *nodes,
    const tcd_kpm_collector_config_t *config,
    tcd_kpm_counters_t *counters,
    tcd_kpm_selected_node_t *selected,
    size_t *match_count,
    char *error,
    size_t error_capacity
)
{
    if (
        nodes == NULL ||
        config == NULL ||
        counters == NULL ||
        selected == NULL ||
        match_count == NULL
    ) {
        set_error(error, error_capacity, "node selector input is null");
        return false;
    }

    if (!config->require_exactly_one_match) {
        set_error(error, error_capacity, "ambiguous selection is forbidden");
        return false;
    }

    e2ap_ngran_node_t requested_type;

    if (!node_type_from_string(config->node_type, &requested_type)) {
        set_error(error, error_capacity, "unsupported node type selector");
        return false;
    }

    memset(selected, 0, sizeof(*selected));
    *match_count = 0U;

    atomic_store_explicit(
        &counters->nodes_discovered,
        (uint64_t)nodes->len,
        memory_order_relaxed
    );

    for (size_t index = 0U; index < (size_t)nodes->len; ++index) {
        const global_e2_node_id_t *candidate = &nodes->n[index].id;

        if (candidate->type != requested_type) {
            continue;
        }

        char canonical_id[TCD_KPM_NODE_SELECTOR_CAPACITY];

        if (
            !tcd_kpm_format_node_id(
                candidate,
                canonical_id,
                sizeof(canonical_id)
            )
        ) {
            set_error(error, error_capacity, "node identifier formatting failed");
            return false;
        }

        if (
            config->node_id[0] != '\0' &&
            strcmp(config->node_id, canonical_id) != 0
        ) {
            continue;
        }

        *match_count += 1U;

        if (*match_count == 1U) {
            selected->source_index = index;
            selected->node_type_raw = (uint32_t)candidate->type;
            selected->nb_id = (uint64_t)candidate->nb_id.nb_id;

            if (candidate->cu_du_id != NULL) {
                selected->cu_du_id_present = true;
                selected->cu_du_id = *candidate->cu_du_id;
            }

            const char *type_name =
                get_e2ap_ngran_name(candidate->type);

            if (type_name == NULL) {
                type_name = "unknown";
            }

            (void)snprintf(
                selected->node_type,
                sizeof(selected->node_type),
                "%s",
                type_name
            );

            (void)snprintf(
                selected->node_id,
                sizeof(selected->node_id),
                "%s",
                canonical_id
            );
        }
    }

    if (*match_count == 0U) {
        set_error(error, error_capacity, "no E2 node matched selector");
        return false;
    }

    if (*match_count > 1U) {
        set_error(error, error_capacity, "E2 node selector is ambiguous");
        return false;
    }

    return true;
}
