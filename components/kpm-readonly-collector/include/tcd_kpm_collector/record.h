#ifndef TCD_KPM_COLLECTOR_RECORD_H
#define TCD_KPM_COLLECTOR_RECORD_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define TCD_KPM_NODE_ID_CAPACITY 128U
#define TCD_KPM_MEASUREMENT_NAME_CAPACITY 256U

typedef enum {
    TCD_KPM_STATUS_OK = 0,
    TCD_KPM_STATUS_LENGTH_MISMATCH,
    TCD_KPM_STATUS_NO_VALUE,
    TCD_KPM_STATUS_UNSUPPORTED_DESCRIPTOR,
    TCD_KPM_STATUS_UNSUPPORTED_VALUE_TYPE,
    TCD_KPM_STATUS_UNSUPPORTED_UE_ID,
    TCD_KPM_STATUS_UNKNOWN_MESSAGE_FORMAT,
    TCD_KPM_STATUS_INVALID_INPUT
} tcd_kpm_structural_status_t;

typedef enum {
    TCD_KPM_DESCRIPTOR_UNKNOWN = 0,
    TCD_KPM_DESCRIPTOR_NAME,
    TCD_KPM_DESCRIPTOR_ID
} tcd_kpm_descriptor_type_t;

typedef enum {
    TCD_KPM_VALUE_UNKNOWN = 0,
    TCD_KPM_VALUE_INTEGER,
    TCD_KPM_VALUE_REAL,
    TCD_KPM_VALUE_NO_VALUE
} tcd_kpm_value_type_t;

typedef enum {
    TCD_KPM_UE_ID_UNKNOWN = 0,
    TCD_KPM_UE_ID_GNB,
    TCD_KPM_UE_ID_GNB_DU,
    TCD_KPM_UE_ID_GNB_CU_UP
} tcd_kpm_ue_id_type_t;

typedef struct {
    tcd_kpm_ue_id_type_t type;
    uint32_t raw_type;

    bool amf_ue_ngap_id_present;
    uint64_t amf_ue_ngap_id;

    bool gnb_cu_ue_f1ap_present;
    uint32_t gnb_cu_ue_f1ap;

    bool gnb_cu_cp_ue_e1ap_present;
    uint32_t gnb_cu_cp_ue_e1ap;

    bool ran_ue_id_present;
    uint64_t ran_ue_id;
} tcd_kpm_ue_id_t;

typedef struct {
    tcd_kpm_descriptor_type_t type;
    uint32_t raw_type;

    bool measurement_name_present;
    size_t measurement_name_length;
    bool measurement_name_truncated;
    char measurement_name[TCD_KPM_MEASUREMENT_NAME_CAPACITY];

    bool measurement_id_present;
    uint32_t measurement_id;
} tcd_kpm_measurement_descriptor_t;

typedef struct {
    tcd_kpm_value_type_t type;
    uint32_t raw_type;

    union {
        int64_t integer_value;
        double real_value;
    } data;
} tcd_kpm_value_t;

typedef struct {
    uint64_t indication_sequence;
    uint64_t logical_subscription_id;

    int64_t receive_timestamp_unix_ns;
    uint64_t kpm_header_timestamp_raw;

    uint32_t message_format_raw;
    uint32_t e2_node_type_raw;

    char e2_node_id[TCD_KPM_NODE_ID_CAPACITY];
    uint32_t ue_report_count;
} tcd_kpm_indication_context_t;

typedef struct {
    tcd_kpm_indication_context_t indication;

    uint32_t ue_report_index;
    tcd_kpm_ue_id_t ue_id;

    uint32_t meas_data_index;
    uint32_t meas_record_index;
    uint32_t meas_info_index;

    uint32_t meas_data_lst_len;
    uint32_t meas_info_lst_len;
    uint32_t meas_record_len;

    tcd_kpm_measurement_descriptor_t descriptor;
    tcd_kpm_value_t value;

    bool incomplete_flag_present;
    bool incomplete_flag;

    tcd_kpm_structural_status_t structural_status;
} tcd_kpm_measurement_record_t;

void tcd_kpm_measurement_record_reset(
    tcd_kpm_measurement_record_t *record
);

const char *tcd_kpm_structural_status_string(
    tcd_kpm_structural_status_t status
);

const char *tcd_kpm_descriptor_type_string(
    tcd_kpm_descriptor_type_t type
);

const char *tcd_kpm_value_type_string(
    tcd_kpm_value_type_t type
);

#endif
