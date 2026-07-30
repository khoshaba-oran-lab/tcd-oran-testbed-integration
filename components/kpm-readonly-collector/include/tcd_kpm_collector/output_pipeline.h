#ifndef TCD_KPM_COLLECTOR_OUTPUT_PIPELINE_H
#define TCD_KPM_COLLECTOR_OUTPUT_PIPELINE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "tcd_kpm_collector/canonical_record.h"
#include "tcd_kpm_collector/prometheus_textfile.h"

#ifdef __cplusplus
extern "C" {
#endif

#define TCD_KPM_OUTPUT_QUEUE_CAPACITY 64U

typedef struct {
    const char *csv_path;
    const char *jsonl_path;
    const char *prometheus_path;
} tcd_kpm_output_pipeline_config_t;

typedef struct {
    bool enabled;
    bool csv_enabled;
    bool jsonl_enabled;
    bool prometheus_enabled;
    bool failed;
    bool stop_requested;
    uint64_t records_accepted;
    uint64_t records_dropped;
    uint64_t queue_depth;
    tcd_kpm_prometheus_snapshot_t prometheus;
} tcd_kpm_output_pipeline_snapshot_t;

typedef struct tcd_kpm_output_pipeline tcd_kpm_output_pipeline_t;

void tcd_kpm_output_pipeline_config_init(
    tcd_kpm_output_pipeline_config_t *config);

bool tcd_kpm_output_pipeline_create(
    tcd_kpm_output_pipeline_t **pipeline,
    const tcd_kpm_output_pipeline_config_t *config,
    char *error,
    size_t error_capacity);

bool tcd_kpm_output_pipeline_create_from_environment(
    tcd_kpm_output_pipeline_t **pipeline,
    char *error,
    size_t error_capacity);

bool tcd_kpm_output_pipeline_try_submit(
    tcd_kpm_output_pipeline_t *pipeline,
    const tcd_kpm_canonical_record_t *record);

void tcd_kpm_output_pipeline_set_runtime_counters(
    tcd_kpm_output_pipeline_t *pipeline,
    uint64_t callback_errors,
    uint64_t subscriptions_created,
    uint64_t subscriptions_removed);

bool tcd_kpm_output_pipeline_wait_idle(
    tcd_kpm_output_pipeline_t *pipeline,
    uint32_t timeout_ms);

bool tcd_kpm_output_pipeline_snapshot(
    tcd_kpm_output_pipeline_t *pipeline,
    tcd_kpm_output_pipeline_snapshot_t *snapshot);

bool tcd_kpm_output_pipeline_shutdown_and_destroy(
    tcd_kpm_output_pipeline_t **pipeline);

#ifdef __cplusplus
}
#endif

#endif
