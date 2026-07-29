#include "tcd_kpm_collector/kpm_subscription.h"

#include "util/e2ap_ngran_types.h"

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

static const sub_oran_sm_t *select_kpm_profile(
    const fr_args_t *args,
    const tcd_kpm_selected_node_t *selected,
    size_t *match_count
)
{
    if (args == NULL || selected == NULL || match_count == NULL) {
        return NULL;
    }

    *match_count = 0U;
    const sub_oran_sm_t *profile = NULL;

    for (int32_t index = 0; index < args->sub_oran_sm_len; ++index) {
        const sub_oran_sm_t *candidate = &args->sub_oran_sm[index];

        if (
            candidate->name == NULL ||
            strcasecmp(candidate->name, "KPM") != 0 ||
            candidate->ran_type == NULL ||
            strcasecmp(candidate->ran_type, selected->node_type) != 0
        ) {
            continue;
        }

        *match_count += 1U;
        profile = candidate;
    }

    return profile;
}

static bool copy_measurement_name(
    byte_array_t *destination,
    const char *source
)
{
    if (destination == NULL || source == NULL) {
        return false;
    }

    const size_t length = strlen(source);

    if (length == 0U) {
        return false;
    }

    destination->buf = calloc(length, sizeof(*destination->buf));

    if (destination->buf == NULL) {
        return false;
    }

    memcpy(destination->buf, source, length);
    destination->len = length;
    return true;
}

static bool build_measurement_info(
    meas_info_format_1_lst_t *destination,
    const act_name_id_t *action
)
{
    if (destination == NULL || action == NULL) {
        return false;
    }

    memset(destination, 0, sizeof(*destination));

    if (action->name != NULL && strcasecmp(action->name, "null") != 0) {
        destination->meas_type.type = NAME_MEAS_TYPE;

        if (
            !copy_measurement_name(
                &destination->meas_type.name,
                action->name
            )
        ) {
            return false;
        }
    } else {
        if (action->id < 0 || action->id > UINT16_MAX) {
            return false;
        }

        destination->meas_type.type = ID_MEAS_TYPE;
        destination->meas_type.id = (uint16_t)action->id;
    }

    destination->label_info_lst = calloc(
        1U,
        sizeof(*destination->label_info_lst)
    );

    if (destination->label_info_lst == NULL) {
        return false;
    }

    destination->label_info_lst_len = 1U;
    destination->label_info_lst[0].noLabel = calloc(
        1U,
        sizeof(*destination->label_info_lst[0].noLabel)
    );

    if (destination->label_info_lst[0].noLabel == NULL) {
        return false;
    }

    *destination->label_info_lst[0].noLabel = TRUE_ENUM_VALUE;
    return true;
}

static bool build_action_format_1(
    kpm_act_def_format_1_t *destination,
    const sub_oran_sm_t *profile,
    uint32_t period_ms
)
{
    if (
        destination == NULL ||
        profile == NULL ||
        profile->act_len <= 0 ||
        profile->actions == NULL
    ) {
        return false;
    }

    memset(destination, 0, sizeof(*destination));
    destination->gran_period_ms = period_ms;
    destination->meas_info_lst = calloc(
        (size_t)profile->act_len,
        sizeof(*destination->meas_info_lst)
    );

    if (destination->meas_info_lst == NULL) {
        return false;
    }

    destination->meas_info_lst_len = (size_t)profile->act_len;

    for (int32_t index = 0; index < profile->act_len; ++index) {
        if (
            !build_measurement_info(
                &destination->meas_info_lst[index],
                &profile->actions[index]
            )
        ) {
            return false;
        }
    }

    return true;
}

static bool build_action_format_4(
    kpm_act_def_format_4_t *destination,
    const sub_oran_sm_t *profile,
    uint32_t period_ms
)
{
    if (destination == NULL || profile == NULL) {
        return false;
    }

    memset(destination, 0, sizeof(*destination));
    destination->matching_cond_lst = calloc(
        1U,
        sizeof(*destination->matching_cond_lst)
    );

    if (destination->matching_cond_lst == NULL) {
        return false;
    }

    destination->matching_cond_lst_len = 1U;

    test_info_lst_t *test_info =
        &destination->matching_cond_lst[0].test_info_lst;

    test_info->test_cond_type = S_NSSAI_TEST_COND_TYPE;
    test_info->S_NSSAI = TRUE_TEST_COND_TYPE;
    test_info->test_cond = calloc(1U, sizeof(*test_info->test_cond));

    if (test_info->test_cond == NULL) {
        return false;
    }

    *test_info->test_cond = EQUAL_TEST_COND;
    test_info->test_cond_value = calloc(
        1U,
        sizeof(*test_info->test_cond_value)
    );

    if (test_info->test_cond_value == NULL) {
        return false;
    }

    test_info->test_cond_value->type = INTEGER_TEST_COND_VALUE;
    test_info->test_cond_value->int_value = calloc(
        1U,
        sizeof(*test_info->test_cond_value->int_value)
    );

    if (test_info->test_cond_value->int_value == NULL) {
        return false;
    }

    *test_info->test_cond_value->int_value = 1;

    return build_action_format_1(
        &destination->action_def_format_1,
        profile,
        period_ms
    );
}

void tcd_kpm_subscription_request_init(
    tcd_kpm_subscription_request_t *request
)
{
    if (request == NULL) {
        return;
    }

    memset(request, 0, sizeof(*request));
}

bool tcd_kpm_subscription_request_build(
    tcd_kpm_subscription_request_t *request,
    const fr_args_t *args,
    const tcd_kpm_selected_node_t *selected,
    const tcd_kpm_collector_config_t *config,
    char *error,
    size_t error_capacity
)
{
    if (
        request == NULL ||
        args == NULL ||
        selected == NULL ||
        config == NULL
    ) {
        set_error(error, error_capacity, "subscription input is null");
        return false;
    }

    tcd_kpm_subscription_request_destroy(request);

    size_t profile_match_count = 0U;
    const sub_oran_sm_t *profile = select_kpm_profile(
        args,
        selected,
        &profile_match_count
    );

    if (profile_match_count == 0U || profile == NULL) {
        set_error(
            error,
            error_capacity,
            "no KPM profile matched the selected E2 node type"
        );
        return false;
    }

    if (profile_match_count > 1U) {
        set_error(
            error,
            error_capacity,
            "multiple KPM profiles matched the selected E2 node type"
        );
        return false;
    }

    if (
        profile->time <= 0 ||
        profile->act_len <= 0 ||
        profile->actions == NULL
    ) {
        set_error(error, error_capacity, "invalid KPM profile");
        return false;
    }

    if (profile->format != 1 && profile->format != 4) {
        set_error(
            error,
            error_capacity,
            "KPM action definition must use format 1 or 4"
        );
        return false;
    }

    if ((uint32_t)profile->time != config->subscription_period_ms) {
        set_error(
            error,
            error_capacity,
            "collector period does not match the selected KPM profile"
        );
        return false;
    }

    request->data.ev_trg_def.type = FORMAT_1_RIC_EVENT_TRIGGER;
    request->data.ev_trg_def.kpm_ric_event_trigger_format_1.report_period_ms =
        config->subscription_period_ms;

    request->data.ad = calloc(1U, sizeof(*request->data.ad));

    if (request->data.ad == NULL) {
        set_error(error, error_capacity, "KPM action allocation failed");
        return false;
    }

    request->data.sz_ad = 1U;
    request->initialised = true;
    request->action_format = (uint32_t)profile->format;
    request->profile_period_ms = (uint32_t)profile->time;
    request->measurement_count = (size_t)profile->act_len;

    bool built = false;

    if (profile->format == 1) {
        request->data.ad[0].type = FORMAT_1_ACTION_DEFINITION;
        built = build_action_format_1(
            &request->data.ad[0].frm_1,
            profile,
            config->subscription_period_ms
        );
    } else {
        request->data.ad[0].type = FORMAT_4_ACTION_DEFINITION;
        built = build_action_format_4(
            &request->data.ad[0].frm_4,
            profile,
            config->subscription_period_ms
        );
    }

    if (!built) {
        set_error(error, error_capacity, "KPM action construction failed");
        tcd_kpm_subscription_request_destroy(request);
        return false;
    }

    return true;
}

void tcd_kpm_subscription_request_destroy(
    tcd_kpm_subscription_request_t *request
)
{
    if (request == NULL) {
        return;
    }

    if (request->initialised) {
        free_kpm_sub_data(&request->data);
    }

    memset(request, 0, sizeof(*request));
}
