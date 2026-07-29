#include "tcd_kpm_collector/config.h"
#include "tcd_kpm_collector/counters.h"
#include "tcd_kpm_collector/flexric_discovery.h"
#include "tcd_kpm_collector/kpm_callback.h"
#include "tcd_kpm_collector/kpm_subscription.h"
#include "tcd_kpm_collector/lifecycle.h"

#include "sm/kpm_sm/kpm_sm_id_wrapper.h"
#include "util/conf_file.h"
#include "xApp/e42_xapp_api.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#define TCD_KPM_ERROR_CAPACITY 256U
#define TCD_KPM_STOP_TIMEOUT_MS 10000U
#define TCD_KPM_RUNTIME_POLL_MS 10U
#define TCD_KPM_LOGICAL_SUBSCRIPTION_ID 1U

static void sleep_milliseconds(uint32_t milliseconds)
{
    struct timespec request = {
        .tv_sec = (time_t)(milliseconds / 1000U),
        .tv_nsec = (long)(milliseconds % 1000U) * 1000000L
    };

    while (nanosleep(&request, &request) != 0) {
    }
}

static bool monotonic_milliseconds(uint64_t *milliseconds)
{
    if (milliseconds == NULL) {
        return false;
    }

    struct timespec now = {0};

    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
        return false;
    }

    *milliseconds = (uint64_t)now.tv_sec * 1000U +
        (uint64_t)now.tv_nsec / 1000000U;
    return true;
}

static bool transition(
    tcd_kpm_lifecycle_t *lifecycle,
    tcd_kpm_lifecycle_state_t next
)
{
    if (tcd_kpm_lifecycle_transition(lifecycle, next)) {
        return true;
    }

    fprintf(
        stderr,
        "invalid lifecycle transition: %s -> %s\n",
        tcd_kpm_lifecycle_state_string(lifecycle->state),
        tcd_kpm_lifecycle_state_string(next)
    );

    return false;
}

static bool stop_xapp_bounded(void)
{
    uint32_t waited_ms = 0U;

    while (!try_stop_xapp_api()) {
        if (waited_ms >= TCD_KPM_STOP_TIMEOUT_MS) {
            return false;
        }

        sleep_milliseconds(1U);
        waited_ms += 1U;
    }

    return true;
}

static void print_help(const char *program)
{
    printf(
        "Usage: %s -c <flexric-xapp-config>\n"
        "\n"
        "COLLECTOR-01 Action 4 bounded read-only KPM collector.\n"
        "\n"
        "Node selection environment:\n"
        "  TCD_KPM_NODE_TYPE                    Default: gNB_DU\n"
        "  TCD_KPM_NODE_ID                      Optional canonical ID\n"
        "  TCD_KPM_DISCOVERY_TIMEOUT_SECONDS    Default: 10\n"
        "  TCD_KPM_DISCOVERY_POLL_MS            Default: 200\n"
        "\n"
        "Subscription bounds:\n"
        "  TCD_KPM_SUBSCRIPTION_PERIOD_MS       Default: 1000\n"
        "  TCD_KPM_MAX_INDICATIONS              Default: 10; 0 disables\n"
        "  TCD_KPM_DURATION_SECONDS             Default: 30; 0 disables\n"
        "  TCD_KPM_STRUCTURED_DEBUG_STDERR      Default: false\n"
        "\n"
        "Exactly one matching KPM profile must be present in the FlexRIC\n"
        "configuration. RAN control APIs are not used.\n",
        program
    );
}

static void print_counter_snapshot(
    const tcd_kpm_counter_snapshot_t *snapshot
)
{
    printf("NODES_DISCOVERED_COUNTER=%llu\n",
        (unsigned long long)snapshot->nodes_discovered);
    printf("SUBSCRIPTIONS_CREATED_COUNTER=%llu\n",
        (unsigned long long)snapshot->subscriptions_created);
    printf("SUBSCRIPTIONS_REMOVED_COUNTER=%llu\n",
        (unsigned long long)snapshot->subscriptions_removed);
    printf("INDICATIONS_RECEIVED_COUNTER=%llu\n",
        (unsigned long long)snapshot->indications_received);
    printf("RECORDS_CREATED_COUNTER=%llu\n",
        (unsigned long long)snapshot->records_created);
    printf("LENGTH_MISMATCH_RECORDS_COUNTER=%llu\n",
        (unsigned long long)snapshot->length_mismatch_records);
    printf("NO_VALUE_RECORDS_COUNTER=%llu\n",
        (unsigned long long)snapshot->no_value_records);
    printf("UNSUPPORTED_RECORDS_COUNTER=%llu\n",
        (unsigned long long)snapshot->unsupported_records);
    printf("CALLBACK_ERRORS_COUNTER=%llu\n",
        (unsigned long long)snapshot->callback_errors);
}

static void print_last_record_debug(
    const tcd_kpm_measurement_record_t *record
)
{
    fprintf(
        stderr,
        "LAST_RECORD_INDICATION_SEQUENCE=%llu\n",
        (unsigned long long)record->indication.indication_sequence
    );
    fprintf(stderr, "LAST_RECORD_NODE_ID=%s\n", record->indication.e2_node_id);
    fprintf(
        stderr,
        "LAST_RECORD_MESSAGE_FORMAT_RAW=%u\n",
        record->indication.message_format_raw
    );
    fprintf(stderr, "LAST_RECORD_UE_REPORT_INDEX=%u\n", record->ue_report_index);
    fprintf(stderr, "LAST_RECORD_MEAS_DATA_INDEX=%u\n", record->meas_data_index);
    fprintf(
        stderr,
        "LAST_RECORD_MEAS_RECORD_INDEX=%u\n",
        record->meas_record_index
    );
    fprintf(stderr, "LAST_RECORD_MEAS_INFO_INDEX=%u\n", record->meas_info_index);
    fprintf(
        stderr,
        "LAST_RECORD_DESCRIPTOR_TYPE=%s\n",
        tcd_kpm_descriptor_type_string(record->descriptor.type)
    );

    if (record->descriptor.measurement_name_present) {
        fprintf(
            stderr,
            "LAST_RECORD_MEASUREMENT_NAME=%s\n",
            record->descriptor.measurement_name
        );
    }

    if (record->descriptor.measurement_id_present) {
        fprintf(
            stderr,
            "LAST_RECORD_MEASUREMENT_ID=%u\n",
            record->descriptor.measurement_id
        );
    }

    fprintf(
        stderr,
        "LAST_RECORD_VALUE_TYPE=%s\n",
        tcd_kpm_value_type_string(record->value.type)
    );
    fprintf(
        stderr,
        "LAST_RECORD_STRUCTURAL_STATUS=%s\n",
        tcd_kpm_structural_status_string(record->structural_status)
    );
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--help") == 0) {
        print_help(argv[0]);
        return 0;
    }

    tcd_kpm_collector_config_t config;
    tcd_kpm_counters_t counters;
    tcd_kpm_lifecycle_t lifecycle;
    tcd_kpm_subscription_request_t subscription_request;
    tcd_kpm_callback_context_t callback_context;

    tcd_kpm_collector_config_defaults(&config);
    tcd_kpm_counters_init(&counters);
    tcd_kpm_lifecycle_init(&lifecycle);
    tcd_kpm_subscription_request_init(&subscription_request);
    memset(&callback_context, 0, sizeof(callback_context));

    char error[TCD_KPM_ERROR_CAPACITY] = {0};

    if (
        !tcd_kpm_collector_config_load_environment(
            &config,
            error,
            sizeof(error)
        )
    ) {
        fprintf(stderr, "configuration error: %s\n", error);
        return 64;
    }

    fr_args_t args = init_fr_args(argc, argv);
    bool api_initialised = false;
    bool nodes_owned = false;
    bool callback_context_initialised = false;
    bool callback_installed = false;
    bool subscription_created = false;
    int subscription_handle = -1;

    e2_node_arr_xapp_t nodes = {0};

    init_xapp_api(&args);
    api_initialised = true;

    if (!transition(&lifecycle, TCD_KPM_LIFECYCLE_API_INITIALISED)) {
        goto failure;
    }

    if (!transition(&lifecycle, TCD_KPM_LIFECYCLE_RIC_CONNECTED)) {
        goto failure;
    }

    const uint64_t timeout_ms =
        (uint64_t)config.discovery_timeout_seconds * 1000U;
    uint64_t elapsed_ms = 0U;

    while (elapsed_ms <= timeout_ms) {
        nodes = e2_nodes_xapp_api();
        nodes_owned = true;

        if (nodes.len > 0U) {
            break;
        }

        free_e2_node_arr_xapp(&nodes);
        nodes_owned = false;
        nodes = (e2_node_arr_xapp_t){0};

        if (elapsed_ms == timeout_ms) {
            break;
        }

        sleep_milliseconds(config.discovery_poll_ms);
        elapsed_ms += config.discovery_poll_ms;

        if (elapsed_ms > timeout_ms) {
            elapsed_ms = timeout_ms;
        }
    }

    if (!nodes_owned || nodes.len == 0U) {
        fprintf(stderr, "E2 node discovery timed out\n");
        goto failure;
    }

    if (!transition(&lifecycle, TCD_KPM_LIFECYCLE_NODE_DISCOVERED)) {
        goto failure;
    }

    tcd_kpm_selected_node_t selected = {0};
    size_t match_count = 0U;

    if (
        !tcd_kpm_select_flexric_node(
            &nodes,
            &config,
            &counters,
            &selected,
            &match_count,
            error,
            sizeof(error)
        )
    ) {
        fprintf(stderr, "node selection error: %s\n", error);
        goto failure;
    }

    if (!transition(&lifecycle, TCD_KPM_LIFECYCLE_NODE_SELECTED)) {
        goto failure;
    }

    if (
        !tcd_kpm_subscription_request_build(
            &subscription_request,
            &args,
            &selected,
            &config,
            error,
            sizeof(error)
        )
    ) {
        fprintf(stderr, "subscription construction error: %s\n", error);
        goto failure;
    }

    lifecycle.logical_subscription_id = TCD_KPM_LOGICAL_SUBSCRIPTION_ID;

    if (
        !tcd_kpm_callback_context_init(
            &callback_context,
            &counters,
            &config,
            lifecycle.logical_subscription_id,
            error,
            sizeof(error)
        )
    ) {
        fprintf(stderr, "callback context error: %s\n", error);
        goto failure;
    }

    callback_context_initialised = true;

    if (
        !tcd_kpm_callback_install(
            &callback_context,
            error,
            sizeof(error)
        )
    ) {
        fprintf(stderr, "callback installation error: %s\n", error);
        goto failure;
    }

    callback_installed = true;

    sm_ans_xapp_t answer = report_sm_xapp_api(
        &nodes.n[selected.source_index].id,
        SM_KPM_ID,
        &subscription_request.data,
        tcd_kpm_flexric_callback
    );

    if (!answer.success) {
        fprintf(
            stderr,
            "KPM subscription creation failed%s%s\n",
            answer.u.reason == NULL ? "" : ": ",
            answer.u.reason == NULL ? "" : answer.u.reason
        );
        goto failure;
    }

    subscription_handle = answer.u.handle;
    subscription_created = true;

    atomic_fetch_add_explicit(
        &counters.subscriptions_created,
        1U,
        memory_order_relaxed
    );

    if (!transition(&lifecycle, TCD_KPM_LIFECYCLE_SUBSCRIPTION_ACTIVE)) {
        goto failure;
    }

    printf("COLLECTOR_EVENT=node_selected\n");
    printf("NODES_DISCOVERED=%u\n", (unsigned int)nodes.len);
    printf("MATCH_COUNT=%zu\n", match_count);
    printf("NODE_SOURCE_INDEX=%zu\n", selected.source_index);
    printf("NODE_TYPE=%s\n", selected.node_type);
    printf("NODE_TYPE_RAW=%u\n", selected.node_type_raw);
    printf("NODE_ID=%s\n", selected.node_id);
    printf("COLLECTOR_EVENT=subscription_created\n");
    printf("SUBSCRIPTION_CREATED=yes\n");
    printf("SUBSCRIPTION_HANDLE=%d\n", subscription_handle);
    printf("LOGICAL_SUBSCRIPTION_ID=%llu\n",
        (unsigned long long)lifecycle.logical_subscription_id);
    printf("KPM_ACTION_FORMAT=%u\n", subscription_request.action_format);
    printf("KPM_MEASUREMENT_COUNT=%zu\n",
        subscription_request.measurement_count);
    printf("KPM_PROFILE_PERIOD_MS=%u\n",
        subscription_request.profile_period_ms);
    printf("KPM_SUBSCRIPTION_PERIOD_MS=%u\n",
        config.subscription_period_ms);
    printf("MAX_INDICATIONS=%llu\n",
        (unsigned long long)config.max_indications);
    printf("DURATION_SECONDS=%u\n", config.duration_seconds);
    printf("COLLECTOR_STAGE=bounded_kpm_subscription\n");

    uint64_t runtime_start_ms = 0U;

    if (!monotonic_milliseconds(&runtime_start_ms)) {
        fprintf(stderr, "monotonic clock read failed\n");
        goto failure;
    }

    const char *stop_reason = NULL;
    bool receiving_transition_done = false;

    for (;;) {
        const uint64_t indications = atomic_load_explicit(
            &counters.indications_received,
            memory_order_relaxed
        );

        if (indications > 0U && !receiving_transition_done) {
            if (!transition(&lifecycle, TCD_KPM_LIFECYCLE_RECEIVING)) {
                goto failure;
            }

            receiving_transition_done = true;
        }

        if (tcd_kpm_callback_stop_requested(&callback_context)) {
            stop_reason = "max_indications";
            break;
        }

        uint64_t now_ms = 0U;

        if (!monotonic_milliseconds(&now_ms)) {
            fprintf(stderr, "monotonic clock read failed\n");
            goto failure;
        }

        if (
            config.duration_seconds > 0U &&
            now_ms - runtime_start_ms >=
                (uint64_t)config.duration_seconds * 1000U
        ) {
            stop_reason = "duration";
            break;
        }

        sleep_milliseconds(TCD_KPM_RUNTIME_POLL_MS);
    }

    if (!transition(&lifecycle, TCD_KPM_LIFECYCLE_STOP_REQUESTED)) {
        goto failure;
    }

    rm_report_sm_xapp_api(subscription_handle);
    subscription_created = false;
    subscription_handle = -1;

    atomic_fetch_add_explicit(
        &counters.subscriptions_removed,
        1U,
        memory_order_relaxed
    );

    if (!transition(&lifecycle, TCD_KPM_LIFECYCLE_SUBSCRIPTION_REMOVED)) {
        goto failure;
    }

    tcd_kpm_callback_uninstall(&callback_context);
    callback_installed = false;

    if (!stop_xapp_bounded()) {
        fprintf(stderr, "FlexRIC xApp API shutdown timed out\n");
        goto failure_without_api_stop;
    }

    api_initialised = false;

    if (!transition(&lifecycle, TCD_KPM_LIFECYCLE_STOPPED)) {
        goto failure_without_api_stop;
    }

    tcd_kpm_counter_snapshot_t snapshot = {0};
    tcd_kpm_counters_snapshot(&counters, &snapshot);

    printf("STOP_REASON=%s\n", stop_reason);
    printf("SUBSCRIPTION_REMOVED=yes\n");
    print_counter_snapshot(&snapshot);

    tcd_kpm_measurement_record_t last_record;
    const bool last_record_present = tcd_kpm_callback_copy_last_record(
        &callback_context,
        &last_record
    );

    printf("LAST_RECORD_PRESENT=%s\n",
        last_record_present ? "yes" : "no");

    if (last_record_present && config.structured_debug_stderr) {
        print_last_record_debug(&last_record);
    }

    printf("FINAL_LIFECYCLE_STATE=%s\n",
        tcd_kpm_lifecycle_state_string(lifecycle.state));
    printf("COLLECTOR_RESULT=PASS\n");

    if (nodes_owned) {
        free_e2_node_arr_xapp(&nodes);
        nodes_owned = false;
    }

    if (callback_context_initialised) {
        tcd_kpm_callback_context_destroy(&callback_context);
        callback_context_initialised = false;
    }

    tcd_kpm_subscription_request_destroy(&subscription_request);
    free_fr_args(&args);
    return 0;

failure:
    if (
        lifecycle.state != TCD_KPM_LIFECYCLE_FAILED &&
        lifecycle.state != TCD_KPM_LIFECYCLE_STOPPED
    ) {
        (void)tcd_kpm_lifecycle_transition(
            &lifecycle,
            TCD_KPM_LIFECYCLE_FAILED
        );
    }

    if (subscription_created) {
        rm_report_sm_xapp_api(subscription_handle);
        subscription_created = false;
        subscription_handle = -1;

        atomic_fetch_add_explicit(
            &counters.subscriptions_removed,
            1U,
            memory_order_relaxed
        );

        (void)tcd_kpm_lifecycle_transition(
            &lifecycle,
            TCD_KPM_LIFECYCLE_SUBSCRIPTION_REMOVED
        );
    }

    if (callback_installed) {
        tcd_kpm_callback_uninstall(&callback_context);
        callback_installed = false;
    }

    if (api_initialised) {
        if (!stop_xapp_bounded()) {
            fprintf(stderr, "FlexRIC xApp API failure shutdown timed out\n");
        }

        api_initialised = false;
    }

    if (
        lifecycle.state == TCD_KPM_LIFECYCLE_FAILED &&
        !lifecycle.subscription_active
    ) {
        (void)tcd_kpm_lifecycle_transition(
            &lifecycle,
            TCD_KPM_LIFECYCLE_STOPPED
        );
    } else if (lifecycle.state == TCD_KPM_LIFECYCLE_SUBSCRIPTION_REMOVED) {
        (void)tcd_kpm_lifecycle_transition(
            &lifecycle,
            TCD_KPM_LIFECYCLE_STOPPED
        );
    }

failure_without_api_stop:
    if (nodes_owned) {
        free_e2_node_arr_xapp(&nodes);
        nodes_owned = false;
    }

    if (callback_context_initialised) {
        tcd_kpm_callback_context_destroy(&callback_context);
        callback_context_initialised = false;
    }

    tcd_kpm_subscription_request_destroy(&subscription_request);
    free_fr_args(&args);

    fprintf(
        stderr,
        "COLLECTOR_RESULT=FAIL\n"
        "FINAL_LIFECYCLE_STATE=%s\n",
        tcd_kpm_lifecycle_state_string(lifecycle.state)
    );

    return 1;
}
