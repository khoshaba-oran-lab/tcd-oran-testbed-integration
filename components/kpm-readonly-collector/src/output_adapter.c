#include "tcd_kpm_collector/output_adapter.h"

#define tcd_kpm_structural_status_t tcd_kpm_canonical_structural_status_t
#define tcd_kpm_descriptor_type_t tcd_kpm_canonical_descriptor_type_t
#define tcd_kpm_value_type_t tcd_kpm_canonical_value_type_t
#define TCD_KPM_DESCRIPTOR_UNKNOWN TCD_KPM_CANONICAL_DESCRIPTOR_UNKNOWN
#define TCD_KPM_DESCRIPTOR_NAME TCD_KPM_CANONICAL_DESCRIPTOR_NAME
#define TCD_KPM_DESCRIPTOR_ID TCD_KPM_CANONICAL_DESCRIPTOR_ID
#define TCD_KPM_VALUE_UNKNOWN TCD_KPM_CANONICAL_VALUE_UNKNOWN
#define TCD_KPM_VALUE_INTEGER TCD_KPM_CANONICAL_VALUE_INTEGER
#define TCD_KPM_VALUE_REAL TCD_KPM_CANONICAL_VALUE_REAL
#define TCD_KPM_VALUE_NO_VALUE TCD_KPM_CANONICAL_VALUE_NO_VALUE
#ifdef TCD_KPM_NODE_TYPE_CAPACITY
#undef TCD_KPM_NODE_TYPE_CAPACITY
#endif
#ifdef TCD_KPM_NODE_ID_CAPACITY
#undef TCD_KPM_NODE_ID_CAPACITY
#endif
#ifdef TCD_KPM_UE_ID_TYPE_CAPACITY
#undef TCD_KPM_UE_ID_TYPE_CAPACITY
#endif
#ifdef TCD_KPM_UE_ID_VALUE_CAPACITY
#undef TCD_KPM_UE_ID_VALUE_CAPACITY
#endif
#ifdef TCD_KPM_MEASUREMENT_NAME_CAPACITY
#undef TCD_KPM_MEASUREMENT_NAME_CAPACITY
#endif
#ifdef TCD_KPM_DIAGNOSTIC_CODE_CAPACITY
#undef TCD_KPM_DIAGNOSTIC_CODE_CAPACITY
#endif
#ifdef TCD_KPM_DIAGNOSTIC_MESSAGE_CAPACITY
#undef TCD_KPM_DIAGNOSTIC_MESSAGE_CAPACITY
#endif
#include "tcd_kpm_collector/output_pipeline.h"
#undef TCD_KPM_VALUE_NO_VALUE
#undef TCD_KPM_VALUE_REAL
#undef TCD_KPM_VALUE_INTEGER
#undef TCD_KPM_VALUE_UNKNOWN
#undef TCD_KPM_DESCRIPTOR_ID
#undef TCD_KPM_DESCRIPTOR_NAME
#undef TCD_KPM_DESCRIPTOR_UNKNOWN
#undef tcd_kpm_value_type_t
#undef tcd_kpm_descriptor_type_t
#undef tcd_kpm_structural_status_t

#include "tcd_kpm_collector/canonical_serialize.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

static void copy_text(char *destination, size_t capacity, const char *source)
{
    if (destination == NULL || capacity == 0U) {
        return;
    }
    if (source == NULL) {
        destination[0] = '\0';
        return;
    }
    (void)snprintf(destination, capacity, "%s", source);
}

static void copy_node(
    tcd_kpm_canonical_record_t *destination,
    const tcd_kpm_measurement_record_t *source)
{
    destination->has_node_type = true;
    (void)snprintf(
        destination->node_type,
        sizeof(destination->node_type),
        "raw_%u",
        source->indication.e2_node_type_raw);

    if (source->indication.e2_node_id[0] != '\0') {
        destination->has_node_id = true;
        copy_text(
            destination->node_id,
            sizeof(destination->node_id),
            source->indication.e2_node_id);
    }
}

static void copy_ue(
    tcd_kpm_canonical_record_t *destination,
    const tcd_kpm_measurement_record_t *source)
{
    switch (source->ue_id.type) {
    case TCD_KPM_UE_ID_GNB:
        copy_text(destination->ue_id_type, sizeof(destination->ue_id_type), "gnb");
        if (source->ue_id.amf_ue_ngap_id_present) {
            destination->has_ue_id_value = true;
            (void)snprintf(
                destination->ue_id_value,
                sizeof(destination->ue_id_value),
                "amf_ue_ngap_id=%llu",
                (unsigned long long)source->ue_id.amf_ue_ngap_id);
        }
        break;
    case TCD_KPM_UE_ID_GNB_DU:
        copy_text(destination->ue_id_type, sizeof(destination->ue_id_type), "gnb_du");
        if (source->ue_id.gnb_cu_ue_f1ap_present) {
            destination->has_ue_id_value = true;
            (void)snprintf(
                destination->ue_id_value,
                sizeof(destination->ue_id_value),
                "gnb_cu_ue_f1ap=%u",
                source->ue_id.gnb_cu_ue_f1ap);
        }
        break;
    case TCD_KPM_UE_ID_GNB_CU_UP:
        copy_text(destination->ue_id_type, sizeof(destination->ue_id_type), "gnb_cu_up");
        if (source->ue_id.gnb_cu_cp_ue_e1ap_present) {
            destination->has_ue_id_value = true;
            (void)snprintf(
                destination->ue_id_value,
                sizeof(destination->ue_id_value),
                "gnb_cu_cp_ue_e1ap=%u",
                source->ue_id.gnb_cu_cp_ue_e1ap);
        }
        break;
    case TCD_KPM_UE_ID_UNKNOWN:
    default:
        copy_text(destination->ue_id_type, sizeof(destination->ue_id_type), "unknown");
        break;
    }
}

static tcd_kpm_canonical_structural_status_t map_diagnostic_status(
    const tcd_kpm_measurement_record_t *source)
{
    switch (source->structural_status) {
    case TCD_KPM_STATUS_LENGTH_MISMATCH:
        return TCD_KPM_STRUCTURAL_STATUS_LENGTH_MISMATCH;
    case TCD_KPM_STATUS_UNSUPPORTED_UE_ID:
        return TCD_KPM_STRUCTURAL_STATUS_UNSUPPORTED_UE_ID;
    case TCD_KPM_STATUS_UNSUPPORTED_DESCRIPTOR:
        return TCD_KPM_STRUCTURAL_STATUS_UNSUPPORTED_DESCRIPTOR;
    case TCD_KPM_STATUS_UNSUPPORTED_VALUE_TYPE:
        return TCD_KPM_STRUCTURAL_STATUS_UNSUPPORTED_VALUE_TYPE;
    case TCD_KPM_STATUS_INVALID_INPUT:
    case TCD_KPM_STATUS_UNKNOWN_MESSAGE_FORMAT:
    case TCD_KPM_STATUS_OK:
    case TCD_KPM_STATUS_NO_VALUE:
    default:
        return TCD_KPM_STRUCTURAL_STATUS_INVALID_INPUT;
    }
}

static const char *diagnostic_code(
    const tcd_kpm_measurement_record_t *source)
{
    switch (source->structural_status) {
    case TCD_KPM_STATUS_LENGTH_MISMATCH:
        return "length_mismatch";
    case TCD_KPM_STATUS_UNSUPPORTED_UE_ID:
        return "unsupported_ue_id";
    case TCD_KPM_STATUS_UNSUPPORTED_DESCRIPTOR:
        return "unsupported_descriptor";
    case TCD_KPM_STATUS_UNSUPPORTED_VALUE_TYPE:
        return "unsupported_value_type";
    case TCD_KPM_STATUS_UNKNOWN_MESSAGE_FORMAT:
        return "unknown_message_format";
    case TCD_KPM_STATUS_INVALID_INPUT:
    case TCD_KPM_STATUS_OK:
    case TCD_KPM_STATUS_NO_VALUE:
    default:
        return "invalid_input";
    }
}

static void copy_common(
    tcd_kpm_canonical_record_t *destination,
    const tcd_kpm_measurement_record_t *source)
{
    destination->indication_sequence =
        source->indication.indication_sequence;
    destination->receive_timestamp_us =
        source->indication.receive_timestamp_unix_ns > 0
            ? (uint64_t)source->indication.receive_timestamp_unix_ns / 1000U
            : 0U;
    if (source->indication.kpm_header_timestamp_raw > 0U) {
        destination->has_kpm_header_timestamp_us = true;
        destination->kpm_header_timestamp_us =
            source->indication.kpm_header_timestamp_raw;
    }
    destination->message_format = source->indication.message_format_raw;
    copy_node(destination, source);

    if (source->ue_report_index != UINT32_MAX) {
        destination->has_ue_report_index = true;
        destination->ue_report_index = source->ue_report_index;
    }
    copy_ue(destination, source);

    if (source->meas_data_index != UINT32_MAX) {
        destination->has_meas_data_index = true;
        destination->meas_data_index = source->meas_data_index;
    }
    destination->meas_data_lst_len = source->meas_data_lst_len;
    destination->meas_info_lst_len = source->meas_info_lst_len;
    destination->meas_record_len = source->meas_record_len;
    destination->incomplete_flag_present = source->incomplete_flag_present;
    destination->incomplete_flag = source->incomplete_flag;
}

static void copy_measurement(
    tcd_kpm_canonical_record_t *destination,
    const tcd_kpm_measurement_record_t *source)
{
    destination->record_kind = TCD_KPM_RECORD_KIND_MEASUREMENT;
    destination->has_meas_info_index = true;
    destination->meas_info_index = source->meas_info_index;
    destination->has_meas_record_index = true;
    destination->meas_record_index = source->meas_record_index;

    if (source->structural_status == TCD_KPM_STATUS_NO_VALUE) {
        destination->structural_status = TCD_KPM_STRUCTURAL_STATUS_NO_VALUE;
    } else {
        destination->structural_status = TCD_KPM_STRUCTURAL_STATUS_OK;
    }

    if (source->descriptor.type == TCD_KPM_DESCRIPTOR_NAME) {
        destination->descriptor_type = TCD_KPM_CANONICAL_DESCRIPTOR_NAME;
        destination->has_measurement_name = true;
        copy_text(
            destination->measurement_name,
            sizeof(destination->measurement_name),
            source->descriptor.measurement_name);
    } else {
        destination->descriptor_type = TCD_KPM_CANONICAL_DESCRIPTOR_ID;
        destination->has_measurement_id = true;
        destination->measurement_id = source->descriptor.measurement_id;
    }

    if (source->value.type == TCD_KPM_VALUE_INTEGER) {
        destination->value_type = TCD_KPM_CANONICAL_VALUE_INTEGER;
        destination->has_integer_value = true;
        destination->integer_value = source->value.data.integer_value;
    } else if (source->value.type == TCD_KPM_VALUE_REAL) {
        destination->value_type = TCD_KPM_CANONICAL_VALUE_REAL;
        destination->has_real_value = true;
        destination->real_value = source->value.data.real_value;
    } else {
        destination->value_type = TCD_KPM_CANONICAL_VALUE_NO_VALUE;
    }
}

static void copy_diagnostic(
    tcd_kpm_canonical_record_t *destination,
    const tcd_kpm_measurement_record_t *source)
{
    destination->record_kind = TCD_KPM_RECORD_KIND_DIAGNOSTIC;
    destination->structural_status = map_diagnostic_status(source);
    destination->descriptor_type = TCD_KPM_CANONICAL_DESCRIPTOR_UNKNOWN;
    destination->value_type = TCD_KPM_CANONICAL_VALUE_UNKNOWN;
    destination->has_diagnostic_code = true;
    copy_text(
        destination->diagnostic_code,
        sizeof(destination->diagnostic_code),
        diagnostic_code(source));
    destination->has_diagnostic_message = true;
    (void)snprintf(
        destination->diagnostic_message,
        sizeof(destination->diagnostic_message),
        "meas_info_lst_len=%u meas_record_len=%u",
        source->meas_info_lst_len,
        source->meas_record_len);
}

bool tcd_kpm_output_adapter_pipeline_create(
    tcd_kpm_output_pipeline_t **pipeline,
    char *error,
    size_t error_capacity)
{
    return tcd_kpm_output_pipeline_create_from_environment(
        pipeline,
        error,
        error_capacity);
}

bool tcd_kpm_output_adapter_submit(
    tcd_kpm_output_pipeline_t *pipeline,
    const tcd_kpm_measurement_record_t *record)
{
    tcd_kpm_canonical_record_t canonical;

    if (pipeline == NULL) {
        return true;
    }
    if (record == NULL) {
        return false;
    }

    tcd_kpm_canonical_record_init(&canonical);
    copy_common(&canonical, record);

    if (record->structural_status == TCD_KPM_STATUS_OK ||
        record->structural_status == TCD_KPM_STATUS_NO_VALUE) {
        copy_measurement(&canonical, record);
    } else {
        copy_diagnostic(&canonical, record);
    }

    return tcd_kpm_output_pipeline_try_submit(pipeline, &canonical);
}

bool tcd_kpm_output_adapter_pipeline_shutdown(
    tcd_kpm_output_pipeline_t **pipeline,
    uint64_t callback_errors,
    uint64_t subscriptions_created,
    uint64_t subscriptions_removed)
{
    if (pipeline == NULL) {
        return false;
    }

    tcd_kpm_output_pipeline_set_runtime_counters(
        *pipeline,
        callback_errors,
        subscriptions_created,
        subscriptions_removed);
    return tcd_kpm_output_pipeline_shutdown_and_destroy(pipeline);
}
