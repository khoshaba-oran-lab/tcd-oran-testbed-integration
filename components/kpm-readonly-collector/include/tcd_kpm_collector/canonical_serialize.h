#ifndef TCD_KPM_COLLECTOR_CANONICAL_SERIALIZE_H
#define TCD_KPM_COLLECTOR_CANONICAL_SERIALIZE_H

#include <stddef.h>

#include "tcd_kpm_collector/canonical_record.h"

typedef enum {
    TCD_KPM_SERIALIZE_OK = 0,
    TCD_KPM_SERIALIZE_INVALID_ARGUMENT = 1,
    TCD_KPM_SERIALIZE_INVALID_RECORD = 2,
    TCD_KPM_SERIALIZE_BUFFER_TOO_SMALL = 3
} tcd_kpm_serialize_result_t;

void tcd_kpm_canonical_record_init(tcd_kpm_canonical_record_t *record);

tcd_kpm_serialize_result_t tcd_kpm_canonical_record_validate(
    const tcd_kpm_canonical_record_t *record,
    const char **reason);

const char *tcd_kpm_serialize_result_name(tcd_kpm_serialize_result_t result);

tcd_kpm_serialize_result_t tcd_kpm_serialize_csv_header(
    char *destination,
    size_t destination_capacity,
    size_t *required_length);

tcd_kpm_serialize_result_t tcd_kpm_serialize_csv_record(
    const tcd_kpm_canonical_record_t *record,
    char *destination,
    size_t destination_capacity,
    size_t *required_length);

tcd_kpm_serialize_result_t tcd_kpm_serialize_jsonl_record(
    const tcd_kpm_canonical_record_t *record,
    char *destination,
    size_t destination_capacity,
    size_t *required_length);

#endif
