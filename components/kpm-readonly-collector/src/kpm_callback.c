#include "tcd_kpm_collector/kpm_callback.h"

#include "tcd_kpm_collector/flexric_discovery.h"
#include "tcd_kpm_collector/kpm_validation.h"

#include "sm/kpm_sm/kpm_sm_id_wrapper.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

static _Atomic(tcd_kpm_callback_context_t *) active_context = NULL;

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

static int64_t realtime_unix_ns(void)
{
    struct timespec now = {0};

    if (clock_gettime(CLOCK_REALTIME, &now) != 0) {
        return 0;
    }

    return (int64_t)now.tv_sec * 1000000000LL + (int64_t)now.tv_nsec;
}

static uint32_t length_to_u32(size_t value)
{
    return value > UINT32_MAX ? UINT32_MAX : (uint32_t)value;
}

static void copy_ue_id(
    tcd_kpm_ue_id_t *destination,
    const ue_id_e2sm_t *source,
    bool *supported
)
{
    if (destination == NULL || supported == NULL) {
        return;
    }

    memset(destination, 0, sizeof(*destination));
    destination->type = TCD_KPM_UE_ID_UNKNOWN;
    *supported = true;

    if (source == NULL) {
        return;
    }

    destination->raw_type = (uint32_t)source->type;

    switch (source->type) {
    case GNB_UE_ID_E2SM:
        destination->type = TCD_KPM_UE_ID_GNB;
        destination->amf_ue_ngap_id_present = true;
        destination->amf_ue_ngap_id = source->gnb.amf_ue_ngap_id;

        if (
            source->gnb.gnb_cu_ue_f1ap_lst_len > 0U &&
            source->gnb.gnb_cu_ue_f1ap_lst != NULL
        ) {
            destination->gnb_cu_ue_f1ap_present = true;
            destination->gnb_cu_ue_f1ap =
                source->gnb.gnb_cu_ue_f1ap_lst[0];
        }

        if (source->gnb.ran_ue_id != NULL) {
            destination->ran_ue_id_present = true;
            destination->ran_ue_id = *source->gnb.ran_ue_id;
        }
        break;

    case GNB_DU_UE_ID_E2SM:
        destination->type = TCD_KPM_UE_ID_GNB_DU;
        destination->gnb_cu_ue_f1ap_present = true;
        destination->gnb_cu_ue_f1ap = source->gnb_du.gnb_cu_ue_f1ap;

        if (source->gnb_du.ran_ue_id != NULL) {
            destination->ran_ue_id_present = true;
            destination->ran_ue_id = *source->gnb_du.ran_ue_id;
        }
        break;

    case GNB_CU_UP_UE_ID_E2SM:
        destination->type = TCD_KPM_UE_ID_GNB_CU_UP;
        destination->gnb_cu_cp_ue_e1ap_present = true;
        destination->gnb_cu_cp_ue_e1ap =
            source->gnb_cu_up.gnb_cu_cp_ue_e1ap;

        if (source->gnb_cu_up.ran_ue_id != NULL) {
            destination->ran_ue_id_present = true;
            destination->ran_ue_id = *source->gnb_cu_up.ran_ue_id;
        }
        break;

    default:
        *supported = false;
        break;
    }
}

static bool copy_descriptor(
    tcd_kpm_measurement_descriptor_t *destination,
    const meas_info_format_1_lst_t *source
)
{
    if (destination == NULL) {
        return false;
    }

    memset(destination, 0, sizeof(*destination));
    destination->type = TCD_KPM_DESCRIPTOR_UNKNOWN;

    if (source == NULL) {
        return false;
    }

    destination->raw_type = (uint32_t)source->meas_type.type;

    switch (source->meas_type.type) {
    case NAME_MEAS_TYPE: {
        destination->type = TCD_KPM_DESCRIPTOR_NAME;
        destination->measurement_name_present = true;
        destination->measurement_name_length = source->meas_type.name.len;

        if (
            source->meas_type.name.len > 0U &&
            source->meas_type.name.buf == NULL
        ) {
            return false;
        }

        size_t copy_length = source->meas_type.name.len;

        if (copy_length >= sizeof(destination->measurement_name)) {
            copy_length = sizeof(destination->measurement_name) - 1U;
            destination->measurement_name_truncated = true;
        }

        if (copy_length > 0U) {
            memcpy(
                destination->measurement_name,
                source->meas_type.name.buf,
                copy_length
            );
        }

        destination->measurement_name[copy_length] = '\0';
        return true;
    }

    case ID_MEAS_TYPE:
        destination->type = TCD_KPM_DESCRIPTOR_ID;
        destination->measurement_id_present = true;
        destination->measurement_id = (uint32_t)source->meas_type.id;
        return true;

    default:
        return false;
    }
}

static bool copy_value(
    tcd_kpm_value_t *destination,
    const meas_record_lst_t *source,
    bool *no_value
)
{
    if (destination == NULL || no_value == NULL) {
        return false;
    }

    memset(destination, 0, sizeof(*destination));
    destination->type = TCD_KPM_VALUE_UNKNOWN;
    *no_value = false;

    if (source == NULL) {
        return false;
    }

    destination->raw_type = (uint32_t)source->value;

    switch (source->value) {
    case INTEGER_MEAS_VALUE:
        destination->type = TCD_KPM_VALUE_INTEGER;
        destination->data.integer_value = (int64_t)source->int_val;
        return true;

    case REAL_MEAS_VALUE:
        destination->type = TCD_KPM_VALUE_REAL;
        destination->data.real_value = source->real_val;
        return true;

    case NO_VALUE_MEAS_VALUE:
        destination->type = TCD_KPM_VALUE_NO_VALUE;
        *no_value = true;
        return true;

    default:
        return false;
    }
}

static void retain_record(
    tcd_kpm_callback_context_t *context,
    const tcd_kpm_measurement_record_t *record
)
{
    if (context == NULL || record == NULL) {
        return;
    }

    atomic_fetch_add_explicit(
        &context->counters->records_created,
        1U,
        memory_order_relaxed
    );

    switch (record->structural_status) {
    case TCD_KPM_STATUS_LENGTH_MISMATCH:
        atomic_fetch_add_explicit(
            &context->counters->length_mismatch_records,
            1U,
            memory_order_relaxed
        );
        break;

    case TCD_KPM_STATUS_NO_VALUE:
        atomic_fetch_add_explicit(
            &context->counters->no_value_records,
            1U,
            memory_order_relaxed
        );
        break;

    case TCD_KPM_STATUS_UNSUPPORTED_DESCRIPTOR:
    case TCD_KPM_STATUS_UNSUPPORTED_VALUE_TYPE:
    case TCD_KPM_STATUS_UNSUPPORTED_UE_ID:
    case TCD_KPM_STATUS_UNKNOWN_MESSAGE_FORMAT:
        atomic_fetch_add_explicit(
            &context->counters->unsupported_records,
            1U,
            memory_order_relaxed
        );
        break;

    case TCD_KPM_STATUS_INVALID_INPUT:
        atomic_fetch_add_explicit(
            &context->counters->callback_errors,
            1U,
            memory_order_relaxed
        );
        break;

    case TCD_KPM_STATUS_OK:
        break;
    }

    if (
        context->last_record_mutex_initialised &&
        pthread_mutex_trylock(&context->last_record_mutex) == 0
    ) {
        context->last_record = *record;
        context->last_record_present = true;
        (void)pthread_mutex_unlock(&context->last_record_mutex);
    }
}

static void process_format_1(
    tcd_kpm_callback_context_t *context,
    const tcd_kpm_indication_context_t *indication,
    uint32_t ue_report_index,
    const ue_id_e2sm_t *ue_source,
    const kpm_ind_msg_format_1_t *message
)
{
    if (context == NULL || indication == NULL || message == NULL) {
        return;
    }

    if (
        message->meas_data_lst_len > 0U &&
        message->meas_data_lst == NULL
    ) {
        atomic_fetch_add_explicit(
            &context->counters->callback_errors,
            1U,
            memory_order_relaxed
        );
        return;
    }

    bool ue_supported = true;
    tcd_kpm_ue_id_t copied_ue = {0};
    copy_ue_id(&copied_ue, ue_source, &ue_supported);

    for (
        size_t data_index = 0U;
        data_index < message->meas_data_lst_len;
        ++data_index
    ) {
        const meas_data_lst_t *data = &message->meas_data_lst[data_index];

        const size_t record_count = data->meas_record_len;
        const size_t info_count = message->meas_info_lst_len;
        const tcd_kpm_row_shape_t shape = {
            .metadata_available = info_count > 0U,
            .metadata = message->meas_info_lst,
            .metadata_len = info_count,
            .record = data->meas_record_lst,
            .record_len = record_count,
            .maximum_supported_length = 65535U,
        };
        const tcd_kpm_row_validation_result_t validation =
            tcd_kpm_validate_row_shape(&shape);

        if (!validation.row_accepted) {
            tcd_kpm_measurement_record_t diagnostic;
            tcd_kpm_measurement_record_reset(&diagnostic);

            diagnostic.indication = *indication;
            diagnostic.ue_report_index = ue_report_index;
            diagnostic.ue_id = copied_ue;
            diagnostic.meas_data_index = length_to_u32(data_index);
            diagnostic.meas_record_index = UINT32_MAX;
            diagnostic.meas_info_index = UINT32_MAX;
            diagnostic.meas_data_lst_len =
                length_to_u32(message->meas_data_lst_len);
            diagnostic.meas_info_lst_len = length_to_u32(info_count);
            diagnostic.meas_record_len = length_to_u32(record_count);

            if (data->incomplete_flag != NULL) {
                diagnostic.incomplete_flag_present = true;
                diagnostic.incomplete_flag =
                    *data->incomplete_flag == TRUE_ENUM_VALUE;
            }

            diagnostic.structural_status =
                validation.status == TCD_KPM_ROW_LENGTH_MISMATCH
                    ? TCD_KPM_STATUS_LENGTH_MISMATCH
                    : TCD_KPM_STATUS_INVALID_INPUT;

            retain_record(context, &diagnostic);
            continue;
        }

        for (
            size_t index = 0U;
            index < validation.normalised_value_count;
            ++index
        ) {
            tcd_kpm_measurement_record_t record;
            tcd_kpm_measurement_record_reset(&record);

            record.indication = *indication;
            record.ue_report_index = ue_report_index;
            record.ue_id = copied_ue;
            record.meas_data_index = length_to_u32(data_index);
            record.meas_record_index = length_to_u32(index);
            record.meas_info_index = length_to_u32(index);
            record.meas_data_lst_len =
                length_to_u32(message->meas_data_lst_len);
            record.meas_info_lst_len = length_to_u32(info_count);
            record.meas_record_len = length_to_u32(record_count);

            if (data->incomplete_flag != NULL) {
                record.incomplete_flag_present = true;
                record.incomplete_flag =
                    *data->incomplete_flag == TRUE_ENUM_VALUE;
            }

            const bool descriptor_supported = copy_descriptor(
                &record.descriptor,
                &message->meas_info_lst[index]
            );

            bool no_value = false;
            const bool value_supported = copy_value(
                &record.value,
                &data->meas_record_lst[index],
                &no_value
            );

            if (!ue_supported) {
                record.structural_status = TCD_KPM_STATUS_UNSUPPORTED_UE_ID;
            } else if (!descriptor_supported) {
                record.structural_status =
                    TCD_KPM_STATUS_UNSUPPORTED_DESCRIPTOR;
            } else if (!value_supported) {
                record.structural_status =
                    TCD_KPM_STATUS_UNSUPPORTED_VALUE_TYPE;
            } else if (no_value) {
                record.structural_status = TCD_KPM_STATUS_NO_VALUE;
            } else {
                record.structural_status = TCD_KPM_STATUS_OK;
            }

            retain_record(context, &record);
        }
    }
}

bool tcd_kpm_callback_context_init(
    tcd_kpm_callback_context_t *context,
    tcd_kpm_counters_t *counters,
    const tcd_kpm_collector_config_t *config,
    uint64_t logical_subscription_id,
    char *error,
    size_t error_capacity
)
{
    if (context == NULL || counters == NULL || config == NULL) {
        set_error(error, error_capacity, "callback context input is null");
        return false;
    }

    memset(context, 0, sizeof(*context));
    context->counters = counters;
    context->logical_subscription_id = logical_subscription_id;
    context->max_indications = config->max_indications;
    context->structured_debug_stderr = config->structured_debug_stderr;
    atomic_init(&context->next_indication_sequence, 0U);
    atomic_init(&context->stop_requested, false);

    if (pthread_mutex_init(&context->last_record_mutex, NULL) != 0) {
        set_error(error, error_capacity, "callback mutex initialisation failed");
        return false;
    }

    context->last_record_mutex_initialised = true;
    return true;
}

void tcd_kpm_callback_context_destroy(
    tcd_kpm_callback_context_t *context
)
{
    if (context == NULL) {
        return;
    }

    tcd_kpm_callback_uninstall(context);

    if (context->last_record_mutex_initialised) {
        (void)pthread_mutex_destroy(&context->last_record_mutex);
    }

    memset(context, 0, sizeof(*context));
}

bool tcd_kpm_callback_install(
    tcd_kpm_callback_context_t *context,
    char *error,
    size_t error_capacity
)
{
    if (context == NULL || context->counters == NULL) {
        set_error(error, error_capacity, "callback context is invalid");
        return false;
    }

    tcd_kpm_callback_context_t *expected = NULL;

    if (
        !atomic_compare_exchange_strong_explicit(
            &active_context,
            &expected,
            context,
            memory_order_release,
            memory_order_relaxed
        )
    ) {
        set_error(error, error_capacity, "a KPM callback is already installed");
        return false;
    }

    return true;
}

void tcd_kpm_callback_uninstall(
    tcd_kpm_callback_context_t *context
)
{
    if (context == NULL) {
        return;
    }

    tcd_kpm_callback_context_t *expected = context;

    (void)atomic_compare_exchange_strong_explicit(
        &active_context,
        &expected,
        NULL,
        memory_order_acq_rel,
        memory_order_relaxed
    );
}

bool tcd_kpm_callback_stop_requested(
    const tcd_kpm_callback_context_t *context
)
{
    if (context == NULL) {
        return true;
    }

    return atomic_load_explicit(
        &context->stop_requested,
        memory_order_acquire
    );
}

bool tcd_kpm_callback_copy_last_record(
    tcd_kpm_callback_context_t *context,
    tcd_kpm_measurement_record_t *record
)
{
    if (
        context == NULL ||
        record == NULL ||
        !context->last_record_mutex_initialised
    ) {
        return false;
    }

    if (pthread_mutex_lock(&context->last_record_mutex) != 0) {
        return false;
    }

    const bool present = context->last_record_present;

    if (present) {
        *record = context->last_record;
    }

    (void)pthread_mutex_unlock(&context->last_record_mutex);
    return present;
}

void tcd_kpm_flexric_callback(
    const sm_ag_if_rd_t *rd,
    const global_e2_node_id_t *e2_node
)
{
    tcd_kpm_callback_context_t *context = atomic_load_explicit(
        &active_context,
        memory_order_acquire
    );

    if (context == NULL) {
        return;
    }

    if (
        rd == NULL ||
        e2_node == NULL ||
        rd->type != INDICATION_MSG_AGENT_IF_ANS_V0 ||
        rd->ind.type != KPM_STATS_V3_0
    ) {
        atomic_fetch_add_explicit(
            &context->counters->callback_errors,
            1U,
            memory_order_relaxed
        );
        return;
    }

    const kpm_ind_data_t *kpm = &rd->ind.kpm.ind;
    const uint64_t sequence = atomic_fetch_add_explicit(
        &context->next_indication_sequence,
        1U,
        memory_order_relaxed
    ) + 1U;

    atomic_fetch_add_explicit(
        &context->counters->indications_received,
        1U,
        memory_order_relaxed
    );

    tcd_kpm_indication_context_t indication = {0};
    indication.indication_sequence = sequence;
    indication.logical_subscription_id = context->logical_subscription_id;
    indication.receive_timestamp_unix_ns = realtime_unix_ns();
    indication.kpm_header_timestamp_raw =
        kpm->hdr.kpm_ric_ind_hdr_format_1.collectStartTime;
    indication.message_format_raw = (uint32_t)kpm->msg.type;
    indication.e2_node_type_raw = (uint32_t)e2_node->type;

    if (
        !tcd_kpm_format_node_id(
            e2_node,
            indication.e2_node_id,
            sizeof(indication.e2_node_id)
        )
    ) {
        atomic_fetch_add_explicit(
            &context->counters->callback_errors,
            1U,
            memory_order_relaxed
        );
        (void)snprintf(
            indication.e2_node_id,
            sizeof(indication.e2_node_id),
            "%s",
            "unavailable"
        );
    }

    if (kpm->msg.type == FORMAT_1_INDICATION_MESSAGE) {
        indication.ue_report_count = 0U;
        process_format_1(
            context,
            &indication,
            UINT32_MAX,
            NULL,
            &kpm->msg.frm_1
        );
    } else if (kpm->msg.type == FORMAT_3_INDICATION_MESSAGE) {
        const kpm_ind_msg_format_3_t *message = &kpm->msg.frm_3;
        indication.ue_report_count =
            length_to_u32(message->ue_meas_report_lst_len);

        if (
            message->ue_meas_report_lst_len > 0U &&
            message->meas_report_per_ue == NULL
        ) {
            atomic_fetch_add_explicit(
                &context->counters->callback_errors,
                1U,
                memory_order_relaxed
            );
        } else {
            for (
                size_t ue_index = 0U;
                ue_index < message->ue_meas_report_lst_len;
                ++ue_index
            ) {
                const meas_report_per_ue_t *report =
                    &message->meas_report_per_ue[ue_index];

                process_format_1(
                    context,
                    &indication,
                    length_to_u32(ue_index),
                    &report->ue_meas_report_lst,
                    &report->ind_msg_format_1
                );
            }
        }
    } else {
        tcd_kpm_measurement_record_t record;
        tcd_kpm_measurement_record_reset(&record);
        record.indication = indication;
        record.ue_report_index = UINT32_MAX;
        record.meas_data_index = UINT32_MAX;
        record.meas_record_index = UINT32_MAX;
        record.meas_info_index = UINT32_MAX;
        record.structural_status = TCD_KPM_STATUS_UNKNOWN_MESSAGE_FORMAT;
        retain_record(context, &record);
    }

    if (
        context->max_indications > 0U &&
        sequence >= context->max_indications
    ) {
        atomic_store_explicit(
            &context->stop_requested,
            true,
            memory_order_release
        );
    }
}
