#define _POSIX_C_SOURCE 200809L

#include "tcd_kpm_collector/prometheus_textfile.h"

#include <errno.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define TCD_KPM_PROMETHEUS_SCHEMA_VERSION "tcd.kpm.record.emulator-draft-0.1"
#define TCD_KPM_PROMETHEUS_COLLECTOR_STAGE "collector-03-sw-prototype"

typedef struct {
    char *output;
    size_t capacity;
    size_t length;
    int failed;
} text_writer_t;

static void writer_appendf(text_writer_t *writer, const char *format, ...)
{
    va_list args;
    va_list copy;
    int needed;

    if (writer == NULL || format == NULL || writer->failed != 0) {
        return;
    }

    va_start(args, format);
    va_copy(copy, args);
    needed = vsnprintf(NULL, 0, format, copy);
    va_end(copy);

    if (needed < 0) {
        writer->failed = 1;
        va_end(args);
        return;
    }

    if ((size_t)needed > SIZE_MAX - writer->length) {
        writer->failed = 1;
        va_end(args);
        return;
    }

    if (writer->output != NULL && writer->capacity > writer->length) {
        const size_t available = writer->capacity - writer->length;
        (void)vsnprintf(writer->output + writer->length, available, format, args);
    }
    va_end(args);

    writer->length += (size_t)needed;
}

static void append_family_header(
    text_writer_t *writer,
    const char *name,
    const char *help,
    const char *type)
{
    writer_appendf(writer, "# HELP %s %s\n", name, help);
    writer_appendf(writer, "# TYPE %s %s\n", name, type);
}

static void append_backend_metrics(
    text_writer_t *writer,
    const tcd_kpm_prometheus_snapshot_t *snapshot)
{
    size_t backend;
    size_t reason;

    append_family_header(
        writer,
        "tcd_kpm_collector_output_records_total",
        "Output records attempted by backend and result.",
        "counter");

    for (backend = 0U; backend < TCD_KPM_OUTPUT_BACKEND_COUNT; ++backend) {
        writer_appendf(
            writer,
            "tcd_kpm_collector_output_records_total{backend=\"%s\",result=\"ok\"} %" PRIu64 "\n",
            tcd_kpm_output_backend_name((tcd_kpm_output_backend_t)backend),
            snapshot->output_records_ok[backend]);
        writer_appendf(
            writer,
            "tcd_kpm_collector_output_records_total{backend=\"%s\",result=\"error\"} %" PRIu64 "\n",
            tcd_kpm_output_backend_name((tcd_kpm_output_backend_t)backend),
            snapshot->output_records_error[backend]);
    }

    append_family_header(
        writer,
        "tcd_kpm_collector_output_errors_total",
        "Output backend failures by bounded reason token.",
        "counter");

    for (backend = 0U; backend < TCD_KPM_OUTPUT_BACKEND_COUNT; ++backend) {
        for (reason = 0U; reason < TCD_KPM_OUTPUT_ERROR_COUNT; ++reason) {
            writer_appendf(
                writer,
                "tcd_kpm_collector_output_errors_total{backend=\"%s\",reason=\"%s\"} %" PRIu64 "\n",
                tcd_kpm_output_backend_name(
                    (tcd_kpm_output_backend_t)backend),
                tcd_kpm_output_error_reason_name(
                    (tcd_kpm_output_error_reason_t)reason),
                snapshot->output_errors[backend][reason]);
        }
    }
}

const char *tcd_kpm_prometheus_status_name(
    tcd_kpm_prometheus_status_t status)
{
    switch (status) {
    case TCD_KPM_PROMETHEUS_OK:
        return "ok";
    case TCD_KPM_PROMETHEUS_INVALID_ARGUMENT:
        return "invalid_argument";
    case TCD_KPM_PROMETHEUS_BUFFER_TOO_SMALL:
        return "buffer_too_small";
    case TCD_KPM_PROMETHEUS_PATH_TOO_LONG:
        return "path_too_long";
    case TCD_KPM_PROMETHEUS_OPEN_FAILED:
        return "open_failed";
    case TCD_KPM_PROMETHEUS_WRITE_FAILED:
        return "write_failed";
    case TCD_KPM_PROMETHEUS_FLUSH_FAILED:
        return "flush_failed";
    case TCD_KPM_PROMETHEUS_CLOSE_FAILED:
        return "close_failed";
    case TCD_KPM_PROMETHEUS_RENAME_FAILED:
        return "rename_failed";
    default:
        return "unknown";
    }
}

const char *tcd_kpm_output_backend_name(
    tcd_kpm_output_backend_t backend)
{
    static const char *const names[TCD_KPM_OUTPUT_BACKEND_COUNT] = {
        "csv",
        "jsonl",
        "prometheus",
        "parquet",
    };

    if ((size_t)backend >= TCD_KPM_OUTPUT_BACKEND_COUNT) {
        return "unknown";
    }
    return names[backend];
}

const char *tcd_kpm_output_error_reason_name(
    tcd_kpm_output_error_reason_t reason)
{
    static const char *const names[TCD_KPM_OUTPUT_ERROR_COUNT] = {
        "open",
        "write",
        "flush",
        "close",
        "rename",
    };

    if ((size_t)reason >= TCD_KPM_OUTPUT_ERROR_COUNT) {
        return "unknown";
    }
    return names[reason];
}

tcd_kpm_prometheus_status_t tcd_kpm_prometheus_serialize(
    const tcd_kpm_prometheus_snapshot_t *snapshot,
    char *output,
    size_t output_capacity,
    size_t *required_length)
{
    text_writer_t writer;

    if (snapshot == NULL || required_length == NULL) {
        return TCD_KPM_PROMETHEUS_INVALID_ARGUMENT;
    }
    if (output == NULL && output_capacity != 0U) {
        return TCD_KPM_PROMETHEUS_INVALID_ARGUMENT;
    }

    writer.output = output;
    writer.capacity = output_capacity;
    writer.length = 0U;
    writer.failed = 0;

    append_family_header(
        &writer,
        "tcd_kpm_collector_build_info",
        "Static build and schema identity.",
        "gauge");
    writer_appendf(
        &writer,
        "tcd_kpm_collector_build_info{schema_version=\"%s\",collector_stage=\"%s\"} 1\n",
        TCD_KPM_PROMETHEUS_SCHEMA_VERSION,
        TCD_KPM_PROMETHEUS_COLLECTOR_STAGE);

    append_family_header(
        &writer,
        "tcd_kpm_collector_indications_total",
        "Accepted KPM indications observed by the collector.",
        "counter");
    writer_appendf(
        &writer,
        "tcd_kpm_collector_indications_total{message_format=\"1\"} %" PRIu64 "\n",
        snapshot->indications_format_1_total);
    writer_appendf(
        &writer,
        "tcd_kpm_collector_indications_total{message_format=\"3\"} %" PRIu64 "\n",
        snapshot->indications_format_3_total);

    append_family_header(
        &writer,
        "tcd_kpm_collector_records_total",
        "Canonical records produced by classification.",
        "counter");
    writer_appendf(
        &writer,
        "tcd_kpm_collector_records_total{record_kind=\"measurement\",structural_status=\"ok\",value_type=\"integer\"} %" PRIu64 "\n",
        snapshot->records_measurement_integer_total);
    writer_appendf(
        &writer,
        "tcd_kpm_collector_records_total{record_kind=\"measurement\",structural_status=\"ok\",value_type=\"real\"} %" PRIu64 "\n",
        snapshot->records_measurement_real_total);
    writer_appendf(
        &writer,
        "tcd_kpm_collector_records_total{record_kind=\"measurement\",structural_status=\"no_value\",value_type=\"no_value\"} %" PRIu64 "\n",
        snapshot->records_measurement_no_value_total);
    writer_appendf(
        &writer,
        "tcd_kpm_collector_records_total{record_kind=\"diagnostic\",structural_status=\"length_mismatch\",value_type=\"unknown\"} %" PRIu64 "\n",
        snapshot->records_diagnostic_length_mismatch_total);
    writer_appendf(
        &writer,
        "tcd_kpm_collector_records_total{record_kind=\"diagnostic\",structural_status=\"invalid_input\",value_type=\"unknown\"} %" PRIu64 "\n",
        snapshot->records_diagnostic_invalid_input_total);

    append_family_header(
        &writer,
        "tcd_kpm_collector_rejected_rows_total",
        "Rows rejected before metadata and value pairing.",
        "counter");
    writer_appendf(
        &writer,
        "tcd_kpm_collector_rejected_rows_total{reason=\"length_mismatch\"} %" PRIu64 "\n",
        snapshot->rejected_rows_length_mismatch_total);
    writer_appendf(
        &writer,
        "tcd_kpm_collector_rejected_rows_total{reason=\"invalid_input\"} %" PRIu64 "\n",
        snapshot->rejected_rows_invalid_input_total);

    append_family_header(
        &writer,
        "tcd_kpm_collector_callback_errors_total",
        "Callback-level internal errors.",
        "counter");
    writer_appendf(
        &writer,
        "tcd_kpm_collector_callback_errors_total %" PRIu64 "\n",
        snapshot->callback_errors_total);

    append_family_header(
        &writer,
        "tcd_kpm_collector_subscriptions_created_total",
        "Successful KPM subscriptions created.",
        "counter");
    writer_appendf(
        &writer,
        "tcd_kpm_collector_subscriptions_created_total %" PRIu64 "\n",
        snapshot->subscriptions_created_total);

    append_family_header(
        &writer,
        "tcd_kpm_collector_subscriptions_removed_total",
        "Successful KPM subscriptions removed.",
        "counter");
    writer_appendf(
        &writer,
        "tcd_kpm_collector_subscriptions_removed_total %" PRIu64 "\n",
        snapshot->subscriptions_removed_total);

    append_backend_metrics(&writer, snapshot);

    append_family_header(
        &writer,
        "tcd_kpm_collector_output_queue_depth",
        "Current bounded output queue depth.",
        "gauge");
    writer_appendf(
        &writer,
        "tcd_kpm_collector_output_queue_depth %" PRIu64 "\n",
        snapshot->output_queue_depth);

    append_family_header(
        &writer,
        "tcd_kpm_collector_last_receive_timestamp_seconds",
        "Unix timestamp of the most recent indication.",
        "gauge");
    writer_appendf(
        &writer,
        "tcd_kpm_collector_last_receive_timestamp_seconds %" PRIu64 "\n",
        snapshot->last_receive_timestamp_seconds);

    append_family_header(
        &writer,
        "tcd_kpm_collector_prometheus_snapshot_timestamp_seconds",
        "Unix timestamp of the current textfile snapshot.",
        "gauge");
    writer_appendf(
        &writer,
        "tcd_kpm_collector_prometheus_snapshot_timestamp_seconds %" PRIu64 "\n",
        snapshot->snapshot_timestamp_seconds);

    if (writer.failed != 0) {
        return TCD_KPM_PROMETHEUS_INVALID_ARGUMENT;
    }

    *required_length = writer.length;

    if (output == NULL) {
        return TCD_KPM_PROMETHEUS_OK;
    }
    if (output_capacity <= writer.length) {
        if (output_capacity > 0U) {
            output[output_capacity - 1U] = '\0';
        }
        return TCD_KPM_PROMETHEUS_BUFFER_TOO_SMALL;
    }

    output[writer.length] = '\0';
    return TCD_KPM_PROMETHEUS_OK;
}

static void initialise_result(tcd_kpm_prometheus_write_result_t *result)
{
    if (result != NULL) {
        result->status = TCD_KPM_PROMETHEUS_OK;
        result->error_reason = TCD_KPM_OUTPUT_ERROR_OPEN;
        result->system_errno = 0;
        result->bytes_written = 0U;
    }
}

static tcd_kpm_prometheus_status_t set_failure(
    tcd_kpm_prometheus_write_result_t *result,
    tcd_kpm_prometheus_status_t status,
    tcd_kpm_output_error_reason_t reason,
    int system_errno,
    size_t bytes_written)
{
    if (result != NULL) {
        result->status = status;
        result->error_reason = reason;
        result->system_errno = system_errno;
        result->bytes_written = bytes_written;
    }
    return status;
}

tcd_kpm_prometheus_status_t tcd_kpm_prometheus_write_atomic(
    const char *target_path,
    const tcd_kpm_prometheus_snapshot_t *snapshot,
    tcd_kpm_prometheus_write_result_t *result)
{
    char snapshot_buffer[TCD_KPM_PROMETHEUS_MAX_SNAPSHOT_BYTES];
    char temporary_path[TCD_KPM_PROMETHEUS_MAX_PATH_BYTES];
    size_t required_length = 0U;
    size_t path_length;
    size_t written;
    FILE *stream;
    int saved_errno;
    int descriptor;
    tcd_kpm_prometheus_status_t status;

    initialise_result(result);

    if (target_path == NULL || target_path[0] == '\0' || snapshot == NULL) {
        return set_failure(
            result,
            TCD_KPM_PROMETHEUS_INVALID_ARGUMENT,
            TCD_KPM_OUTPUT_ERROR_OPEN,
            EINVAL,
            0U);
    }

    status = tcd_kpm_prometheus_serialize(
        snapshot,
        snapshot_buffer,
        sizeof(snapshot_buffer),
        &required_length);
    if (status != TCD_KPM_PROMETHEUS_OK) {
        return set_failure(
            result,
            status,
            TCD_KPM_OUTPUT_ERROR_WRITE,
            EINVAL,
            0U);
    }

    path_length = strlen(target_path);
    if (path_length + sizeof(".tmp") > sizeof(temporary_path)) {
        return set_failure(
            result,
            TCD_KPM_PROMETHEUS_PATH_TOO_LONG,
            TCD_KPM_OUTPUT_ERROR_OPEN,
            ENAMETOOLONG,
            0U);
    }

    (void)snprintf(
        temporary_path,
        sizeof(temporary_path),
        "%s.tmp",
        target_path);

    stream = fopen(temporary_path, "wb");
    if (stream == NULL) {
        return set_failure(
            result,
            TCD_KPM_PROMETHEUS_OPEN_FAILED,
            TCD_KPM_OUTPUT_ERROR_OPEN,
            errno,
            0U);
    }

    written = fwrite(snapshot_buffer, 1U, required_length, stream);
    if (written != required_length) {
        saved_errno = errno != 0 ? errno : EIO;
        (void)fclose(stream);
        (void)remove(temporary_path);
        return set_failure(
            result,
            TCD_KPM_PROMETHEUS_WRITE_FAILED,
            TCD_KPM_OUTPUT_ERROR_WRITE,
            saved_errno,
            written);
    }

    if (fflush(stream) != 0) {
        saved_errno = errno != 0 ? errno : EIO;
        (void)fclose(stream);
        (void)remove(temporary_path);
        return set_failure(
            result,
            TCD_KPM_PROMETHEUS_FLUSH_FAILED,
            TCD_KPM_OUTPUT_ERROR_FLUSH,
            saved_errno,
            written);
    }

    descriptor = fileno(stream);
    if (descriptor < 0 || fsync(descriptor) != 0) {
        saved_errno = errno != 0 ? errno : EIO;
        (void)fclose(stream);
        (void)remove(temporary_path);
        return set_failure(
            result,
            TCD_KPM_PROMETHEUS_FLUSH_FAILED,
            TCD_KPM_OUTPUT_ERROR_FLUSH,
            saved_errno,
            written);
    }

    if (fclose(stream) != 0) {
        saved_errno = errno != 0 ? errno : EIO;
        (void)remove(temporary_path);
        return set_failure(
            result,
            TCD_KPM_PROMETHEUS_CLOSE_FAILED,
            TCD_KPM_OUTPUT_ERROR_CLOSE,
            saved_errno,
            written);
    }

    if (rename(temporary_path, target_path) != 0) {
        saved_errno = errno != 0 ? errno : EIO;
        (void)remove(temporary_path);
        return set_failure(
            result,
            TCD_KPM_PROMETHEUS_RENAME_FAILED,
            TCD_KPM_OUTPUT_ERROR_RENAME,
            saved_errno,
            written);
    }

    if (result != NULL) {
        result->status = TCD_KPM_PROMETHEUS_OK;
        result->error_reason = TCD_KPM_OUTPUT_ERROR_OPEN;
        result->system_errno = 0;
        result->bytes_written = written;
    }
    return TCD_KPM_PROMETHEUS_OK;
}
