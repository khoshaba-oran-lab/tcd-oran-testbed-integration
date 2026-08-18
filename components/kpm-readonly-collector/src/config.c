#include "tcd_kpm_collector/config.h"

#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
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

static bool copy_environment_string(
    const char *name,
    char *destination,
    size_t destination_capacity,
    char *error,
    size_t error_capacity
)
{
    const char *value = getenv(name);

    if (value == NULL) {
        return true;
    }

    const size_t length = strlen(value);

    if (length == 0U || length >= destination_capacity) {
        set_error(error, error_capacity, "invalid environment string");
        return false;
    }

    memcpy(destination, value, length + 1U);
    return true;
}

static bool parse_u32_environment(
    const char *name,
    uint32_t minimum,
    uint32_t maximum,
    uint32_t *destination,
    char *error,
    size_t error_capacity
)
{
    const char *value = getenv(name);

    if (value == NULL) {
        return true;
    }

    errno = 0;
    char *end = NULL;
    const unsigned long parsed = strtoul(value, &end, 10);

    if (
        errno != 0 ||
        end == value ||
        *end != '\0' ||
        parsed > UINT_MAX ||
        parsed < minimum ||
        parsed > maximum
    ) {
        set_error(error, error_capacity, "invalid unsigned environment value");
        return false;
    }

    *destination = (uint32_t)parsed;
    return true;
}

static bool parse_u64_environment(
    const char *name,
    uint64_t minimum,
    uint64_t maximum,
    uint64_t *destination,
    char *error,
    size_t error_capacity
)
{
    const char *value = getenv(name);

    if (value == NULL) {
        return true;
    }

    errno = 0;
    char *end = NULL;
    const unsigned long long parsed = strtoull(value, &end, 10);

    if (
        errno != 0 ||
        end == value ||
        *end != '\0' ||
        parsed < minimum ||
        parsed > maximum
    ) {
        set_error(error, error_capacity, "invalid 64-bit environment value");
        return false;
    }

    *destination = (uint64_t)parsed;
    return true;
}

static bool parse_bool_environment(
    const char *name,
    bool *destination,
    char *error,
    size_t error_capacity
)
{
    const char *value = getenv(name);

    if (value == NULL) {
        return true;
    }

    if (
        strcmp(value, "1") == 0 ||
        strcasecmp(value, "true") == 0 ||
        strcasecmp(value, "yes") == 0
    ) {
        *destination = true;
        return true;
    }

    if (
        strcmp(value, "0") == 0 ||
        strcasecmp(value, "false") == 0 ||
        strcasecmp(value, "no") == 0
    ) {
        *destination = false;
        return true;
    }

    set_error(error, error_capacity, "invalid boolean environment value");
    return false;
}

static bool parse_required_exact_match(
    bool *destination,
    char *error,
    size_t error_capacity
)
{
    if (
        !parse_bool_environment(
            "TCD_KPM_REQUIRE_EXACTLY_ONE_MATCH",
            destination,
            error,
            error_capacity
        )
    ) {
        return false;
    }

    if (!*destination) {
        set_error(
            error,
            error_capacity,
            "COLLECTOR-01 requires exactly one matching E2 node"
        );
        return false;
    }

    return true;
}

void tcd_kpm_collector_config_defaults(
    tcd_kpm_collector_config_t *config
)
{
    if (config == NULL) {
        return;
    }

    memset(config, 0, sizeof(*config));

    (void)snprintf(
        config->node_type,
        sizeof(config->node_type),
        "%s",
        "gNB_DU"
    );

    config->require_exactly_one_match = true;
    config->discovery_timeout_seconds = 10U;
    config->discovery_poll_ms = 200U;
    config->subscription_period_ms = 1000U;
    config->max_indications = 10U;
    config->duration_seconds = 30U;
    config->structured_debug_stderr = false;
}

bool tcd_kpm_collector_config_load_environment(
    tcd_kpm_collector_config_t *config,
    char *error,
    size_t error_capacity
)
{
    if (config == NULL) {
        set_error(error, error_capacity, "configuration pointer is null");
        return false;
    }

    if (
        !copy_environment_string(
            "TCD_KPM_NODE_TYPE",
            config->node_type,
            sizeof(config->node_type),
            error,
            error_capacity
        )
    ) {
        return false;
    }

    const char *node_id = getenv("TCD_KPM_NODE_ID");

    if (node_id != NULL) {
        const size_t length = strlen(node_id);

        if (length >= sizeof(config->node_id)) {
            set_error(error, error_capacity, "node identifier is too long");
            return false;
        }

        memcpy(config->node_id, node_id, length + 1U);
    }

    if (
        !parse_required_exact_match(
            &config->require_exactly_one_match,
            error,
            error_capacity
        ) ||
        !parse_u32_environment(
            "TCD_KPM_DISCOVERY_TIMEOUT_SECONDS",
            1U,
            300U,
            &config->discovery_timeout_seconds,
            error,
            error_capacity
        ) ||
        !parse_u32_environment(
            "TCD_KPM_DISCOVERY_POLL_MS",
            10U,
            5000U,
            &config->discovery_poll_ms,
            error,
            error_capacity
        ) ||
        !parse_u32_environment(
            "TCD_KPM_SUBSCRIPTION_PERIOD_MS",
            1U,
            60000U,
            &config->subscription_period_ms,
            error,
            error_capacity
        ) ||
        !parse_u64_environment(
            "TCD_KPM_MAX_INDICATIONS",
            0U,
            1000000000ULL,
            &config->max_indications,
            error,
            error_capacity
        ) ||
        !parse_u32_environment(
            "TCD_KPM_DURATION_SECONDS",
            0U,
            86400U,
            &config->duration_seconds,
            error,
            error_capacity
        ) ||
        !parse_bool_environment(
            "TCD_KPM_STRUCTURED_DEBUG_STDERR",
            &config->structured_debug_stderr,
            error,
            error_capacity
        )
    ) {
        return false;
    }

    if (!tcd_kpm_collector_config_has_finite_limit(config)) {
        set_error(
            error,
            error_capacity,
            "at least one runtime bound must be non-zero"
        );
        return false;
    }

    return true;
}

bool tcd_kpm_collector_config_has_finite_limit(
    const tcd_kpm_collector_config_t *config
)
{
    if (config == NULL) {
        return false;
    }

    return config->max_indications > 0U ||
           config->duration_seconds > 0U;
}
