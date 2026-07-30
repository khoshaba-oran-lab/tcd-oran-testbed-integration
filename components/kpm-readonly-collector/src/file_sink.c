#include "tcd_kpm_collector/file_sink.h"

#include "tcd_kpm_collector/canonical_serialize.h"

#include <stddef.h>
#include <string.h>

static bool valid_format(tcd_kpm_file_sink_format_t format)
{
    return format == TCD_KPM_FILE_SINK_FORMAT_CSV ||
           format == TCD_KPM_FILE_SINK_FORMAT_JSONL;
}

static bool copy_path(char *destination, size_t capacity, const char *source)
{
    size_t length = 0U;

    if (destination == NULL || capacity == 0U || source == NULL) {
        return false;
    }

    while (length < capacity && source[length] != '\0') {
        ++length;
    }
    if (length == 0U || length == capacity) {
        return false;
    }

    memcpy(destination, source, length + 1U);
    return true;
}

static void mark_failure(tcd_kpm_file_sink_t *sink)
{
    sink->failed = true;
    ++sink->errors;
}

static tcd_kpm_file_sink_result_t write_and_flush(
    tcd_kpm_file_sink_t *sink,
    const char *data,
    size_t length)
{
    size_t written = 0U;

    written = fwrite(data, 1U, length, sink->stream);
    if (written != length) {
        mark_failure(sink);
        return TCD_KPM_FILE_SINK_WRITE_FAILED;
    }
    if (fflush(sink->stream) != 0) {
        mark_failure(sink);
        return TCD_KPM_FILE_SINK_FLUSH_FAILED;
    }

    return TCD_KPM_FILE_SINK_OK;
}

void tcd_kpm_file_sink_init(tcd_kpm_file_sink_t *sink)
{
    if (sink == NULL) {
        return;
    }

    memset(sink, 0, sizeof(*sink));
    sink->format = TCD_KPM_FILE_SINK_FORMAT_INVALID;
}

const char *tcd_kpm_file_sink_result_name(
    tcd_kpm_file_sink_result_t result)
{
    switch (result) {
    case TCD_KPM_FILE_SINK_OK:
        return "ok";
    case TCD_KPM_FILE_SINK_INVALID_ARGUMENT:
        return "invalid_argument";
    case TCD_KPM_FILE_SINK_ALREADY_OPEN:
        return "already_open";
    case TCD_KPM_FILE_SINK_OPEN_FAILED:
        return "open_failed";
    case TCD_KPM_FILE_SINK_SERIALIZE_FAILED:
        return "serialize_failed";
    case TCD_KPM_FILE_SINK_WRITE_FAILED:
        return "write_failed";
    case TCD_KPM_FILE_SINK_FLUSH_FAILED:
        return "flush_failed";
    case TCD_KPM_FILE_SINK_CLOSE_FAILED:
        return "close_failed";
    case TCD_KPM_FILE_SINK_FAILED:
        return "sink_failed";
    default:
        return "unknown";
    }
}

const char *tcd_kpm_file_sink_format_name(
    tcd_kpm_file_sink_format_t format)
{
    switch (format) {
    case TCD_KPM_FILE_SINK_FORMAT_CSV:
        return "csv";
    case TCD_KPM_FILE_SINK_FORMAT_JSONL:
        return "jsonl";
    default:
        return "invalid";
    }
}

tcd_kpm_file_sink_result_t tcd_kpm_file_sink_open(
    tcd_kpm_file_sink_t *sink,
    tcd_kpm_file_sink_format_t format,
    const char *path)
{
    char header[TCD_KPM_SERIALIZED_RECORD_CAPACITY];
    size_t header_length = 0U;
    tcd_kpm_serialize_result_t serialize_result;
    tcd_kpm_file_sink_result_t write_result;

    if (sink == NULL || path == NULL || !valid_format(format)) {
        return TCD_KPM_FILE_SINK_INVALID_ARGUMENT;
    }
    if (sink->is_open || sink->stream != NULL) {
        return TCD_KPM_FILE_SINK_ALREADY_OPEN;
    }

    tcd_kpm_file_sink_init(sink);
    if (!copy_path(sink->path, sizeof(sink->path), path)) {
        return TCD_KPM_FILE_SINK_INVALID_ARGUMENT;
    }

    sink->format = format;
    sink->stream = fopen(path, "wb");
    if (sink->stream == NULL) {
        sink->format = TCD_KPM_FILE_SINK_FORMAT_INVALID;
        sink->path[0] = '\0';
        ++sink->errors;
        return TCD_KPM_FILE_SINK_OPEN_FAILED;
    }
    sink->is_open = true;

    if (format == TCD_KPM_FILE_SINK_FORMAT_CSV) {
        serialize_result = tcd_kpm_serialize_csv_header(
            header,
            sizeof(header),
            &header_length);
        if (serialize_result != TCD_KPM_SERIALIZE_OK) {
            mark_failure(sink);
            (void)fclose(sink->stream);
            sink->stream = NULL;
            sink->is_open = false;
            return TCD_KPM_FILE_SINK_SERIALIZE_FAILED;
        }

        write_result = write_and_flush(sink, header, header_length);
        if (write_result != TCD_KPM_FILE_SINK_OK) {
            (void)fclose(sink->stream);
            sink->stream = NULL;
            sink->is_open = false;
            return write_result;
        }
    }

    return TCD_KPM_FILE_SINK_OK;
}

tcd_kpm_file_sink_result_t tcd_kpm_file_sink_write(
    tcd_kpm_file_sink_t *sink,
    const tcd_kpm_canonical_record_t *record)
{
    char serialized[TCD_KPM_SERIALIZED_RECORD_CAPACITY];
    size_t serialized_length = 0U;
    tcd_kpm_serialize_result_t serialize_result;
    tcd_kpm_file_sink_result_t write_result;

    if (sink == NULL || record == NULL) {
        return TCD_KPM_FILE_SINK_INVALID_ARGUMENT;
    }
    if (!sink->is_open || sink->stream == NULL || !valid_format(sink->format)) {
        return TCD_KPM_FILE_SINK_INVALID_ARGUMENT;
    }
    if (sink->failed) {
        return TCD_KPM_FILE_SINK_FAILED;
    }

    if (sink->format == TCD_KPM_FILE_SINK_FORMAT_CSV) {
        serialize_result = tcd_kpm_serialize_csv_record(
            record,
            serialized,
            sizeof(serialized),
            &serialized_length);
    } else {
        serialize_result = tcd_kpm_serialize_jsonl_record(
            record,
            serialized,
            sizeof(serialized),
            &serialized_length);
    }

    if (serialize_result != TCD_KPM_SERIALIZE_OK) {
        mark_failure(sink);
        return TCD_KPM_FILE_SINK_SERIALIZE_FAILED;
    }

    write_result = write_and_flush(sink, serialized, serialized_length);
    if (write_result != TCD_KPM_FILE_SINK_OK) {
        return write_result;
    }

    ++sink->records_written;
    return TCD_KPM_FILE_SINK_OK;
}

tcd_kpm_file_sink_result_t tcd_kpm_file_sink_close(
    tcd_kpm_file_sink_t *sink)
{
    bool failed_before_close;
    int flush_result;
    int close_result;

    if (sink == NULL || !sink->is_open || sink->stream == NULL) {
        return TCD_KPM_FILE_SINK_INVALID_ARGUMENT;
    }

    failed_before_close = sink->failed;
    flush_result = fflush(sink->stream);
    close_result = fclose(sink->stream);
    sink->stream = NULL;
    sink->is_open = false;

    if (flush_result != 0) {
        if (!sink->failed) {
            mark_failure(sink);
        }
        return TCD_KPM_FILE_SINK_FLUSH_FAILED;
    }
    if (close_result != 0) {
        if (!sink->failed) {
            mark_failure(sink);
        }
        return TCD_KPM_FILE_SINK_CLOSE_FAILED;
    }
    if (failed_before_close) {
        return TCD_KPM_FILE_SINK_FAILED;
    }

    return TCD_KPM_FILE_SINK_OK;
}
