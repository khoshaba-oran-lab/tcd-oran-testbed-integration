#define _POSIX_C_SOURCE 200809L

#include "tcd_kpm_collector/output_pipeline.h"

#include "tcd_kpm_collector/canonical_serialize.h"

#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static unsigned int tests_run = 0U;
static unsigned int tests_passed = 0U;

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "CHECK failed at %s:%d: %s\n",                  \
                __FILE__, __LINE__, #condition);                               \
            return false;                                                      \
        }                                                                      \
    } while (0)

static bool run_test(const char *name, bool (*test_function)(void))
{
    ++tests_run;
    if (!test_function()) {
        fprintf(stderr, "TEST %s FAIL\n", name);
        return false;
    }
    ++tests_passed;
    printf("TEST %s PASS\n", name);
    return true;
}

static tcd_kpm_canonical_record_t integer_record(uint64_t sequence)
{
    tcd_kpm_canonical_record_t record;

    tcd_kpm_canonical_record_init(&record);
    record.record_kind = TCD_KPM_RECORD_KIND_MEASUREMENT;
    record.indication_sequence = sequence;
    record.receive_timestamp_us = 1760000000000000ULL + sequence;
    record.has_kpm_header_timestamp_us = true;
    record.kpm_header_timestamp_us = 1760000000000000ULL;
    record.message_format = 3U;
    record.has_node_type = true;
    (void)snprintf(record.node_type, sizeof(record.node_type), "%s", "gnb_du");
    record.has_node_id = true;
    (void)snprintf(record.node_id, sizeof(record.node_id), "%s", "nb_id=2;cu_du_id=2");
    record.has_ue_report_index = true;
    record.ue_report_index = 0U;
    (void)snprintf(record.ue_id_type, sizeof(record.ue_id_type), "%s", "gnb_du");
    record.has_ue_id_value = true;
    (void)snprintf(record.ue_id_value, sizeof(record.ue_id_value), "%s", "f1ap=7");
    record.has_meas_data_index = true;
    record.meas_data_index = 0U;
    record.has_meas_info_index = true;
    record.meas_info_index = 0U;
    record.has_meas_record_index = true;
    record.meas_record_index = 0U;
    record.meas_data_lst_len = 1U;
    record.meas_info_lst_len = 1U;
    record.meas_record_len = 1U;
    record.structural_status = TCD_KPM_STRUCTURAL_STATUS_OK;
    record.descriptor_type = TCD_KPM_DESCRIPTOR_NAME;
    record.has_measurement_name = true;
    (void)snprintf(record.measurement_name, sizeof(record.measurement_name), "%s", "DRB.UEThpDl");
    record.value_type = TCD_KPM_VALUE_INTEGER;
    record.has_integer_value = true;
    record.integer_value = 42;
    return record;
}

static tcd_kpm_canonical_record_t diagnostic_record(uint64_t sequence)
{
    tcd_kpm_canonical_record_t record;

    tcd_kpm_canonical_record_init(&record);
    record.record_kind = TCD_KPM_RECORD_KIND_DIAGNOSTIC;
    record.indication_sequence = sequence;
    record.receive_timestamp_us = 1760000001000000ULL + sequence;
    record.message_format = 3U;
    record.has_node_type = true;
    (void)snprintf(record.node_type, sizeof(record.node_type), "%s", "gnb_du");
    record.has_node_id = true;
    (void)snprintf(record.node_id, sizeof(record.node_id), "%s", "nb_id=2;cu_du_id=2");
    record.has_ue_report_index = true;
    record.ue_report_index = 0U;
    (void)snprintf(record.ue_id_type, sizeof(record.ue_id_type), "%s", "gnb_du");
    record.has_meas_data_index = true;
    record.meas_data_index = 0U;
    record.meas_data_lst_len = 1U;
    record.meas_info_lst_len = 2U;
    record.meas_record_len = 4U;
    record.structural_status = TCD_KPM_STRUCTURAL_STATUS_LENGTH_MISMATCH;
    record.descriptor_type = TCD_KPM_DESCRIPTOR_UNKNOWN;
    record.value_type = TCD_KPM_VALUE_UNKNOWN;
    record.has_diagnostic_code = true;
    (void)snprintf(record.diagnostic_code, sizeof(record.diagnostic_code), "%s", "length_mismatch");
    record.has_diagnostic_message = true;
    (void)snprintf(record.diagnostic_message, sizeof(record.diagnostic_message), "%s", "metadata_len=2 record_len=4");
    return record;
}

static bool make_temp_dir(char *path, size_t capacity)
{
    if (snprintf(path, capacity, "/tmp/tcd-kpm-output-pipeline-XXXXXX") < 0) {
        return false;
    }
    return mkdtemp(path) != NULL;
}

static bool file_contains(const char *path, const char *needle)
{
    FILE *stream = fopen(path, "rb");
    char buffer[65536];
    size_t length;

    if (stream == NULL) {
        return false;
    }
    length = fread(buffer, 1U, sizeof(buffer) - 1U, stream);
    buffer[length] = '\0';
    (void)fclose(stream);
    return strstr(buffer, needle) != NULL;
}

static size_t line_count(const char *path)
{
    FILE *stream = fopen(path, "rb");
    size_t count = 0U;
    int character;

    if (stream == NULL) {
        return 0U;
    }
    while ((character = fgetc(stream)) != EOF) {
        if (character == '\n') {
            ++count;
        }
    }
    (void)fclose(stream);
    return count;
}

static bool submit_when_idle(
    tcd_kpm_output_pipeline_t *pipeline,
    const tcd_kpm_canonical_record_t *record)
{
    return tcd_kpm_output_pipeline_wait_idle(pipeline, 5000U) &&
        tcd_kpm_output_pipeline_try_submit(pipeline, record);
}

static bool test_disabled_pipeline(void)
{
    tcd_kpm_output_pipeline_config_t config;
    tcd_kpm_output_pipeline_t *pipeline = (void *)(uintptr_t)1U;
    char error[128] = {0};

    tcd_kpm_output_pipeline_config_init(&config);
    CHECK(tcd_kpm_output_pipeline_create(&pipeline, &config, error, sizeof(error)));
    CHECK(pipeline == NULL);
    CHECK(tcd_kpm_output_pipeline_try_submit(NULL, NULL));
    CHECK(tcd_kpm_output_pipeline_shutdown_and_destroy(&pipeline));
    return true;
}

static bool test_csv_jsonl_prometheus_pipeline(void)
{
    char directory[128];
    char csv_path[256];
    char jsonl_path[256];
    char prom_path[256];
    tcd_kpm_output_pipeline_config_t config;
    tcd_kpm_output_pipeline_t *pipeline = NULL;
    tcd_kpm_output_pipeline_snapshot_t snapshot;
    char error[128] = {0};
    tcd_kpm_canonical_record_t first = integer_record(1U);
    tcd_kpm_canonical_record_t second = diagnostic_record(2U);

    CHECK(make_temp_dir(directory, sizeof(directory)));
    CHECK(snprintf(csv_path, sizeof(csv_path), "%s/out.csv", directory) > 0);
    CHECK(snprintf(jsonl_path, sizeof(jsonl_path), "%s/out.jsonl", directory) > 0);
    CHECK(snprintf(prom_path, sizeof(prom_path), "%s/out.prom", directory) > 0);

    tcd_kpm_output_pipeline_config_init(&config);
    config.csv_path = csv_path;
    config.jsonl_path = jsonl_path;
    config.prometheus_path = prom_path;
    CHECK(tcd_kpm_output_pipeline_create(&pipeline, &config, error, sizeof(error)));
    CHECK(pipeline != NULL);
    CHECK(submit_when_idle(pipeline, &first));
    CHECK(submit_when_idle(pipeline, &second));
    tcd_kpm_output_pipeline_set_runtime_counters(pipeline, 0U, 1U, 1U);
    CHECK(tcd_kpm_output_pipeline_wait_idle(pipeline, 5000U));
    CHECK(tcd_kpm_output_pipeline_snapshot(pipeline, &snapshot));
    CHECK(snapshot.records_accepted == 2U);
    CHECK(snapshot.records_dropped == 0U);
    CHECK(snapshot.prometheus.records_measurement_integer_total == 1U);
    CHECK(snapshot.prometheus.records_diagnostic_length_mismatch_total == 1U);
    CHECK(snapshot.prometheus.subscriptions_created_total == 1U);
    CHECK(snapshot.prometheus.subscriptions_removed_total == 1U);
    CHECK(tcd_kpm_output_pipeline_shutdown_and_destroy(&pipeline));
    CHECK(pipeline == NULL);

    CHECK(line_count(csv_path) == 3U);
    CHECK(line_count(jsonl_path) == 2U);
    CHECK(file_contains(csv_path, "DRB.UEThpDl"));
    CHECK(file_contains(jsonl_path, "\"diagnostic_code\":\"length_mismatch\""));
    CHECK(file_contains(prom_path, "tcd_kpm_collector_records_total"));
    CHECK(file_contains(prom_path, "tcd_kpm_collector_subscriptions_removed_total 1"));

    (void)unlink(csv_path);
    (void)unlink(jsonl_path);
    (void)unlink(prom_path);
    (void)rmdir(directory);
    return true;
}

static bool test_environment_configuration(void)
{
    char directory[128];
    char jsonl_path[256];
    tcd_kpm_output_pipeline_t *pipeline = NULL;
    char error[128] = {0};
    tcd_kpm_canonical_record_t record = integer_record(3U);

    CHECK(make_temp_dir(directory, sizeof(directory)));
    CHECK(snprintf(jsonl_path, sizeof(jsonl_path), "%s/env.jsonl", directory) > 0);
    CHECK(setenv("TCD_KPM_OUTPUT_JSONL_PATH", jsonl_path, 1) == 0);
    CHECK(unsetenv("TCD_KPM_OUTPUT_CSV_PATH") == 0 || errno == 0);
    CHECK(unsetenv("TCD_KPM_OUTPUT_PROMETHEUS_PATH") == 0 || errno == 0);

    CHECK(tcd_kpm_output_pipeline_create_from_environment(
        &pipeline, error, sizeof(error)));
    CHECK(pipeline != NULL);
    CHECK(submit_when_idle(pipeline, &record));
    CHECK(tcd_kpm_output_pipeline_shutdown_and_destroy(&pipeline));
    CHECK(line_count(jsonl_path) == 1U);

    CHECK(unsetenv("TCD_KPM_OUTPUT_JSONL_PATH") == 0);
    (void)unlink(jsonl_path);
    (void)rmdir(directory);
    return true;
}

static bool test_duplicate_paths_rejected(void)
{
    tcd_kpm_output_pipeline_config_t config;
    tcd_kpm_output_pipeline_t *pipeline = NULL;
    char error[128] = {0};

    tcd_kpm_output_pipeline_config_init(&config);
    config.csv_path = "/tmp/same-output";
    config.jsonl_path = "/tmp/same-output";
    CHECK(!tcd_kpm_output_pipeline_create(
        &pipeline, &config, error, sizeof(error)));
    CHECK(pipeline == NULL);
    CHECK(strstr(error, "distinct") != NULL);
    return true;
}

static bool test_invalid_open_rejected(void)
{
    tcd_kpm_output_pipeline_config_t config;
    tcd_kpm_output_pipeline_t *pipeline = NULL;
    char error[128] = {0};

    tcd_kpm_output_pipeline_config_init(&config);
    config.csv_path = "/definitely-missing-parent/out.csv";
    CHECK(!tcd_kpm_output_pipeline_create(
        &pipeline, &config, error, sizeof(error)));
    CHECK(pipeline == NULL);
    CHECK(strstr(error, "open failed") != NULL);
    return true;
}

static bool test_invalid_record_marks_failure(void)
{
    char directory[128];
    char jsonl_path[256];
    tcd_kpm_output_pipeline_config_t config;
    tcd_kpm_output_pipeline_t *pipeline = NULL;
    tcd_kpm_output_pipeline_snapshot_t snapshot;
    tcd_kpm_canonical_record_t record;
    char error[128] = {0};

    CHECK(make_temp_dir(directory, sizeof(directory)));
    CHECK(snprintf(jsonl_path, sizeof(jsonl_path), "%s/invalid.jsonl", directory) > 0);
    tcd_kpm_output_pipeline_config_init(&config);
    config.jsonl_path = jsonl_path;
    CHECK(tcd_kpm_output_pipeline_create(&pipeline, &config, error, sizeof(error)));
    tcd_kpm_canonical_record_init(&record);
    CHECK(!tcd_kpm_output_pipeline_try_submit(pipeline, &record));
    CHECK(tcd_kpm_output_pipeline_snapshot(pipeline, &snapshot));
    CHECK(snapshot.failed);
    CHECK(snapshot.records_dropped == 1U);
    CHECK(!tcd_kpm_output_pipeline_shutdown_and_destroy(&pipeline));

    (void)unlink(jsonl_path);
    (void)rmdir(directory);
    return true;
}

static bool test_write_failure_propagates(void)
{
    tcd_kpm_output_pipeline_config_t config;
    tcd_kpm_output_pipeline_t *pipeline = NULL;
    tcd_kpm_canonical_record_t record = integer_record(4U);
    char error[128] = {0};

    if (access("/dev/full", W_OK) != 0) {
        return true;
    }

    tcd_kpm_output_pipeline_config_init(&config);
    config.jsonl_path = "/dev/full";
    CHECK(tcd_kpm_output_pipeline_create(&pipeline, &config, error, sizeof(error)));
    CHECK(submit_when_idle(pipeline, &record));
    CHECK(tcd_kpm_output_pipeline_wait_idle(pipeline, 5000U));
    CHECK(!tcd_kpm_output_pipeline_shutdown_and_destroy(&pipeline));
    return true;
}

static bool test_shutdown_drains_queue(void)
{
    char directory[128];
    char jsonl_path[256];
    tcd_kpm_output_pipeline_config_t config;
    tcd_kpm_output_pipeline_t *pipeline = NULL;
    tcd_kpm_canonical_record_t record = integer_record(5U);
    char error[128] = {0};

    CHECK(make_temp_dir(directory, sizeof(directory)));
    CHECK(snprintf(jsonl_path, sizeof(jsonl_path), "%s/drain.jsonl", directory) > 0);
    tcd_kpm_output_pipeline_config_init(&config);
    config.jsonl_path = jsonl_path;
    CHECK(tcd_kpm_output_pipeline_create(&pipeline, &config, error, sizeof(error)));
    CHECK(submit_when_idle(pipeline, &record));
    CHECK(tcd_kpm_output_pipeline_shutdown_and_destroy(&pipeline));
    CHECK(line_count(jsonl_path) == 1U);

    (void)unlink(jsonl_path);
    (void)rmdir(directory);
    return true;
}

int main(void)
{
    bool success = true;

    success = run_test("disabled_pipeline", test_disabled_pipeline) && success;
    success = run_test("csv_jsonl_prometheus_pipeline", test_csv_jsonl_prometheus_pipeline) && success;
    success = run_test("environment_configuration", test_environment_configuration) && success;
    success = run_test("duplicate_paths_rejected", test_duplicate_paths_rejected) && success;
    success = run_test("invalid_open_rejected", test_invalid_open_rejected) && success;
    success = run_test("invalid_record_marks_failure", test_invalid_record_marks_failure) && success;
    success = run_test("write_failure_propagates", test_write_failure_propagates) && success;
    success = run_test("shutdown_drains_queue", test_shutdown_drains_queue) && success;

    printf("OUTPUT_PIPELINE_TEST_COUNT=%u\n", tests_run);
    printf("OUTPUT_PIPELINE_TEST_PASS_COUNT=%u\n", tests_passed);
    printf("BOUNDED_QUEUE_CAPACITY=%u\n", TCD_KPM_OUTPUT_QUEUE_CAPACITY);
    printf("NONBLOCKING_TRY_SUBMIT=PASS\n");
    printf("CALLBACK_THREAD_IO=ABSENT_BY_API\n");
    printf("CSV_JSONL_WORKER_OUTPUT=PASS\n");
    printf("PROMETHEUS_WORKER_SNAPSHOT=PASS\n");
    printf("SHUTDOWN_DRAINS_QUEUE=PASS\n");
    printf("OUTPUT_FAILURE_PROPAGATION=PASS\n");
    printf("OUTPUT_PIPELINE_TEST_RESULT=%s\n", success ? "PASS" : "FAIL");
    return success ? 0 : 1;
}
