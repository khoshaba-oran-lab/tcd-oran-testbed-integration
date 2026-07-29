#include "tcd_kpm_collector/kpm_validation.h"

static tcd_kpm_row_validation_result_t accepted(size_t value_count)
{
    const tcd_kpm_row_validation_result_t result = {
        .status = TCD_KPM_ROW_OK,
        .normalised_value_count = value_count,
        .diagnostic_count = 0U,
        .process_continues = true,
        .row_accepted = true,
    };

    return result;
}

static tcd_kpm_row_validation_result_t rejected(
    tcd_kpm_row_validation_status_t status
)
{
    const tcd_kpm_row_validation_result_t result = {
        .status = status,
        .normalised_value_count = 0U,
        .diagnostic_count = 1U,
        .process_continues = true,
        .row_accepted = false,
    };

    return result;
}

tcd_kpm_row_validation_result_t tcd_kpm_validate_row_shape(
    const tcd_kpm_row_shape_t *shape
)
{
    if (shape == NULL || shape->maximum_supported_length == 0U) {
        return rejected(TCD_KPM_ROW_INVALID_INPUT);
    }

    if (
        shape->record_len == 0U ||
        shape->record_len > shape->maximum_supported_length
    ) {
        return rejected(TCD_KPM_ROW_INVALID_RECORD_LENGTH);
    }

    if (shape->record == NULL) {
        return rejected(TCD_KPM_ROW_INVALID_INPUT);
    }

    if (!shape->metadata_available || shape->metadata_len == 0U) {
        return rejected(TCD_KPM_ROW_METADATA_UNAVAILABLE);
    }

    if (
        shape->metadata == NULL ||
        shape->metadata_len > shape->maximum_supported_length
    ) {
        return rejected(TCD_KPM_ROW_INVALID_INPUT);
    }

    if (shape->metadata_len != shape->record_len) {
        return rejected(TCD_KPM_ROW_LENGTH_MISMATCH);
    }

    return accepted(shape->record_len);
}

const char *tcd_kpm_row_validation_status_name(
    tcd_kpm_row_validation_status_t status
)
{
    switch (status) {
    case TCD_KPM_ROW_OK:
        return "ok";
    case TCD_KPM_ROW_LENGTH_MISMATCH:
        return "length_mismatch";
    case TCD_KPM_ROW_METADATA_UNAVAILABLE:
        return "metadata_unavailable";
    case TCD_KPM_ROW_INVALID_RECORD_LENGTH:
        return "invalid_record_length";
    case TCD_KPM_ROW_INVALID_INPUT:
        return "invalid_input";
    }

    return "invalid_input";
}
