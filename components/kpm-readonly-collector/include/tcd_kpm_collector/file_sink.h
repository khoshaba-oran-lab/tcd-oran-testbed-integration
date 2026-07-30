#ifndef TCD_KPM_COLLECTOR_FILE_SINK_H
#define TCD_KPM_COLLECTOR_FILE_SINK_H

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "tcd_kpm_collector/canonical_record.h"

#define TCD_KPM_FILE_SINK_PATH_CAPACITY 4096U
#define TCD_KPM_SERIALIZED_RECORD_CAPACITY 8192U

typedef enum {
    TCD_KPM_FILE_SINK_FORMAT_INVALID = 0,
    TCD_KPM_FILE_SINK_FORMAT_CSV = 1,
    TCD_KPM_FILE_SINK_FORMAT_JSONL = 2
} tcd_kpm_file_sink_format_t;

typedef enum {
    TCD_KPM_FILE_SINK_OK = 0,
    TCD_KPM_FILE_SINK_INVALID_ARGUMENT = 1,
    TCD_KPM_FILE_SINK_ALREADY_OPEN = 2,
    TCD_KPM_FILE_SINK_OPEN_FAILED = 3,
    TCD_KPM_FILE_SINK_SERIALIZE_FAILED = 4,
    TCD_KPM_FILE_SINK_WRITE_FAILED = 5,
    TCD_KPM_FILE_SINK_FLUSH_FAILED = 6,
    TCD_KPM_FILE_SINK_CLOSE_FAILED = 7,
    TCD_KPM_FILE_SINK_FAILED = 8
} tcd_kpm_file_sink_result_t;

typedef struct {
    FILE *stream;
    tcd_kpm_file_sink_format_t format;
    bool is_open;
    bool failed;
    uint64_t records_written;
    uint64_t errors;
    char path[TCD_KPM_FILE_SINK_PATH_CAPACITY];
} tcd_kpm_file_sink_t;

void tcd_kpm_file_sink_init(tcd_kpm_file_sink_t *sink);

const char *tcd_kpm_file_sink_result_name(
    tcd_kpm_file_sink_result_t result);

const char *tcd_kpm_file_sink_format_name(
    tcd_kpm_file_sink_format_t format);

tcd_kpm_file_sink_result_t tcd_kpm_file_sink_open(
    tcd_kpm_file_sink_t *sink,
    tcd_kpm_file_sink_format_t format,
    const char *path);

tcd_kpm_file_sink_result_t tcd_kpm_file_sink_write(
    tcd_kpm_file_sink_t *sink,
    const tcd_kpm_canonical_record_t *record);

tcd_kpm_file_sink_result_t tcd_kpm_file_sink_close(
    tcd_kpm_file_sink_t *sink);

#endif
