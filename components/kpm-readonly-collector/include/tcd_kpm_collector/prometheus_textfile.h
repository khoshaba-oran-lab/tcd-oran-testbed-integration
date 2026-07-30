#ifndef TCD_KPM_COLLECTOR_PROMETHEUS_TEXTFILE_H
#define TCD_KPM_COLLECTOR_PROMETHEUS_TEXTFILE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TCD_KPM_PROMETHEUS_MAX_SNAPSHOT_BYTES 32768U
#define TCD_KPM_PROMETHEUS_MAX_PATH_BYTES 4096U

typedef enum {
    TCD_KPM_OUTPUT_BACKEND_CSV = 0,
    TCD_KPM_OUTPUT_BACKEND_JSONL = 1,
    TCD_KPM_OUTPUT_BACKEND_PROMETHEUS = 2,
    TCD_KPM_OUTPUT_BACKEND_PARQUET = 3,
    TCD_KPM_OUTPUT_BACKEND_COUNT = 4
} tcd_kpm_output_backend_t;

typedef enum {
    TCD_KPM_OUTPUT_ERROR_OPEN = 0,
    TCD_KPM_OUTPUT_ERROR_WRITE = 1,
    TCD_KPM_OUTPUT_ERROR_FLUSH = 2,
    TCD_KPM_OUTPUT_ERROR_CLOSE = 3,
    TCD_KPM_OUTPUT_ERROR_RENAME = 4,
    TCD_KPM_OUTPUT_ERROR_COUNT = 5
} tcd_kpm_output_error_reason_t;

typedef struct {
    uint64_t indications_format_1_total;
    uint64_t indications_format_3_total;

    uint64_t records_measurement_integer_total;
    uint64_t records_measurement_real_total;
    uint64_t records_measurement_no_value_total;
    uint64_t records_diagnostic_length_mismatch_total;
    uint64_t records_diagnostic_invalid_input_total;

    uint64_t rejected_rows_length_mismatch_total;
    uint64_t rejected_rows_invalid_input_total;
    uint64_t callback_errors_total;
    uint64_t subscriptions_created_total;
    uint64_t subscriptions_removed_total;

    uint64_t output_records_ok[TCD_KPM_OUTPUT_BACKEND_COUNT];
    uint64_t output_records_error[TCD_KPM_OUTPUT_BACKEND_COUNT];
    uint64_t output_errors[TCD_KPM_OUTPUT_BACKEND_COUNT]
                          [TCD_KPM_OUTPUT_ERROR_COUNT];

    uint64_t output_queue_depth;
    uint64_t last_receive_timestamp_seconds;
    uint64_t snapshot_timestamp_seconds;
} tcd_kpm_prometheus_snapshot_t;

typedef enum {
    TCD_KPM_PROMETHEUS_OK = 0,
    TCD_KPM_PROMETHEUS_INVALID_ARGUMENT = 1,
    TCD_KPM_PROMETHEUS_BUFFER_TOO_SMALL = 2,
    TCD_KPM_PROMETHEUS_PATH_TOO_LONG = 3,
    TCD_KPM_PROMETHEUS_OPEN_FAILED = 4,
    TCD_KPM_PROMETHEUS_WRITE_FAILED = 5,
    TCD_KPM_PROMETHEUS_FLUSH_FAILED = 6,
    TCD_KPM_PROMETHEUS_CLOSE_FAILED = 7,
    TCD_KPM_PROMETHEUS_RENAME_FAILED = 8
} tcd_kpm_prometheus_status_t;

typedef struct {
    tcd_kpm_prometheus_status_t status;
    tcd_kpm_output_error_reason_t error_reason;
    int system_errno;
    size_t bytes_written;
} tcd_kpm_prometheus_write_result_t;

const char *tcd_kpm_prometheus_status_name(
    tcd_kpm_prometheus_status_t status);

const char *tcd_kpm_output_backend_name(
    tcd_kpm_output_backend_t backend);

const char *tcd_kpm_output_error_reason_name(
    tcd_kpm_output_error_reason_t reason);

tcd_kpm_prometheus_status_t tcd_kpm_prometheus_serialize(
    const tcd_kpm_prometheus_snapshot_t *snapshot,
    char *output,
    size_t output_capacity,
    size_t *required_length);

tcd_kpm_prometheus_status_t tcd_kpm_prometheus_write_atomic(
    const char *target_path,
    const tcd_kpm_prometheus_snapshot_t *snapshot,
    tcd_kpm_prometheus_write_result_t *result);

#ifdef __cplusplus
}
#endif

#endif
