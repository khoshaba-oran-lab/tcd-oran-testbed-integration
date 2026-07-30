#ifndef TCD_KPM_COLLECTOR_CANONICAL_RECORD_H
#define TCD_KPM_COLLECTOR_CANONICAL_RECORD_H

#include <stdbool.h>
#include <stdint.h>

#define TCD_KPM_CANONICAL_SCHEMA_VERSION "tcd.kpm.record.emulator-draft-0.1"

#define TCD_KPM_NODE_TYPE_CAPACITY 32U
#define TCD_KPM_NODE_ID_CAPACITY 128U
#define TCD_KPM_UE_ID_TYPE_CAPACITY 32U
#define TCD_KPM_UE_ID_VALUE_CAPACITY 128U
#define TCD_KPM_MEASUREMENT_NAME_CAPACITY 256U
#define TCD_KPM_DIAGNOSTIC_CODE_CAPACITY 64U
#define TCD_KPM_DIAGNOSTIC_MESSAGE_CAPACITY 256U

typedef enum {
    TCD_KPM_RECORD_KIND_INVALID = 0,
    TCD_KPM_RECORD_KIND_MEASUREMENT = 1,
    TCD_KPM_RECORD_KIND_DIAGNOSTIC = 2
} tcd_kpm_record_kind_t;

typedef enum {
    TCD_KPM_STRUCTURAL_STATUS_INVALID = 0,
    TCD_KPM_STRUCTURAL_STATUS_OK = 1,
    TCD_KPM_STRUCTURAL_STATUS_NO_VALUE = 2,
    TCD_KPM_STRUCTURAL_STATUS_LENGTH_MISMATCH = 3,
    TCD_KPM_STRUCTURAL_STATUS_INVALID_INPUT = 4,
    TCD_KPM_STRUCTURAL_STATUS_UNSUPPORTED_UE_ID = 5,
    TCD_KPM_STRUCTURAL_STATUS_UNSUPPORTED_DESCRIPTOR = 6,
    TCD_KPM_STRUCTURAL_STATUS_UNSUPPORTED_VALUE_TYPE = 7
} tcd_kpm_structural_status_t;

typedef enum {
    TCD_KPM_DESCRIPTOR_UNKNOWN = 0,
    TCD_KPM_DESCRIPTOR_NAME = 1,
    TCD_KPM_DESCRIPTOR_ID = 2
} tcd_kpm_descriptor_type_t;

typedef enum {
    TCD_KPM_VALUE_UNKNOWN = 0,
    TCD_KPM_VALUE_INTEGER = 1,
    TCD_KPM_VALUE_REAL = 2,
    TCD_KPM_VALUE_NO_VALUE = 3
} tcd_kpm_value_type_t;

typedef struct {
    tcd_kpm_record_kind_t record_kind;
    uint64_t indication_sequence;
    uint64_t receive_timestamp_us;

    bool has_kpm_header_timestamp_us;
    uint64_t kpm_header_timestamp_us;

    uint32_t message_format;

    bool has_node_type;
    char node_type[TCD_KPM_NODE_TYPE_CAPACITY];

    bool has_node_id;
    char node_id[TCD_KPM_NODE_ID_CAPACITY];

    bool has_ue_report_index;
    uint32_t ue_report_index;

    char ue_id_type[TCD_KPM_UE_ID_TYPE_CAPACITY];

    bool has_ue_id_value;
    char ue_id_value[TCD_KPM_UE_ID_VALUE_CAPACITY];

    bool has_meas_data_index;
    uint32_t meas_data_index;

    bool has_meas_info_index;
    uint32_t meas_info_index;

    bool has_meas_record_index;
    uint32_t meas_record_index;

    uint32_t meas_data_lst_len;
    uint32_t meas_info_lst_len;
    uint32_t meas_record_len;

    bool incomplete_flag_present;
    bool incomplete_flag;

    tcd_kpm_structural_status_t structural_status;
    tcd_kpm_descriptor_type_t descriptor_type;

    bool has_measurement_name;
    char measurement_name[TCD_KPM_MEASUREMENT_NAME_CAPACITY];

    bool has_measurement_id;
    uint32_t measurement_id;

    tcd_kpm_value_type_t value_type;

    bool has_integer_value;
    int64_t integer_value;

    bool has_real_value;
    double real_value;

    bool has_diagnostic_code;
    char diagnostic_code[TCD_KPM_DIAGNOSTIC_CODE_CAPACITY];

    bool has_diagnostic_message;
    char diagnostic_message[TCD_KPM_DIAGNOSTIC_MESSAGE_CAPACITY];
} tcd_kpm_canonical_record_t;

#endif
