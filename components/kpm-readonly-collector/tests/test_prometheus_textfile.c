#define _POSIX_C_SOURCE 200809L

#include "tcd_kpm_collector/prometheus_textfile.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static unsigned int test_count = 0U;
static unsigned int pass_count = 0U;

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(                                                           \
                stderr,                                                        \
                "CHECK failed at %s:%d: %s\n",                                \
                __FILE__,                                                      \
                __LINE__,                                                      \
                #condition);                                                   \
            return 1;                                                          \
        }                                                                      \
    } while (0)

static tcd_kpm_prometheus_snapshot_t sample_snapshot(void)
{
    tcd_kpm_prometheus_snapshot_t snapshot;
    size_t backend;
    size_t reason;

    memset(&snapshot, 0, sizeof(snapshot));
    snapshot.indications_format_1_total = 2U;
    snapshot.indications_format_3_total = 5U;
    snapshot.records_measurement_integer_total = 11U;
    snapshot.records_measurement_real_total = 7U;
    snapshot.records_measurement_no_value_total = 3U;
    snapshot.records_diagnostic_length_mismatch_total = 33U;
    snapshot.records_diagnostic_invalid_input_total = 4U;
    snapshot.rejected_rows_length_mismatch_total = 33U;
    snapshot.rejected_rows_invalid_input_total = 4U;
    snapshot.callback_errors_total = 0U;
    snapshot.subscriptions_created_total = 1U;
    snapshot.subscriptions_removed_total = 1U;

    for (backend = 0U; backend < TCD_KPM_OUTPUT_BACKEND_COUNT; ++backend) {
        snapshot.output_records_ok[backend] = 100U + backend;
        snapshot.output_records_error[backend] = 10U + backend;
        for (reason = 0U; reason < TCD_KPM_OUTPUT_ERROR_COUNT; ++reason) {
            snapshot.output_errors[backend][reason] =
                (backend * 10U) + reason;
        }
    }

    snapshot.output_queue_depth = 8U;
    snapshot.last_receive_timestamp_seconds = 1785340000U;
    snapshot.snapshot_timestamp_seconds = 1785340001U;
    return snapshot;
}

static int read_file(
    const char *path,
    char *buffer,
    size_t capacity,
    size_t *length)
{
    FILE *stream;
    size_t amount;

    if (path == NULL || buffer == NULL || capacity == 0U || length == NULL) {
        return -1;
    }

    stream = fopen(path, "rb");
    if (stream == NULL) {
        return -1;
    }

    amount = fread(buffer, 1U, capacity - 1U, stream);
    if (ferror(stream) != 0) {
        (void)fclose(stream);
        return -1;
    }
    if (fclose(stream) != 0) {
        return -1;
    }

    buffer[amount] = '\0';
    *length = amount;
    return 0;
}

static int make_path(
    char *output,
    size_t capacity,
    const char *directory,
    const char *name)
{
    const int written = snprintf(output, capacity, "%s/%s", directory, name);

    if (written < 0 || (size_t)written >= capacity) {
        return -1;
    }
    return 0;
}

static int test_serialize_snapshot(void)
{
    const tcd_kpm_prometheus_snapshot_t snapshot = sample_snapshot();
    char output[TCD_KPM_PROMETHEUS_MAX_SNAPSHOT_BYTES];
    size_t required = 0U;

    CHECK(
        tcd_kpm_prometheus_serialize(
            &snapshot,
            output,
            sizeof(output),
            &required) == TCD_KPM_PROMETHEUS_OK);
    CHECK(required == strlen(output));
    CHECK(strstr(output, "# TYPE tcd_kpm_collector_build_info gauge\n") != NULL);
    CHECK(strstr(output, "schema_version=\"tcd.kpm.record.emulator-draft-0.1\"") != NULL);
    CHECK(strstr(output, "collector_stage=\"collector-03-sw-prototype\"") != NULL);
    CHECK(strstr(output, "message_format=\"3\"} 5\n") != NULL);
    CHECK(strstr(output, "reason=\"length_mismatch\"} 33\n") != NULL);
    CHECK(strstr(output, "backend=\"parquet\",result=\"ok\"} 103\n") != NULL);
    CHECK(strstr(output, "backend=\"prometheus\",reason=\"rename\"} 24\n") != NULL);
    CHECK(strstr(output, "ue_id") == NULL);
    CHECK(strstr(output, "node_id") == NULL);
    CHECK(strstr(output, "measurement_name") == NULL);
    CHECK(strstr(output, "diagnostic_message") == NULL);

    return 0;
}

static int test_count_only_and_determinism(void)
{
    const tcd_kpm_prometheus_snapshot_t snapshot = sample_snapshot();
    char first[TCD_KPM_PROMETHEUS_MAX_SNAPSHOT_BYTES];
    char second[TCD_KPM_PROMETHEUS_MAX_SNAPSHOT_BYTES];
    size_t count_only = 0U;
    size_t first_length = 0U;
    size_t second_length = 0U;

    CHECK(
        tcd_kpm_prometheus_serialize(
            &snapshot,
            NULL,
            0U,
            &count_only) == TCD_KPM_PROMETHEUS_OK);
    CHECK(
        tcd_kpm_prometheus_serialize(
            &snapshot,
            first,
            sizeof(first),
            &first_length) == TCD_KPM_PROMETHEUS_OK);
    CHECK(
        tcd_kpm_prometheus_serialize(
            &snapshot,
            second,
            sizeof(second),
            &second_length) == TCD_KPM_PROMETHEUS_OK);

    CHECK(count_only == first_length);
    CHECK(first_length == second_length);
    CHECK(memcmp(first, second, first_length + 1U) == 0);
    return 0;
}

static int test_buffer_boundary(void)
{
    const tcd_kpm_prometheus_snapshot_t snapshot = sample_snapshot();
    char full[TCD_KPM_PROMETHEUS_MAX_SNAPSHOT_BYTES];
    char *exact;
    char *short_buffer;
    size_t required = 0U;
    size_t exact_required = 0U;
    size_t short_required = 0U;

    CHECK(
        tcd_kpm_prometheus_serialize(
            &snapshot,
            full,
            sizeof(full),
            &required) == TCD_KPM_PROMETHEUS_OK);

    exact = malloc(required + 1U);
    short_buffer = malloc(required);
    CHECK(exact != NULL);
    CHECK(short_buffer != NULL);

    CHECK(
        tcd_kpm_prometheus_serialize(
            &snapshot,
            exact,
            required + 1U,
            &exact_required) == TCD_KPM_PROMETHEUS_OK);
    CHECK(exact_required == required);
    CHECK(memcmp(exact, full, required + 1U) == 0);

    CHECK(
        tcd_kpm_prometheus_serialize(
            &snapshot,
            short_buffer,
            required,
            &short_required) == TCD_KPM_PROMETHEUS_BUFFER_TOO_SMALL);
    CHECK(short_required == required);

    free(short_buffer);
    free(exact);
    return 0;
}

static int test_atomic_initial_write(void)
{
    const tcd_kpm_prometheus_snapshot_t snapshot = sample_snapshot();
    char directory_template[] = "/tmp/tcd-prom-initial-XXXXXX";
    char path[TCD_KPM_PROMETHEUS_MAX_PATH_BYTES];
    char temporary_path[TCD_KPM_PROMETHEUS_MAX_PATH_BYTES];
    char expected[TCD_KPM_PROMETHEUS_MAX_SNAPSHOT_BYTES];
    char actual[TCD_KPM_PROMETHEUS_MAX_SNAPSHOT_BYTES];
    size_t expected_length = 0U;
    size_t actual_length = 0U;
    tcd_kpm_prometheus_write_result_t result;
    char *directory = mkdtemp(directory_template);

    CHECK(directory != NULL);
    CHECK(make_path(path, sizeof(path), directory, "collector.prom") == 0);
    CHECK(
        snprintf(temporary_path, sizeof(temporary_path), "%s.tmp", path) > 0);

    CHECK(
        tcd_kpm_prometheus_serialize(
            &snapshot,
            expected,
            sizeof(expected),
            &expected_length) == TCD_KPM_PROMETHEUS_OK);
    CHECK(
        tcd_kpm_prometheus_write_atomic(
            path,
            &snapshot,
            &result) == TCD_KPM_PROMETHEUS_OK);
    CHECK(result.status == TCD_KPM_PROMETHEUS_OK);
    CHECK(result.bytes_written == expected_length);
    CHECK(access(temporary_path, F_OK) != 0);
    CHECK(read_file(path, actual, sizeof(actual), &actual_length) == 0);
    CHECK(actual_length == expected_length);
    CHECK(memcmp(actual, expected, expected_length + 1U) == 0);

    CHECK(unlink(path) == 0);
    CHECK(rmdir(directory) == 0);
    return 0;
}

static int test_atomic_replace(void)
{
    tcd_kpm_prometheus_snapshot_t snapshot = sample_snapshot();
    char directory_template[] = "/tmp/tcd-prom-replace-XXXXXX";
    char path[TCD_KPM_PROMETHEUS_MAX_PATH_BYTES];
    char actual[TCD_KPM_PROMETHEUS_MAX_SNAPSHOT_BYTES];
    size_t actual_length = 0U;
    FILE *stream;
    tcd_kpm_prometheus_write_result_t result;
    char *directory = mkdtemp(directory_template);

    CHECK(directory != NULL);
    CHECK(make_path(path, sizeof(path), directory, "collector.prom") == 0);

    stream = fopen(path, "wb");
    CHECK(stream != NULL);
    CHECK(fputs("old\n", stream) >= 0);
    CHECK(fclose(stream) == 0);

    snapshot.output_queue_depth = 77U;
    CHECK(
        tcd_kpm_prometheus_write_atomic(
            path,
            &snapshot,
            &result) == TCD_KPM_PROMETHEUS_OK);
    CHECK(read_file(path, actual, sizeof(actual), &actual_length) == 0);
    CHECK(actual_length > 4U);
    CHECK(strstr(actual, "tcd_kpm_collector_output_queue_depth 77\n") != NULL);
    CHECK(strcmp(actual, "old\n") != 0);

    CHECK(unlink(path) == 0);
    CHECK(rmdir(directory) == 0);
    return 0;
}

static int test_flush_failure_preserves_target(void)
{
    const tcd_kpm_prometheus_snapshot_t snapshot = sample_snapshot();
    char directory_template[] = "/tmp/tcd-prom-full-XXXXXX";
    char path[TCD_KPM_PROMETHEUS_MAX_PATH_BYTES];
    char temporary_path[TCD_KPM_PROMETHEUS_MAX_PATH_BYTES];
    char actual[32];
    size_t actual_length = 0U;
    FILE *stream;
    tcd_kpm_prometheus_write_result_t result;
    char *directory = mkdtemp(directory_template);

    CHECK(directory != NULL);
    CHECK(make_path(path, sizeof(path), directory, "collector.prom") == 0);
    CHECK(
        snprintf(temporary_path, sizeof(temporary_path), "%s.tmp", path) > 0);

    stream = fopen(path, "wb");
    CHECK(stream != NULL);
    CHECK(fputs("stable\n", stream) >= 0);
    CHECK(fclose(stream) == 0);

    CHECK(symlink("/dev/full", temporary_path) == 0);
    {
        const tcd_kpm_prometheus_status_t status =
            tcd_kpm_prometheus_write_atomic(path, &snapshot, &result);

        CHECK(
            status == TCD_KPM_PROMETHEUS_WRITE_FAILED ||
            status == TCD_KPM_PROMETHEUS_FLUSH_FAILED);
        CHECK(result.status == status);
        CHECK(
            result.error_reason == TCD_KPM_OUTPUT_ERROR_WRITE ||
            result.error_reason == TCD_KPM_OUTPUT_ERROR_FLUSH);
    }
    CHECK(access(temporary_path, F_OK) != 0);
    CHECK(read_file(path, actual, sizeof(actual), &actual_length) == 0);
    CHECK(actual_length == strlen("stable\n"));
    CHECK(strcmp(actual, "stable\n") == 0);

    CHECK(unlink(path) == 0);
    CHECK(rmdir(directory) == 0);
    return 0;
}

static int test_rename_failure_removes_temporary(void)
{
    const tcd_kpm_prometheus_snapshot_t snapshot = sample_snapshot();
    char directory_template[] = "/tmp/tcd-prom-rename-XXXXXX";
    char target_directory[TCD_KPM_PROMETHEUS_MAX_PATH_BYTES];
    char temporary_path[TCD_KPM_PROMETHEUS_MAX_PATH_BYTES];
    struct stat target_status;
    tcd_kpm_prometheus_write_result_t result;
    char *directory = mkdtemp(directory_template);

    CHECK(directory != NULL);
    CHECK(
        make_path(
            target_directory,
            sizeof(target_directory),
            directory,
            "target-directory") == 0);
    CHECK(mkdir(target_directory, 0700) == 0);
    CHECK(
        snprintf(
            temporary_path,
            sizeof(temporary_path),
            "%s.tmp",
            target_directory) > 0);

    CHECK(
        tcd_kpm_prometheus_write_atomic(
            target_directory,
            &snapshot,
            &result) == TCD_KPM_PROMETHEUS_RENAME_FAILED);
    CHECK(result.status == TCD_KPM_PROMETHEUS_RENAME_FAILED);
    CHECK(result.error_reason == TCD_KPM_OUTPUT_ERROR_RENAME);
    CHECK(access(temporary_path, F_OK) != 0);
    CHECK(stat(target_directory, &target_status) == 0);
    CHECK(S_ISDIR(target_status.st_mode));

    CHECK(rmdir(target_directory) == 0);
    CHECK(rmdir(directory) == 0);
    return 0;
}

static int test_invalid_arguments_and_path_limit(void)
{
    const tcd_kpm_prometheus_snapshot_t snapshot = sample_snapshot();
    tcd_kpm_prometheus_write_result_t result;
    char *long_path;

    CHECK(
        tcd_kpm_prometheus_serialize(
            NULL,
            NULL,
            0U,
            NULL) == TCD_KPM_PROMETHEUS_INVALID_ARGUMENT);
    CHECK(
        tcd_kpm_prometheus_write_atomic(
            NULL,
            &snapshot,
            &result) == TCD_KPM_PROMETHEUS_INVALID_ARGUMENT);
    CHECK(
        tcd_kpm_prometheus_write_atomic(
            "",
            &snapshot,
            &result) == TCD_KPM_PROMETHEUS_INVALID_ARGUMENT);

    long_path = malloc(TCD_KPM_PROMETHEUS_MAX_PATH_BYTES + 16U);
    CHECK(long_path != NULL);
    memset(long_path, 'a', TCD_KPM_PROMETHEUS_MAX_PATH_BYTES + 15U);
    long_path[TCD_KPM_PROMETHEUS_MAX_PATH_BYTES + 15U] = '\0';

    CHECK(
        tcd_kpm_prometheus_write_atomic(
            long_path,
            &snapshot,
            &result) == TCD_KPM_PROMETHEUS_PATH_TOO_LONG);
    CHECK(result.status == TCD_KPM_PROMETHEUS_PATH_TOO_LONG);

    free(long_path);
    return 0;
}

static int run_test(const char *name, int (*function)(void))
{
    const int rc = function();

    ++test_count;
    if (rc != 0) {
        fprintf(stderr, "TEST %s FAIL\n", name);
        return rc;
    }

    ++pass_count;
    printf("TEST %s PASS\n", name);
    return 0;
}

int main(void)
{
    if (run_test("serialize_snapshot", test_serialize_snapshot) != 0 ||
        run_test(
            "count_only_and_determinism",
            test_count_only_and_determinism) != 0 ||
        run_test("buffer_boundary", test_buffer_boundary) != 0 ||
        run_test("atomic_initial_write", test_atomic_initial_write) != 0 ||
        run_test("atomic_replace", test_atomic_replace) != 0 ||
        run_test(
            "flush_failure_preserves_target",
            test_flush_failure_preserves_target) != 0 ||
        run_test(
            "rename_failure_removes_temporary",
            test_rename_failure_removes_temporary) != 0 ||
        run_test(
            "invalid_arguments_and_path_limit",
            test_invalid_arguments_and_path_limit) != 0) {
        return 1;
    }

    printf("PROMETHEUS_TEXTFILE_TEST_COUNT=%u\n", test_count);
    printf("PROMETHEUS_TEXTFILE_TEST_PASS_COUNT=%u\n", pass_count);
    printf("PROMETHEUS_FORMAT=PASS\n");
    printf("BOUNDED_LABEL_POLICY=PASS\n");
    printf("ATOMIC_RENAME=PASS\n");
    printf("TARGET_PRESERVED_ON_FAILURE=PASS\n");
    printf("TEMPORARY_FILE_CLEANUP=PASS\n");
    printf("WRITE_FLUSH_RENAME_ERROR_DETECTION=PASS\n");
    printf("PROMETHEUS_ATOMIC_TEXTFILE_SINK=PASS\n");

    return test_count == pass_count ? 0 : 1;
}
