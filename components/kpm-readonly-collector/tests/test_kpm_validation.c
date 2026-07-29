#include "tcd_kpm_collector/kpm_validation.h"

#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FIELD_COUNT 8U
#define LINE_CAPACITY 1024U
#define MAX_SUPPORTED_LENGTH 65535U

static bool parse_size(const char *text, size_t *value)
{
    if (text == NULL || value == NULL || *text == '\0') {
        return false;
    }

    errno = 0;
    char *end = NULL;
    const unsigned long long parsed = strtoull(text, &end, 10);

    if (errno != 0 || end == text || *end != '\0') {
        return false;
    }

    *value = (size_t)parsed;
    return (unsigned long long)*value == parsed;
}

static bool parse_unsigned(const char *text, unsigned int *value)
{
    size_t parsed = 0U;

    if (!parse_size(text, &parsed) || parsed > 4294967295ULL) {
        return false;
    }

    *value = (unsigned int)parsed;
    return true;
}

static size_t split_fields(char *line, char **fields, size_t capacity)
{
    size_t count = 0U;
    char *cursor = line;

    while (count < capacity) {
        fields[count++] = cursor;
        char *tab = strchr(cursor, '\t');

        if (tab == NULL) {
            break;
        }

        *tab = '\0';
        cursor = tab + 1;
    }

    return count;
}

static int run_contract_vectors(const char *path)
{
    FILE *stream = fopen(path, "r");

    if (stream == NULL) {
        perror("fopen");
        return 1;
    }

    char line[LINE_CAPACITY] = {0};

    if (fgets(line, sizeof(line), stream) == NULL) {
        (void)fclose(stream);
        fprintf(stderr, "missing TSV header\n");
        return 1;
    }

    size_t vector_count = 0U;
    size_t passed_count = 0U;
    unsigned char metadata_storage = 0U;
    unsigned char record_storage = 0U;

    while (fgets(line, sizeof(line), stream) != NULL) {
        line[strcspn(line, "\r\n")] = '\0';

        if (line[0] == '\0') {
            continue;
        }

        char *fields[FIELD_COUNT] = {0};
        const size_t field_count = split_fields(line, fields, FIELD_COUNT);

        if (field_count != FIELD_COUNT) {
            fprintf(stderr, "invalid field count: %zu\n", field_count);
            (void)fclose(stream);
            return 1;
        }

        size_t metadata_len = 0U;
        size_t record_len = 0U;
        size_t expected_values = 0U;
        unsigned int expected_diagnostics = 0U;

        if (
            !parse_size(fields[2], &metadata_len) ||
            !parse_size(fields[3], &record_len) ||
            !parse_size(fields[5], &expected_values) ||
            !parse_unsigned(fields[6], &expected_diagnostics)
        ) {
            fprintf(stderr, "invalid numeric field in case %s\n", fields[0]);
            (void)fclose(stream);
            return 1;
        }

        const bool metadata_available = strcmp(fields[1], "present") == 0;
        const bool metadata_unavailable = strcmp(fields[1], "unavailable") == 0;

        if (!metadata_available && !metadata_unavailable) {
            fprintf(stderr, "invalid metadata state in case %s\n", fields[0]);
            (void)fclose(stream);
            return 1;
        }

        const tcd_kpm_row_shape_t shape = {
            .metadata_available = metadata_available,
            .metadata = metadata_available ? &metadata_storage : NULL,
            .metadata_len = metadata_len,
            .record = record_len > 0U ? &record_storage : NULL,
            .record_len = record_len,
            .maximum_supported_length = MAX_SUPPORTED_LENGTH,
        };

        const tcd_kpm_row_validation_result_t result =
            tcd_kpm_validate_row_shape(&shape);
        const char *actual_status =
            tcd_kpm_row_validation_status_name(result.status);
        const bool expected_continue = strcmp(fields[7], "yes") == 0;

        const bool passed =
            strcmp(actual_status, fields[4]) == 0 &&
            result.normalised_value_count == expected_values &&
            result.diagnostic_count == expected_diagnostics &&
            result.process_continues == expected_continue &&
            result.row_accepted == (strcmp(fields[4], "ok") == 0);

        printf(
            "VECTOR\t%s\t%s\t%zu\t%u\t%s\t%s\n",
            fields[0],
            actual_status,
            result.normalised_value_count,
            result.diagnostic_count,
            result.process_continues ? "yes" : "no",
            passed ? "PASS" : "FAIL"
        );

        vector_count += 1U;
        passed_count += passed ? 1U : 0U;
    }

    (void)fclose(stream);

    if (vector_count != 6U || passed_count != vector_count) {
        fprintf(
            stderr,
            "vector failure: total=%zu passed=%zu\n",
            vector_count,
            passed_count
        );
        return 1;
    }

    printf("VECTOR_COUNT=%zu\n", vector_count);
    printf("VECTOR_PASS_COUNT=%zu\n", passed_count);
    return 0;
}

static int run_additional_defensive_cases(void)
{
    unsigned char storage = 0U;

    const tcd_kpm_row_shape_t null_record = {
        .metadata_available = true,
        .metadata = &storage,
        .metadata_len = 2U,
        .record = NULL,
        .record_len = 2U,
        .maximum_supported_length = MAX_SUPPORTED_LENGTH,
    };

    const tcd_kpm_row_shape_t oversized_record = {
        .metadata_available = true,
        .metadata = &storage,
        .metadata_len = 2U,
        .record = &storage,
        .record_len = MAX_SUPPORTED_LENGTH + 1U,
        .maximum_supported_length = MAX_SUPPORTED_LENGTH,
    };

    const tcd_kpm_row_shape_t null_metadata = {
        .metadata_available = true,
        .metadata = NULL,
        .metadata_len = 2U,
        .record = &storage,
        .record_len = 2U,
        .maximum_supported_length = MAX_SUPPORTED_LENGTH,
    };

    const tcd_kpm_row_validation_result_t null_record_result =
        tcd_kpm_validate_row_shape(&null_record);
    const tcd_kpm_row_validation_result_t oversized_result =
        tcd_kpm_validate_row_shape(&oversized_record);
    const tcd_kpm_row_validation_result_t null_metadata_result =
        tcd_kpm_validate_row_shape(&null_metadata);

    if (
        null_record_result.status != TCD_KPM_ROW_INVALID_INPUT ||
        oversized_result.status != TCD_KPM_ROW_INVALID_RECORD_LENGTH ||
        null_metadata_result.status != TCD_KPM_ROW_INVALID_INPUT
    ) {
        fprintf(stderr, "additional defensive case failed\n");
        return 1;
    }

    printf("ADDITIONAL_DEFENSIVE_CASES=PASS\n");
    return 0;
}

static int run_continuation_sequence(void)
{
    unsigned char metadata = 0U;
    unsigned char record = 0U;

    const tcd_kpm_row_shape_t rejected_shape = {
        .metadata_available = true,
        .metadata = &metadata,
        .metadata_len = 2U,
        .record = &record,
        .record_len = 4U,
        .maximum_supported_length = MAX_SUPPORTED_LENGTH,
    };

    const tcd_kpm_row_shape_t valid_shape = {
        .metadata_available = true,
        .metadata = &metadata,
        .metadata_len = 2U,
        .record = &record,
        .record_len = 2U,
        .maximum_supported_length = MAX_SUPPORTED_LENGTH,
    };

    const tcd_kpm_row_validation_result_t rejected_result =
        tcd_kpm_validate_row_shape(&rejected_shape);
    const tcd_kpm_row_validation_result_t valid_result =
        tcd_kpm_validate_row_shape(&valid_shape);

    if (
        rejected_result.status != TCD_KPM_ROW_LENGTH_MISMATCH ||
        rejected_result.normalised_value_count != 0U ||
        !rejected_result.process_continues ||
        valid_result.status != TCD_KPM_ROW_OK ||
        valid_result.normalised_value_count != 2U ||
        !valid_result.row_accepted
    ) {
        fprintf(stderr, "continuation sequence failed\n");
        return 1;
    }

    printf("CONTINUATION_SEQUENCE=PASS\n");
    return 0;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s <test-vectors.tsv>\n", argv[0]);
        return 2;
    }

    if (
        run_contract_vectors(argv[1]) != 0 ||
        run_additional_defensive_cases() != 0 ||
        run_continuation_sequence() != 0
    ) {
        return 1;
    }

    printf("SILENT_TRUNCATION_OBSERVED=no\n");
    printf("VALIDATION_CORE_TEST_RESULT=PASS\n");
    return 0;
}
