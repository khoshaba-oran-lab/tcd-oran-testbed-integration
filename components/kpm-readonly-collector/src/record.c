#include "tcd_kpm_collector/record.h"

#include <stdint.h>
#include <string.h>

void tcd_kpm_measurement_record_reset(
    tcd_kpm_measurement_record_t *record
)
{
    if (record == NULL) {
        return;
    }

    memset(record, 0, sizeof(*record));

    record->ue_report_index = UINT32_MAX;
    record->meas_data_index = UINT32_MAX;
    record->meas_record_index = UINT32_MAX;
    record->meas_info_index = UINT32_MAX;
    record->ue_id.type = TCD_KPM_UE_ID_UNKNOWN;
    record->descriptor.type = TCD_KPM_DESCRIPTOR_UNKNOWN;
    record->value.type = TCD_KPM_VALUE_UNKNOWN;
    record->structural_status = TCD_KPM_STATUS_INVALID_INPUT;
}

const char *tcd_kpm_structural_status_string(
    tcd_kpm_structural_status_t status
)
{
    switch (status) {
    case TCD_KPM_STATUS_OK:
        return "ok";
    case TCD_KPM_STATUS_LENGTH_MISMATCH:
        return "length_mismatch";
    case TCD_KPM_STATUS_NO_VALUE:
        return "no_value";
    case TCD_KPM_STATUS_UNSUPPORTED_DESCRIPTOR:
        return "unsupported_descriptor";
    case TCD_KPM_STATUS_UNSUPPORTED_VALUE_TYPE:
        return "unsupported_value_type";
    case TCD_KPM_STATUS_UNSUPPORTED_UE_ID:
        return "unsupported_ue_id";
    case TCD_KPM_STATUS_UNKNOWN_MESSAGE_FORMAT:
        return "unknown_message_format";
    case TCD_KPM_STATUS_INVALID_INPUT:
        return "invalid_input";
    }

    return "invalid_status";
}

const char *tcd_kpm_descriptor_type_string(
    tcd_kpm_descriptor_type_t type
)
{
    switch (type) {
    case TCD_KPM_DESCRIPTOR_UNKNOWN:
        return "unknown";
    case TCD_KPM_DESCRIPTOR_NAME:
        return "name";
    case TCD_KPM_DESCRIPTOR_ID:
        return "id";
    }

    return "invalid_descriptor_type";
}

const char *tcd_kpm_value_type_string(
    tcd_kpm_value_type_t type
)
{
    switch (type) {
    case TCD_KPM_VALUE_UNKNOWN:
        return "unknown";
    case TCD_KPM_VALUE_INTEGER:
        return "integer";
    case TCD_KPM_VALUE_REAL:
        return "real";
    case TCD_KPM_VALUE_NO_VALUE:
        return "no_value";
    }

    return "invalid_value_type";
}
