#ifndef TCD_KPM_COLLECTOR_KPM_VALIDATION_H
#define TCD_KPM_COLLECTOR_KPM_VALIDATION_H

#include <stdbool.h>
#include <stddef.h>

typedef enum {
    TCD_KPM_ROW_OK = 0,
    TCD_KPM_ROW_LENGTH_MISMATCH,
    TCD_KPM_ROW_METADATA_UNAVAILABLE,
    TCD_KPM_ROW_INVALID_RECORD_LENGTH,
    TCD_KPM_ROW_INVALID_INPUT
} tcd_kpm_row_validation_status_t;

typedef struct {
    bool metadata_available;
    const void *metadata;
    size_t metadata_len;

    const void *record;
    size_t record_len;

    size_t maximum_supported_length;
} tcd_kpm_row_shape_t;

typedef struct {
    tcd_kpm_row_validation_status_t status;
    size_t normalised_value_count;
    unsigned int diagnostic_count;
    bool process_continues;
    bool row_accepted;
} tcd_kpm_row_validation_result_t;

tcd_kpm_row_validation_result_t tcd_kpm_validate_row_shape(
    const tcd_kpm_row_shape_t *shape
);

const char *tcd_kpm_row_validation_status_name(
    tcd_kpm_row_validation_status_t status
);

#endif
