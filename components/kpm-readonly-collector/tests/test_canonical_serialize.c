#include "tcd_kpm_collector/canonical_serialize.h"

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void copy_text(char *destination, size_t capacity, const char *source)
{
    const size_t length = strlen(source);
    assert(length < capacity);
    memcpy(destination, source, length + 1U);
}

static tcd_kpm_canonical_record_t measurement_integer_record(void)
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
    copy_text(record.ue_id_value, sizeof(record.ue_id_value), "ue\n1");
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

static void test_csv_header(void)
{
    char output[1024];
    size_t required = 0U;
    const char expected[] =
        "schema_version,record_kind,indication_sequence,receive_timestamp_us,"
        "kpm_header_timestamp_us,message_format,node_type,node_id,"
        "ue_report_index,ue_id_type,ue_id_value,meas_data_index,"
        "meas_info_index,meas_record_index,meas_data_lst_len,"
        "meas_info_lst_len,meas_record_len,incomplete_flag_present,"
        "incomplete_flag,structural_status,descriptor_type,measurement_name,"
        "measurement_id,value_type,integer_value,real_value,diagnostic_code,"
        "diagnostic_message\n";

    assert(tcd_kpm_serialize_csv_header(
        output,
        sizeof(output),
        &required) == TCD_KPM_SERIALIZE_OK);
    assert(required == strlen(expected));
    assert(strcmp(output, expected) == 0);
    printf("TEST csv_header PASS\n");
}

static void test_integer_serialization(void)
{
    tcd_kpm_canonical_record_t record = measurement_integer_record();
    char csv[2048];
    char json[4096];
    size_t csv_length = 0U;
    size_t json_length = 0U;
    const char *reason = NULL;

    assert(tcd_kpm_canonical_record_validate(&record, &reason) ==
           TCD_KPM_SERIALIZE_OK);
    assert(reason == NULL);
    assert(tcd_kpm_serialize_csv_record(
        &record,
        csv,
        sizeof(csv),
        &csv_length) == TCD_KPM_SERIALIZE_OK);
    assert(tcd_kpm_serialize_jsonl_record(
        &record,
        json,
        sizeof(json),
        &json_length) == TCD_KPM_SERIALIZE_OK);

    assert(csv_length == strlen(csv));
    assert(json_length == strlen(json));
    assert(strstr(csv, "\"gnb,du\"") != NULL);
    assert(strstr(csv, "\"node\"\"A\"") != NULL);
    assert(strstr(csv, "\"ue\n1\"") != NULL);
    assert(strstr(csv, ",\"integer\",-42,,,") != NULL);
    assert(strstr(json, "\"schema_version\":\"tcd.kpm.record.emulator-draft-0.1\"") != NULL);
    assert(strstr(json, "\"node_type\":\"gnb,du\"") != NULL);
    assert(strstr(json, "\"node_id\":\"node\\\"A\"") != NULL);
    assert(strstr(json, "\"ue_id_value\":\"ue\\n1\"") != NULL);
    assert(strstr(json, "\"integer_value\":-42") != NULL);
    assert(json[json_length - 1U] == '\n');
    printf("TEST integer_serialization PASS\n");
}

static void test_diagnostic_serialization(void)
{
    tcd_kpm_canonical_record_t record = diagnostic_record();
    char csv[2048];
    char json[4096];
    size_t length = 0U;

    assert(tcd_kpm_serialize_csv_record(
        &record,
        csv,
        sizeof(csv),
        &length) == TCD_KPM_SERIALIZE_OK);
    assert(strstr(csv, "\"length_mismatch\"") != NULL);
    assert(strstr(
        csv,
        "\"length_mismatch\",\"unknown\",,,\"unknown\",,,\"length_mismatch\"") != NULL);

    assert(tcd_kpm_serialize_jsonl_record(
        &record,
        json,
        sizeof(json),
        &length) == TCD_KPM_SERIALIZE_OK);
    assert(strstr(json, "\"record_kind\":\"diagnostic\"") != NULL);
    assert(strstr(json, "\"meas_info_index\":null") != NULL);
    assert(strstr(json, "\"meas_record_index\":null") != NULL);
    assert(strstr(json, "\"measurement_name\":null") != NULL);
    assert(strstr(json, "\"integer_value\":null") != NULL);
    assert(strstr(json, "\"real_value\":null") != NULL);
    assert(strstr(json, "\"diagnostic_code\":\"length_mismatch\"") != NULL);
    printf("TEST diagnostic_serialization PASS\n");
}

static void test_real_and_no_value(void)
{
    tcd_kpm_canonical_record_t real_record = measurement_integer_record();
    tcd_kpm_canonical_record_t no_value_record = measurement_integer_record();
    char json[4096];
    size_t length = 0U;

    real_record.descriptor_type = TCD_KPM_DESCRIPTOR_ID;
    real_record.has_measurement_name = false;
    real_record.has_measurement_id = true;
    real_record.measurement_id = 17U;
    real_record.value_type = TCD_KPM_VALUE_REAL;
    real_record.has_integer_value = false;
    real_record.has_real_value = true;
    real_record.real_value = 1.25;

    assert(tcd_kpm_serialize_jsonl_record(
        &real_record,
        json,
        sizeof(json),
        &length) == TCD_KPM_SERIALIZE_OK);
    assert(strstr(json, "\"measurement_id\":17") != NULL);
    assert(strstr(json, "\"real_value\":1.25") != NULL);

    no_value_record.structural_status = TCD_KPM_STRUCTURAL_STATUS_NO_VALUE;
    no_value_record.value_type = TCD_KPM_VALUE_NO_VALUE;
    no_value_record.has_integer_value = false;

    assert(tcd_kpm_serialize_jsonl_record(
        &no_value_record,
        json,
        sizeof(json),
        &length) == TCD_KPM_SERIALIZE_OK);
    assert(strstr(json, "\"value_type\":\"no_value\"") != NULL);
    assert(strstr(json, "\"integer_value\":null") != NULL);
    assert(strstr(json, "\"real_value\":null") != NULL);
    printf("TEST real_and_no_value PASS\n");
}

static void test_buffer_sizing_and_determinism(void)
{
    tcd_kpm_canonical_record_t record = measurement_integer_record();
    char first[4096];
    char second[4096];
    char small[17];
    size_t required_count_only = 0U;
    size_t required_small = 0U;
    size_t required_full = 0U;

    assert(tcd_kpm_serialize_jsonl_record(
        &record,
        NULL,
        0U,
        &required_count_only) == TCD_KPM_SERIALIZE_BUFFER_TOO_SMALL);
    assert(required_count_only > sizeof(small));

    memset(small, 'X', sizeof(small));
    assert(tcd_kpm_serialize_jsonl_record(
        &record,
        small,
        sizeof(small),
        &required_small) == TCD_KPM_SERIALIZE_BUFFER_TOO_SMALL);
    assert(required_small == required_count_only);
    assert(small[sizeof(small) - 1U] == '\0');

    assert(tcd_kpm_serialize_jsonl_record(
        &record,
        first,
        sizeof(first),
        &required_full) == TCD_KPM_SERIALIZE_OK);
    assert(required_full == required_count_only);
    assert(tcd_kpm_serialize_jsonl_record(
        &record,
        second,
        sizeof(second),
        NULL) == TCD_KPM_SERIALIZE_OK);
    assert(strcmp(first, second) == 0);
    printf("TEST buffer_sizing_and_determinism PASS\n");
}

static void test_invalid_records(void)
{
    tcd_kpm_canonical_record_t record = measurement_integer_record();
    const char *reason = NULL;

    record.has_meas_record_index = false;
    assert(tcd_kpm_canonical_record_validate(&record, &reason) ==
           TCD_KPM_SERIALIZE_INVALID_RECORD);
    assert(strcmp(reason, "measurement_pair_indexes_invalid") == 0);

    record = diagnostic_record();
    record.meas_record_len = record.meas_info_lst_len;
    assert(tcd_kpm_canonical_record_validate(&record, &reason) ==
           TCD_KPM_SERIALIZE_INVALID_RECORD);
    assert(strcmp(reason, "length_mismatch_lengths_equal") == 0);

    record = measurement_integer_record();
    record.value_type = TCD_KPM_VALUE_REAL;
    record.has_integer_value = false;
    record.has_real_value = true;
    record.real_value = NAN;
    assert(tcd_kpm_canonical_record_validate(&record, &reason) ==
           TCD_KPM_SERIALIZE_INVALID_RECORD);
    assert(strcmp(reason, "real_value_invalid") == 0);

    record = measurement_integer_record();
    record.node_type[0] = (char)0xC0;
    record.node_type[1] = (char)0xAF;
    record.node_type[2] = '\0';
    assert(tcd_kpm_canonical_record_validate(&record, &reason) ==
           TCD_KPM_SERIALIZE_INVALID_RECORD);
    assert(strcmp(reason, "invalid_utf8_or_unterminated_string") == 0);

    printf("TEST invalid_records PASS\n");
}

static void test_json_control_escape(void)
{
    tcd_kpm_canonical_record_t record = diagnostic_record();
    char json[4096];
    size_t length = 0U;

    copy_text(
        record.diagnostic_message,
        sizeof(record.diagnostic_message),
        "quote=\" slash=\\ tab=\t control=\001");
    assert(tcd_kpm_serialize_jsonl_record(
        &record,
        json,
        sizeof(json),
        &length) == TCD_KPM_SERIALIZE_OK);
    assert(strstr(json, "quote=\\\"") != NULL);
    assert(strstr(json, "slash=\\\\") != NULL);
    assert(strstr(json, "tab=\\t") != NULL);
    assert(strstr(json, "control=\\u0001") != NULL);
    printf("TEST json_control_escape PASS\n");
}

int main(void)
{
    test_csv_header();
    test_integer_serialization();
    test_diagnostic_serialization();
    test_real_and_no_value();
    test_buffer_sizing_and_determinism();
    test_invalid_records();
    test_json_control_escape();

    printf("CANONICAL_SERIALIZATION_TEST_COUNT=7\n");
    printf("CANONICAL_SERIALIZATION_TEST_PASS_COUNT=7\n");
    printf("CSV_SERIALIZATION=PASS\n");
    printf("JSONL_SERIALIZATION=PASS\n");
    printf("UTF8_VALIDATION=PASS\n");
    printf("NONFINITE_NUMBER_REJECTION=PASS\n");
    printf("BUFFER_BOUNDARY_VALIDATION=PASS\n");
    printf("DETERMINISTIC_SERIALIZATION=PASS\n");
    printf("CANONICAL_SERIALIZATION_CORE=PASS\n");
    return EXIT_SUCCESS;
}
