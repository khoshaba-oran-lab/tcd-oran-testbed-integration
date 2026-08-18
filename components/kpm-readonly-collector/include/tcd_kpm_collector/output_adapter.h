#ifndef TCD_KPM_COLLECTOR_OUTPUT_ADAPTER_H
#define TCD_KPM_COLLECTOR_OUTPUT_ADAPTER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "tcd_kpm_collector/record.h"

struct tcd_kpm_output_pipeline;
typedef struct tcd_kpm_output_pipeline tcd_kpm_output_pipeline_t;

bool tcd_kpm_output_adapter_pipeline_create(
    tcd_kpm_output_pipeline_t **pipeline,
    char *error,
    size_t error_capacity);

bool tcd_kpm_output_adapter_submit(
    tcd_kpm_output_pipeline_t *pipeline,
    const tcd_kpm_measurement_record_t *record);

bool tcd_kpm_output_adapter_pipeline_shutdown(
    tcd_kpm_output_pipeline_t **pipeline,
    uint64_t callback_errors,
    uint64_t subscriptions_created,
    uint64_t subscriptions_removed);

#endif
