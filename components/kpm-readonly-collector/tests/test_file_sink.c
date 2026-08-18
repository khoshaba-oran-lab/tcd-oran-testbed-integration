#define _POSIX_C_SOURCE 200809L

#include "tcd_kpm_collector/file_sink.h"
#include "tcd_kpm_collector/canonical_serialize.h"

#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void copy_text(char *destination, size_t capacity, const char *source)
{
    const size_t length = strlen(source);
    assert(length < capacity);
    memcpy(destination, source, length + 1U);
}

static tcd_kpm_canonical_record_t measurement_record(void)
{
    tcd_kpm_canonical_record_t record;
    tcd_kpm_canonical_record_init(&record);

    record.record_kind = TCD_KPM_RECORD_KIND_MEASUREMENT;
    record.indication_sequence = 7U;
    record.receive_timestamp_us = 1700000000123456ULL;
    record.has_kpm_header_timestamp_us = true;
    record.kpm_header_timestamp_us = 1700000000000000ULL;
    record.message_format = 3U;
    record.has_node_type = true;
    copy_text(record.node_type, sizeof(record.node_type), "gnb,du");
    record.has_node_id = true;
    copy_text(record.node_id, sizeof(record.node_id), "node\"A");
    record.has_ue_report_index = true;
    record.ue_report_index = 0U;
    copy_text(record.ue_id_type, sizeof(record.ue_id_type), "gnb_du_ue_id");
    record.has_ue_id_value = true;
    copy_text(record.ue_id_value, sizeof(record.ue_id_value), "ue-1");
    record.has_meas_data_index = true;
    record.meas_data_index = 1U;
    record.has_meas_info_index = true;
    record.meas_info_index = 2U;
    record.has_meas_record_index = true;
    record.meas_record_index = 2U;
    record.meas_data_lst_len = 3U;
    record.meas_info_lst_len = 4U;
    record.meas_record_len = 4U;
    record.incomplete_flag_present = true;
    record.incomplete_flag = false;
    record.structural_status = TCD_KPM_STRUCTURAL_STATUS_OK;
    record.descriptor_type = TCD_KPM_DESCRIPTOR_NAME;
    record.has_measurement_name = true;
    copy_text(
        record.measurement_name,
        sizeof(record.measurement_name),
        "DRB.UEThpDl");
    record.value_type = TCD_KPM_VALUE_INTEGER;
    record.has_integer_value = true;
    record.integer_value = -42;

    return record;
}

static tcd_kpm_canonical_record_t diagnostic_record(void)
{
    tcd_kpm_canonical_record_t record;
    tcd_kpm_canonical_record_init(&record);

    record.record_kind = TCD_KPM_RECORD_KIND_DIAGNOSTIC;
    record.indication_sequence = 8U;
    record.receive_timestamp_us = 1700000001123456ULL;
    record.message_format = 3U;
    copy_text(record.ue_id_type, sizeof(record.ue_id_type), "unknown");
    record.has_meas_data_index = true;
    record.meas_data_index = 0U;
    record.meas_data_lst_len = 1U;
    record.meas_info_lst_len = 2U;
    record.meas_record_len = 4U;
    record.structural_status = TCD_KPM_STRUCTURAL_STATUS_LENGTH_MISMATCH;
    record.descriptor_type = TCD_KPM_DESCRIPTOR_UNKNOWN;
    record.value_type = TCD_KPM_VALUE_UNKNOWN;
    record.has_diagnostic_code = true;
    copy_text(
        record.diagnostic_code,
        sizeof(record.diagnostic_code),
        "length_mismatch");
    record.has_diagnostic_message = true;
    copy_text(
        record.diagnostic_message,
        sizeof(record.diagnostic_message),
        "metadata=2, record=4");

    return record;
}

static char *read_file(const char *path, size_t *length_out)
{
    FILE *stream = fopen(path, "rb");
    long length;
    char *data;

    assert(stream != NULL);
    assert(fseek(stream, 0L, SEEK_END) == 0);
    length = ftell(stream);
    assert(length >= 0L);
    assert(fseek(stream, 0L, SEEK_SET) == 0);

    data = malloc((size_t)length + 1U);
    assert(data != NULL);
    assert(fread(data, 1U, (size_t)length, stream) == (size_t)length);
    data[length] = '\0';
    assert(fclose(stream) == 0);

    if (length_out != NULL) {
        *length_out = (size_t)length;
    }
    return data;
}

static size_t count_byte(const char *data, size_t length, char value)
{
    size_t count = 0U;
    size_t index;

    for (index = 0U; index < length; ++index) {
        if (data[index] == value) {
            ++count;
        }
    }
    return count;
}

static void make_path(
    char *destination,
    size_t capacity,
    const char *directory,
    const char *name)
{
    const int result = snprintf(destination, capacity, "%s/%s", directory, name);
    assert(result > 0);
    assert((size_t)result < capacity);
}

static void test_csv_sink(const char *directory)
{
    char path[512];
    tcd_kpm_file_sink_t sink;
    tcd_kpm_canonical_record_t measurement = measurement_record();
    tcd_kpm_canonical_record_t diagnostic = diagnostic_record();
    char *data;
    size_t length;

    make_path(path, sizeof(path), directory, "records.csv");
    tcd_kpm_file_sink_init(&sink);

    assert(tcd_kpm_file_sink_open(
        &sink,
        TCD_KPM_FILE_SINK_FORMAT_CSV,
        path) == TCD_KPM_FILE_SINK_OK);
    assert(sink.is_open);
    assert(!sink.failed);
    assert(sink.records_written == 0U);
    assert(tcd_kpm_file_sink_write(&sink, &measurement) ==
           TCD_KPM_FILE_SINK_OK);
    assert(tcd_kpm_file_sink_write(&sink, &diagnostic) ==
           TCD_KPM_FILE_SINK_OK);
    assert(sink.records_written == 2U);
    assert(sink.errors == 0U);
    assert(tcd_kpm_file_sink_close(&sink) == TCD_KPM_FILE_SINK_OK);

    data = read_file(path, &length);
    assert(count_byte(data, length, '\n') == 3U);
    assert(strncmp(data, "schema_version,record_kind,", 27U) == 0);
    assert(strstr(data, "\"tcd.kpm.record.emulator-draft-0.1\",\"measurement\",") != NULL);
    assert(strstr(data, "\"tcd.kpm.record.emulator-draft-0.1\",\"diagnostic\",") != NULL);
    assert(strstr(data, "\"gnb,du\"") != NULL);
    assert(strstr(data, "length_mismatch") != NULL);
    free(data);

    printf("TEST csv_sink PASS\n");
}

static void test_jsonl_sink(const char *directory)
{
    char path[512];
    tcd_kpm_file_sink_t sink;
    tcd_kpm_canonical_record_t measurement = measurement_record();
    tcd_kpm_canonical_record_t diagnostic = diagnostic_record();
    char *data;
    size_t length;

    make_path(path, sizeof(path), directory, "records.jsonl");
    tcd_kpm_file_sink_init(&sink);

    assert(tcd_kpm_file_sink_open(
        &sink,
        TCD_KPM_FILE_SINK_FORMAT_JSONL,
        path) == TCD_KPM_FILE_SINK_OK);
    assert(tcd_kpm_file_sink_write(&sink, &measurement) ==
           TCD_KPM_FILE_SINK_OK);
    assert(tcd_kpm_file_sink_write(&sink, &diagnostic) ==
           TCD_KPM_FILE_SINK_OK);
    assert(tcd_kpm_file_sink_close(&sink) == TCD_KPM_FILE_SINK_OK);

    data = read_file(path, &length);
    assert(count_byte(data, length, '\n') == 2U);
    assert(strstr(data, "{\"schema_version\":\"tcd.kpm.record.emulator-draft-0.1\"") == data);
    assert(strstr(data, "\"record_kind\":\"measurement\"") != NULL);
    assert(strstr(data, "\"record_kind\":\"diagnostic\"") != NULL);
    assert(strstr(data, "\"diagnostic_code\":\"length_mismatch\"") != NULL);
    free(data);

    printf("TEST jsonl_sink PASS\n");
}

static void test_invalid_record_no_partial_write(const char *directory)
{
    char path[512];
    tcd_kpm_file_sink_t sink;
    tcd_kpm_canonical_record_t record = measurement_record();
    struct stat before;
    struct stat after;

    make_path(path, sizeof(path), directory, "invalid.jsonl");
    tcd_kpm_file_sink_init(&sink);
    assert(tcd_kpm_file_sink_open(
        &sink,
        TCD_KPM_FILE_SINK_FORMAT_JSONL,
        path) == TCD_KPM_FILE_SINK_OK);
    assert(stat(path, &before) == 0);

    record.has_meas_record_index = false;
    assert(tcd_kpm_file_sink_write(&sink, &record) ==
           TCD_KPM_FILE_SINK_SERIALIZE_FAILED);
    assert(sink.failed);
    assert(sink.records_written == 0U);
    assert(sink.errors == 1U);
    assert(tcd_kpm_file_sink_write(&sink, &record) ==
           TCD_KPM_FILE_SINK_FAILED);
    assert(stat(path, &after) == 0);
    assert(after.st_size == before.st_size);
    assert(tcd_kpm_file_sink_close(&sink) == TCD_KPM_FILE_SINK_FAILED);

    printf("TEST invalid_record_no_partial_write PASS\n");
}

static void test_open_and_state_errors(const char *directory)
{
    char path[512];
    tcd_kpm_file_sink_t sink;
    tcd_kpm_canonical_record_t record = measurement_record();

    make_path(path, sizeof(path), directory, "state.jsonl");
    tcd_kpm_file_sink_init(&sink);

    assert(tcd_kpm_file_sink_open(NULL, TCD_KPM_FILE_SINK_FORMAT_JSONL, path) ==
           TCD_KPM_FILE_SINK_INVALID_ARGUMENT);
    assert(tcd_kpm_file_sink_open(
        &sink,
        TCD_KPM_FILE_SINK_FORMAT_INVALID,
        path) == TCD_KPM_FILE_SINK_INVALID_ARGUMENT);
    assert(tcd_kpm_file_sink_open(
        &sink,
        TCD_KPM_FILE_SINK_FORMAT_JSONL,
        directory) == TCD_KPM_FILE_SINK_OPEN_FAILED);
    assert(sink.errors == 1U);

    tcd_kpm_file_sink_init(&sink);
    assert(tcd_kpm_file_sink_open(
        &sink,
        TCD_KPM_FILE_SINK_FORMAT_JSONL,
        path) == TCD_KPM_FILE_SINK_OK);
    assert(tcd_kpm_file_sink_open(
        &sink,
        TCD_KPM_FILE_SINK_FORMAT_JSONL,
        path) == TCD_KPM_FILE_SINK_ALREADY_OPEN);
    assert(tcd_kpm_file_sink_close(&sink) == TCD_KPM_FILE_SINK_OK);
    assert(tcd_kpm_file_sink_write(&sink, &record) ==
           TCD_KPM_FILE_SINK_INVALID_ARGUMENT);
    assert(tcd_kpm_file_sink_close(&sink) ==
           TCD_KPM_FILE_SINK_INVALID_ARGUMENT);
    assert(strcmp(tcd_kpm_file_sink_format_name(
        TCD_KPM_FILE_SINK_FORMAT_CSV), "csv") == 0);
    assert(strcmp(tcd_kpm_file_sink_result_name(
        TCD_KPM_FILE_SINK_FLUSH_FAILED), "flush_failed") == 0);

    printf("TEST open_and_state_errors PASS\n");
}

static void test_dev_full_write_failure(void)
{
    tcd_kpm_file_sink_t sink;
    tcd_kpm_canonical_record_t record = measurement_record();
    tcd_kpm_file_sink_result_t result;

    assert(access("/dev/full", W_OK) == 0);
    tcd_kpm_file_sink_init(&sink);
    assert(tcd_kpm_file_sink_open(
        &sink,
        TCD_KPM_FILE_SINK_FORMAT_JSONL,
        "/dev/full") == TCD_KPM_FILE_SINK_OK);

    result = tcd_kpm_file_sink_write(&sink, &record);
    assert(result == TCD_KPM_FILE_SINK_WRITE_FAILED ||
           result == TCD_KPM_FILE_SINK_FLUSH_FAILED);
    assert(sink.failed);
    assert(sink.records_written == 0U);
    assert(sink.errors == 1U);
    assert(tcd_kpm_file_sink_write(&sink, &record) ==
           TCD_KPM_FILE_SINK_FAILED);
    result = tcd_kpm_file_sink_close(&sink);
    assert(result == TCD_KPM_FILE_SINK_FAILED ||
           result == TCD_KPM_FILE_SINK_FLUSH_FAILED ||
           result == TCD_KPM_FILE_SINK_CLOSE_FAILED);

    printf("TEST dev_full_write_failure PASS\n");
}

static void test_csv_header_failure_dev_full(void)
{
    tcd_kpm_file_sink_t sink;
    tcd_kpm_file_sink_result_t result;

    assert(access("/dev/full", W_OK) == 0);
    tcd_kpm_file_sink_init(&sink);
    result = tcd_kpm_file_sink_open(
        &sink,
        TCD_KPM_FILE_SINK_FORMAT_CSV,
        "/dev/full");
    assert(result == TCD_KPM_FILE_SINK_WRITE_FAILED ||
           result == TCD_KPM_FILE_SINK_FLUSH_FAILED);
    assert(!sink.is_open);
    assert(sink.stream == NULL);
    assert(sink.failed);
    assert(sink.errors == 1U);

    printf("TEST csv_header_failure_dev_full PASS\n");
}

static void fill_control_text(char *destination, size_t capacity)
{
    size_t index;
    assert(capacity > 1U);
    for (index = 0U; index + 1U < capacity; ++index) {
        destination[index] = (char)((index % 31U) + 1U);
    }
    destination[capacity - 1U] = '\0';
}

static void test_maximum_escaped_record(const char *directory)
{
    char path[512];
    tcd_kpm_file_sink_t sink;
    tcd_kpm_canonical_record_t record = measurement_record();
    char *data;
    size_t length;

    make_path(path, sizeof(path), directory, "maximum.jsonl");
    fill_control_text(record.node_type, sizeof(record.node_type));
    fill_control_text(record.node_id, sizeof(record.node_id));
    fill_control_text(record.ue_id_type, sizeof(record.ue_id_type));
    fill_control_text(record.ue_id_value, sizeof(record.ue_id_value));
    fill_control_text(record.measurement_name, sizeof(record.measurement_name));

    tcd_kpm_file_sink_init(&sink);
    assert(tcd_kpm_file_sink_open(
        &sink,
        TCD_KPM_FILE_SINK_FORMAT_JSONL,
        path) == TCD_KPM_FILE_SINK_OK);
    assert(tcd_kpm_file_sink_write(&sink, &record) ==
           TCD_KPM_FILE_SINK_OK);
    assert(sink.records_written == 1U);
    assert(tcd_kpm_file_sink_close(&sink) == TCD_KPM_FILE_SINK_OK);

    data = read_file(path, &length);
    assert(length > 3000U);
    assert(length < TCD_KPM_SERIALIZED_RECORD_CAPACITY);
    assert(data[length - 1U] == '\n');
    free(data);

    printf("TEST maximum_escaped_record PASS\n");
}

int main(void)
{
    char directory_template[] = "/tmp/tcd-kpm-file-sink-XXXXXX";
    char *directory = mkdtemp(directory_template);

    assert(directory != NULL);

    test_csv_sink(directory);
    test_jsonl_sink(directory);
    test_invalid_record_no_partial_write(directory);
    test_open_and_state_errors(directory);
    test_dev_full_write_failure();
    test_csv_header_failure_dev_full();
    test_maximum_escaped_record(directory);

    {
        static const char *const names[] = {
            "records.csv",
            "records.jsonl",
            "invalid.jsonl",
            "state.jsonl",
            "maximum.jsonl"
        };
        size_t index;
        char path[512];

        for (index = 0U; index < sizeof(names) / sizeof(names[0]); ++index) {
            make_path(path, sizeof(path), directory, names[index]);
            assert(unlink(path) == 0);
        }
        assert(rmdir(directory) == 0);
    }

    printf("FILE_SINK_TEST_COUNT=7\n");
    printf("FILE_SINK_TEST_PASS_COUNT=7\n");
    printf("CSV_FILE_SINK=PASS\n");
    printf("JSONL_FILE_SINK=PASS\n");
    printf("COMPLETE_ROW_WRITE_POLICY=PASS\n");
    printf("INVALID_RECORD_NO_PARTIAL_WRITE=PASS\n");
    printf("WRITE_FLUSH_ERROR_DETECTION=PASS\n");
    printf("FIXED_SERIALIZATION_BUFFER=PASS\n");
    printf("NATIVE_CSV_JSONL_SINKS=PASS\n");

    return EXIT_SUCCESS;
}
