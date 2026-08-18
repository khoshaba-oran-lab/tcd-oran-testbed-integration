#define _POSIX_C_SOURCE 200809L

#include "tcd_kpm_collector/output_pipeline.h"

#include "tcd_kpm_collector/canonical_serialize.h"
#include "tcd_kpm_collector/file_sink.h"

#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

struct tcd_kpm_output_pipeline {
    pthread_mutex_t mutex;
    pthread_cond_t work_condition;
    pthread_cond_t idle_condition;
    pthread_t worker;
    bool mutex_initialised;
    bool work_condition_initialised;
    bool idle_condition_initialised;
    bool worker_started;
    bool worker_busy;
    bool stop_requested;

    bool csv_enabled;
    bool jsonl_enabled;
    bool prometheus_enabled;
    char prometheus_path[TCD_KPM_PROMETHEUS_MAX_PATH_BYTES];

    tcd_kpm_file_sink_t csv_sink;
    tcd_kpm_file_sink_t jsonl_sink;

    tcd_kpm_canonical_record_t queue[TCD_KPM_OUTPUT_QUEUE_CAPACITY];
    size_t queue_head;
    size_t queue_tail;
    size_t queue_count;

    uint64_t records_accepted;
    atomic_uint_fast64_t records_dropped;
    atomic_bool failed;

    uint64_t last_indication_sequence;
    bool last_indication_present;
    tcd_kpm_prometheus_snapshot_t prometheus;
};

static void set_error(
    char *error,
    size_t error_capacity,
    const char *message)
{
    if (error == NULL || error_capacity == 0U) {
        return;
    }
    (void)snprintf(error, error_capacity, "%s", message);
}

static bool copy_path(char *destination, size_t capacity, const char *source)
{
    size_t length;

    if (destination == NULL || capacity == 0U || source == NULL) {
        return false;
    }
    length = strlen(source);
    if (length == 0U || length >= capacity) {
        return false;
    }
    memcpy(destination, source, length + 1U);
    return true;
}

static bool path_enabled(const char *path)
{
    return path != NULL && path[0] != '\0';
}

static bool paths_are_distinct(
    const tcd_kpm_output_pipeline_config_t *config)
{
    const char *paths[3] = {
        config->csv_path,
        config->jsonl_path,
        config->prometheus_path,
    };

    for (size_t left = 0U; left < 3U; ++left) {
        if (!path_enabled(paths[left])) {
            continue;
        }
        for (size_t right = left + 1U; right < 3U; ++right) {
            if (path_enabled(paths[right]) &&
                strcmp(paths[left], paths[right]) == 0) {
                return false;
            }
        }
    }
    return true;
}

static uint64_t realtime_seconds(void)
{
    struct timespec now = {0};

    if (clock_gettime(CLOCK_REALTIME, &now) != 0 || now.tv_sec < 0) {
        return 0U;
    }
    return (uint64_t)now.tv_sec;
}

static void mark_failed(tcd_kpm_output_pipeline_t *pipeline)
{
    atomic_store_explicit(&pipeline->failed, true, memory_order_release);
}

static tcd_kpm_output_error_reason_t file_result_reason(
    tcd_kpm_file_sink_result_t result)
{
    switch (result) {
    case TCD_KPM_FILE_SINK_OPEN_FAILED:
        return TCD_KPM_OUTPUT_ERROR_OPEN;
    case TCD_KPM_FILE_SINK_FLUSH_FAILED:
        return TCD_KPM_OUTPUT_ERROR_FLUSH;
    case TCD_KPM_FILE_SINK_CLOSE_FAILED:
        return TCD_KPM_OUTPUT_ERROR_CLOSE;
    case TCD_KPM_FILE_SINK_WRITE_FAILED:
    case TCD_KPM_FILE_SINK_SERIALIZE_FAILED:
    case TCD_KPM_FILE_SINK_FAILED:
    case TCD_KPM_FILE_SINK_INVALID_ARGUMENT:
    case TCD_KPM_FILE_SINK_ALREADY_OPEN:
    default:
        return TCD_KPM_OUTPUT_ERROR_WRITE;
    }
}

static void account_file_result(
    tcd_kpm_output_pipeline_t *pipeline,
    tcd_kpm_output_backend_t backend,
    tcd_kpm_file_sink_result_t result)
{
    if (result == TCD_KPM_FILE_SINK_OK) {
        ++pipeline->prometheus.output_records_ok[backend];
        return;
    }

    ++pipeline->prometheus.output_records_error[backend];
    ++pipeline->prometheus.output_errors[backend][file_result_reason(result)];
    mark_failed(pipeline);
}

static void account_record(
    tcd_kpm_output_pipeline_t *pipeline,
    const tcd_kpm_canonical_record_t *record)
{
    if (!pipeline->last_indication_present ||
        pipeline->last_indication_sequence != record->indication_sequence) {
        if (record->message_format == 1U) {
            ++pipeline->prometheus.indications_format_1_total;
        } else if (record->message_format == 3U) {
            ++pipeline->prometheus.indications_format_3_total;
        }
        pipeline->last_indication_sequence = record->indication_sequence;
        pipeline->last_indication_present = true;
    }

    if (record->record_kind == TCD_KPM_RECORD_KIND_MEASUREMENT) {
        if (record->value_type == TCD_KPM_VALUE_INTEGER) {
            ++pipeline->prometheus.records_measurement_integer_total;
        } else if (record->value_type == TCD_KPM_VALUE_REAL) {
            ++pipeline->prometheus.records_measurement_real_total;
        } else if (record->value_type == TCD_KPM_VALUE_NO_VALUE) {
            ++pipeline->prometheus.records_measurement_no_value_total;
        }
    } else if (record->record_kind == TCD_KPM_RECORD_KIND_DIAGNOSTIC) {
        if (record->structural_status ==
            TCD_KPM_STRUCTURAL_STATUS_LENGTH_MISMATCH) {
            ++pipeline->prometheus.records_diagnostic_length_mismatch_total;
            ++pipeline->prometheus.rejected_rows_length_mismatch_total;
        } else {
            ++pipeline->prometheus.records_diagnostic_invalid_input_total;
            ++pipeline->prometheus.rejected_rows_invalid_input_total;
        }
    }

    pipeline->prometheus.last_receive_timestamp_seconds =
        record->receive_timestamp_us / 1000000U;
}

static void compose_snapshot_locked(
    tcd_kpm_output_pipeline_t *pipeline,
    tcd_kpm_prometheus_snapshot_t *snapshot)
{
    const uint64_t dropped = atomic_load_explicit(
        &pipeline->records_dropped,
        memory_order_acquire);

    *snapshot = pipeline->prometheus;
    snapshot->output_queue_depth = (uint64_t)pipeline->queue_count;
    snapshot->snapshot_timestamp_seconds = realtime_seconds();

    if (dropped > 0U) {
        if (pipeline->csv_enabled) {
            snapshot->output_records_error[TCD_KPM_OUTPUT_BACKEND_CSV] +=
                dropped;
            snapshot->output_errors[TCD_KPM_OUTPUT_BACKEND_CSV]
                                   [TCD_KPM_OUTPUT_ERROR_WRITE] += dropped;
        }
        if (pipeline->jsonl_enabled) {
            snapshot->output_records_error[TCD_KPM_OUTPUT_BACKEND_JSONL] +=
                dropped;
            snapshot->output_errors[TCD_KPM_OUTPUT_BACKEND_JSONL]
                                   [TCD_KPM_OUTPUT_ERROR_WRITE] += dropped;
        }
        if (pipeline->prometheus_enabled) {
            snapshot->output_records_error
                [TCD_KPM_OUTPUT_BACKEND_PROMETHEUS] += dropped;
            snapshot->output_errors[TCD_KPM_OUTPUT_BACKEND_PROMETHEUS]
                                   [TCD_KPM_OUTPUT_ERROR_WRITE] += dropped;
        }
    }
}

static void write_prometheus_snapshot(
    tcd_kpm_output_pipeline_t *pipeline,
    const tcd_kpm_prometheus_snapshot_t *snapshot)
{
    tcd_kpm_prometheus_write_result_t result;
    const tcd_kpm_prometheus_status_t status =
        tcd_kpm_prometheus_write_atomic(
            pipeline->prometheus_path,
            snapshot,
            &result);

    if (pthread_mutex_lock(&pipeline->mutex) != 0) {
        mark_failed(pipeline);
        return;
    }

    if (status == TCD_KPM_PROMETHEUS_OK) {
        ++pipeline->prometheus.output_records_ok
            [TCD_KPM_OUTPUT_BACKEND_PROMETHEUS];
    } else {
        ++pipeline->prometheus.output_records_error
            [TCD_KPM_OUTPUT_BACKEND_PROMETHEUS];
        ++pipeline->prometheus.output_errors
            [TCD_KPM_OUTPUT_BACKEND_PROMETHEUS][result.error_reason];
        mark_failed(pipeline);
    }

    (void)pthread_mutex_unlock(&pipeline->mutex);
}

static void process_record(
    tcd_kpm_output_pipeline_t *pipeline,
    const tcd_kpm_canonical_record_t *record)
{
    tcd_kpm_file_sink_result_t csv_result = TCD_KPM_FILE_SINK_OK;
    tcd_kpm_file_sink_result_t jsonl_result = TCD_KPM_FILE_SINK_OK;
    tcd_kpm_prometheus_snapshot_t snapshot;

    if (pipeline->csv_enabled) {
        csv_result = tcd_kpm_file_sink_write(&pipeline->csv_sink, record);
    }
    if (pipeline->jsonl_enabled) {
        jsonl_result = tcd_kpm_file_sink_write(&pipeline->jsonl_sink, record);
    }

    if (pthread_mutex_lock(&pipeline->mutex) != 0) {
        mark_failed(pipeline);
        return;
    }

    account_record(pipeline, record);
    if (pipeline->csv_enabled) {
        account_file_result(
            pipeline,
            TCD_KPM_OUTPUT_BACKEND_CSV,
            csv_result);
    }
    if (pipeline->jsonl_enabled) {
        account_file_result(
            pipeline,
            TCD_KPM_OUTPUT_BACKEND_JSONL,
            jsonl_result);
    }
    compose_snapshot_locked(pipeline, &snapshot);

    (void)pthread_mutex_unlock(&pipeline->mutex);

    if (pipeline->prometheus_enabled) {
        write_prometheus_snapshot(pipeline, &snapshot);
    }
}

static void *worker_main(void *argument)
{
    tcd_kpm_output_pipeline_t *pipeline = argument;

    for (;;) {
        tcd_kpm_canonical_record_t record;

        if (pthread_mutex_lock(&pipeline->mutex) != 0) {
            mark_failed(pipeline);
            return NULL;
        }

        while (pipeline->queue_count == 0U && !pipeline->stop_requested) {
            if (pthread_cond_wait(
                    &pipeline->work_condition,
                    &pipeline->mutex) != 0) {
                mark_failed(pipeline);
                (void)pthread_mutex_unlock(&pipeline->mutex);
                return NULL;
            }
        }

        if (pipeline->queue_count == 0U && pipeline->stop_requested) {
            pipeline->worker_busy = false;
            (void)pthread_cond_broadcast(&pipeline->idle_condition);
            (void)pthread_mutex_unlock(&pipeline->mutex);
            return NULL;
        }

        record = pipeline->queue[pipeline->queue_head];
        pipeline->queue_head =
            (pipeline->queue_head + 1U) % TCD_KPM_OUTPUT_QUEUE_CAPACITY;
        --pipeline->queue_count;
        pipeline->worker_busy = true;

        (void)pthread_mutex_unlock(&pipeline->mutex);

        process_record(pipeline, &record);

        if (pthread_mutex_lock(&pipeline->mutex) != 0) {
            mark_failed(pipeline);
            return NULL;
        }
        pipeline->worker_busy = false;
        if (pipeline->queue_count == 0U) {
            (void)pthread_cond_broadcast(&pipeline->idle_condition);
        }
        (void)pthread_mutex_unlock(&pipeline->mutex);
    }
}

void tcd_kpm_output_pipeline_config_init(
    tcd_kpm_output_pipeline_config_t *config)
{
    if (config == NULL) {
        return;
    }
    memset(config, 0, sizeof(*config));
}

static void cleanup_partial(tcd_kpm_output_pipeline_t *pipeline)
{
    if (pipeline == NULL) {
        return;
    }
    if (pipeline->csv_sink.is_open) {
        (void)tcd_kpm_file_sink_close(&pipeline->csv_sink);
    }
    if (pipeline->jsonl_sink.is_open) {
        (void)tcd_kpm_file_sink_close(&pipeline->jsonl_sink);
    }
    if (pipeline->idle_condition_initialised) {
        (void)pthread_cond_destroy(&pipeline->idle_condition);
    }
    if (pipeline->work_condition_initialised) {
        (void)pthread_cond_destroy(&pipeline->work_condition);
    }
    if (pipeline->mutex_initialised) {
        (void)pthread_mutex_destroy(&pipeline->mutex);
    }
    free(pipeline);
}

bool tcd_kpm_output_pipeline_create(
    tcd_kpm_output_pipeline_t **pipeline,
    const tcd_kpm_output_pipeline_config_t *config,
    char *error,
    size_t error_capacity)
{
    tcd_kpm_output_pipeline_t *created;
    tcd_kpm_file_sink_result_t sink_result;
    const bool csv_enabled = config != NULL && path_enabled(config->csv_path);
    const bool jsonl_enabled = config != NULL && path_enabled(config->jsonl_path);
    const bool prometheus_enabled =
        config != NULL && path_enabled(config->prometheus_path);

    if (pipeline == NULL || config == NULL) {
        set_error(error, error_capacity, "output pipeline input is null");
        return false;
    }
    *pipeline = NULL;

    if (!csv_enabled && !jsonl_enabled && !prometheus_enabled) {
        return true;
    }
    if (!paths_are_distinct(config)) {
        set_error(error, error_capacity, "output paths must be distinct");
        return false;
    }

    created = calloc(1U, sizeof(*created));
    if (created == NULL) {
        set_error(error, error_capacity, "output pipeline allocation failed");
        return false;
    }

    created->csv_enabled = csv_enabled;
    created->jsonl_enabled = jsonl_enabled;
    created->prometheus_enabled = prometheus_enabled;
    tcd_kpm_file_sink_init(&created->csv_sink);
    tcd_kpm_file_sink_init(&created->jsonl_sink);
    atomic_init(&created->records_dropped, 0U);
    atomic_init(&created->failed, false);

    if (pthread_mutex_init(&created->mutex, NULL) != 0) {
        set_error(error, error_capacity, "output pipeline mutex init failed");
        cleanup_partial(created);
        return false;
    }
    created->mutex_initialised = true;

    if (pthread_cond_init(&created->work_condition, NULL) != 0) {
        set_error(error, error_capacity, "output work condition init failed");
        cleanup_partial(created);
        return false;
    }
    created->work_condition_initialised = true;

    if (pthread_cond_init(&created->idle_condition, NULL) != 0) {
        set_error(error, error_capacity, "output idle condition init failed");
        cleanup_partial(created);
        return false;
    }
    created->idle_condition_initialised = true;

    if (csv_enabled) {
        sink_result = tcd_kpm_file_sink_open(
            &created->csv_sink,
            TCD_KPM_FILE_SINK_FORMAT_CSV,
            config->csv_path);
        if (sink_result != TCD_KPM_FILE_SINK_OK) {
            set_error(error, error_capacity, "CSV output sink open failed");
            cleanup_partial(created);
            return false;
        }
    }

    if (jsonl_enabled) {
        sink_result = tcd_kpm_file_sink_open(
            &created->jsonl_sink,
            TCD_KPM_FILE_SINK_FORMAT_JSONL,
            config->jsonl_path);
        if (sink_result != TCD_KPM_FILE_SINK_OK) {
            set_error(error, error_capacity, "JSONL output sink open failed");
            cleanup_partial(created);
            return false;
        }
    }

    if (prometheus_enabled &&
        !copy_path(
            created->prometheus_path,
            sizeof(created->prometheus_path),
            config->prometheus_path)) {
        set_error(error, error_capacity, "Prometheus output path invalid");
        cleanup_partial(created);
        return false;
    }

    if (pthread_create(&created->worker, NULL, worker_main, created) != 0) {
        set_error(error, error_capacity, "output worker creation failed");
        cleanup_partial(created);
        return false;
    }
    created->worker_started = true;
    *pipeline = created;
    return true;
}

bool tcd_kpm_output_pipeline_create_from_environment(
    tcd_kpm_output_pipeline_t **pipeline,
    char *error,
    size_t error_capacity)
{
    tcd_kpm_output_pipeline_config_t config;

    tcd_kpm_output_pipeline_config_init(&config);
    config.csv_path = getenv("TCD_KPM_OUTPUT_CSV_PATH");
    config.jsonl_path = getenv("TCD_KPM_OUTPUT_JSONL_PATH");
    config.prometheus_path = getenv("TCD_KPM_OUTPUT_PROMETHEUS_PATH");

    return tcd_kpm_output_pipeline_create(
        pipeline,
        &config,
        error,
        error_capacity);
}

bool tcd_kpm_output_pipeline_try_submit(
    tcd_kpm_output_pipeline_t *pipeline,
    const tcd_kpm_canonical_record_t *record)
{
    const char *reason = NULL;

    if (pipeline == NULL) {
        return true;
    }
    if (record == NULL ||
        tcd_kpm_canonical_record_validate(record, &reason) !=
            TCD_KPM_SERIALIZE_OK) {
        (void)reason;
        atomic_fetch_add_explicit(
            &pipeline->records_dropped,
            1U,
            memory_order_relaxed);
        mark_failed(pipeline);
        return false;
    }

    if (pthread_mutex_trylock(&pipeline->mutex) != 0) {
        atomic_fetch_add_explicit(
            &pipeline->records_dropped,
            1U,
            memory_order_relaxed);
        mark_failed(pipeline);
        return false;
    }

    if (pipeline->stop_requested ||
        pipeline->queue_count >= TCD_KPM_OUTPUT_QUEUE_CAPACITY) {
        (void)pthread_mutex_unlock(&pipeline->mutex);
        atomic_fetch_add_explicit(
            &pipeline->records_dropped,
            1U,
            memory_order_relaxed);
        mark_failed(pipeline);
        return false;
    }

    pipeline->queue[pipeline->queue_tail] = *record;
    pipeline->queue_tail =
        (pipeline->queue_tail + 1U) % TCD_KPM_OUTPUT_QUEUE_CAPACITY;
    ++pipeline->queue_count;
    ++pipeline->records_accepted;
    (void)pthread_cond_signal(&pipeline->work_condition);
    (void)pthread_mutex_unlock(&pipeline->mutex);
    return true;
}

void tcd_kpm_output_pipeline_set_runtime_counters(
    tcd_kpm_output_pipeline_t *pipeline,
    uint64_t callback_errors,
    uint64_t subscriptions_created,
    uint64_t subscriptions_removed)
{
    if (pipeline == NULL) {
        return;
    }
    if (pthread_mutex_lock(&pipeline->mutex) != 0) {
        mark_failed(pipeline);
        return;
    }
    pipeline->prometheus.callback_errors_total = callback_errors;
    pipeline->prometheus.subscriptions_created_total = subscriptions_created;
    pipeline->prometheus.subscriptions_removed_total = subscriptions_removed;
    (void)pthread_mutex_unlock(&pipeline->mutex);
}

static bool absolute_deadline(uint32_t timeout_ms, struct timespec *deadline)
{
    if (deadline == NULL || clock_gettime(CLOCK_REALTIME, deadline) != 0) {
        return false;
    }
    deadline->tv_sec += (time_t)(timeout_ms / 1000U);
    deadline->tv_nsec += (long)(timeout_ms % 1000U) * 1000000L;
    if (deadline->tv_nsec >= 1000000000L) {
        ++deadline->tv_sec;
        deadline->tv_nsec -= 1000000000L;
    }
    return true;
}

bool tcd_kpm_output_pipeline_wait_idle(
    tcd_kpm_output_pipeline_t *pipeline,
    uint32_t timeout_ms)
{
    struct timespec deadline;
    bool idle;

    if (pipeline == NULL) {
        return true;
    }
    if (!absolute_deadline(timeout_ms, &deadline)) {
        return false;
    }
    if (pthread_mutex_lock(&pipeline->mutex) != 0) {
        return false;
    }

    while (pipeline->queue_count != 0U || pipeline->worker_busy) {
        const int wait_result = pthread_cond_timedwait(
            &pipeline->idle_condition,
            &pipeline->mutex,
            &deadline);
        if (wait_result == ETIMEDOUT) {
            (void)pthread_mutex_unlock(&pipeline->mutex);
            return false;
        }
        if (wait_result != 0) {
            (void)pthread_mutex_unlock(&pipeline->mutex);
            return false;
        }
    }

    idle = pipeline->queue_count == 0U && !pipeline->worker_busy;
    (void)pthread_mutex_unlock(&pipeline->mutex);
    return idle;
}

bool tcd_kpm_output_pipeline_snapshot(
    tcd_kpm_output_pipeline_t *pipeline,
    tcd_kpm_output_pipeline_snapshot_t *snapshot)
{
    if (snapshot == NULL) {
        return false;
    }
    memset(snapshot, 0, sizeof(*snapshot));
    if (pipeline == NULL) {
        return true;
    }
    if (pthread_mutex_lock(&pipeline->mutex) != 0) {
        return false;
    }

    snapshot->enabled = true;
    snapshot->csv_enabled = pipeline->csv_enabled;
    snapshot->jsonl_enabled = pipeline->jsonl_enabled;
    snapshot->prometheus_enabled = pipeline->prometheus_enabled;
    snapshot->failed = atomic_load_explicit(
        &pipeline->failed,
        memory_order_acquire);
    snapshot->stop_requested = pipeline->stop_requested;
    snapshot->records_accepted = pipeline->records_accepted;
    snapshot->records_dropped = atomic_load_explicit(
        &pipeline->records_dropped,
        memory_order_acquire);
    snapshot->queue_depth = (uint64_t)pipeline->queue_count;
    compose_snapshot_locked(pipeline, &snapshot->prometheus);

    (void)pthread_mutex_unlock(&pipeline->mutex);
    return true;
}

bool tcd_kpm_output_pipeline_shutdown_and_destroy(
    tcd_kpm_output_pipeline_t **pipeline_pointer)
{
    tcd_kpm_output_pipeline_t *pipeline;
    bool success = true;
    tcd_kpm_prometheus_snapshot_t snapshot;

    if (pipeline_pointer == NULL) {
        return false;
    }
    pipeline = *pipeline_pointer;
    *pipeline_pointer = NULL;
    if (pipeline == NULL) {
        return true;
    }

    if (pthread_mutex_lock(&pipeline->mutex) != 0) {
        mark_failed(pipeline);
        success = false;
    } else {
        pipeline->stop_requested = true;
        (void)pthread_cond_broadcast(&pipeline->work_condition);
        (void)pthread_mutex_unlock(&pipeline->mutex);
    }

    if (pipeline->worker_started &&
        pthread_join(pipeline->worker, NULL) != 0) {
        mark_failed(pipeline);
        success = false;
    }
    pipeline->worker_started = false;

    if (pipeline->csv_enabled) {
        const tcd_kpm_file_sink_result_t result =
            tcd_kpm_file_sink_close(&pipeline->csv_sink);
        if (pthread_mutex_lock(&pipeline->mutex) == 0) {
            if (result != TCD_KPM_FILE_SINK_OK) {
                ++pipeline->prometheus.output_errors
                    [TCD_KPM_OUTPUT_BACKEND_CSV][file_result_reason(result)];
                mark_failed(pipeline);
                success = false;
            }
            (void)pthread_mutex_unlock(&pipeline->mutex);
        } else {
            success = false;
        }
    }

    if (pipeline->jsonl_enabled) {
        const tcd_kpm_file_sink_result_t result =
            tcd_kpm_file_sink_close(&pipeline->jsonl_sink);
        if (pthread_mutex_lock(&pipeline->mutex) == 0) {
            if (result != TCD_KPM_FILE_SINK_OK) {
                ++pipeline->prometheus.output_errors
                    [TCD_KPM_OUTPUT_BACKEND_JSONL][file_result_reason(result)];
                mark_failed(pipeline);
                success = false;
            }
            (void)pthread_mutex_unlock(&pipeline->mutex);
        } else {
            success = false;
        }
    }

    if (pthread_mutex_lock(&pipeline->mutex) == 0) {
        compose_snapshot_locked(pipeline, &snapshot);
        (void)pthread_mutex_unlock(&pipeline->mutex);
    } else {
        memset(&snapshot, 0, sizeof(snapshot));
        success = false;
    }

    if (pipeline->prometheus_enabled) {
        tcd_kpm_prometheus_write_result_t result;
        if (tcd_kpm_prometheus_write_atomic(
                pipeline->prometheus_path,
                &snapshot,
                &result) != TCD_KPM_PROMETHEUS_OK) {
            mark_failed(pipeline);
            success = false;
        }
    }

    if (atomic_load_explicit(&pipeline->records_dropped, memory_order_acquire) >
        0U) {
        success = false;
    }
    if (atomic_load_explicit(&pipeline->failed, memory_order_acquire)) {
        success = false;
    }

    cleanup_partial(pipeline);
    return success;
}
