#include "tcd_kpm_collector/canonical_serialize.h"

#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    char *data;
    size_t capacity;
    size_t length;
    bool overflow;
} tcd_kpm_builder_t;

static void builder_init(tcd_kpm_builder_t *builder, char *data, size_t capacity)
{
    builder->data = data;
    builder->capacity = capacity;
    builder->length = 0U;
    builder->overflow = false;
    if (data != NULL && capacity > 0U) {
        data[0] = '\0';
    }
}

static void builder_append_bytes(
    tcd_kpm_builder_t *builder,
    const char *bytes,
    size_t length)
{
    size_t available = 0U;
    size_t copy_length = 0U;

    if (builder->data != NULL && builder->capacity > 0U &&
        builder->length < builder->capacity - 1U) {
        available = (builder->capacity - 1U) - builder->length;
        copy_length = length < available ? length : available;
        if (copy_length > 0U) {
            memcpy(builder->data + builder->length, bytes, copy_length);
        }
    }

    if (length > SIZE_MAX - builder->length) {
        builder->overflow = true;
        builder->length = SIZE_MAX;
    } else {
        builder->length += length;
    }

    if (copy_length < length) {
        builder->overflow = true;
    }

    if (builder->data != NULL && builder->capacity > 0U) {
        const size_t terminator =
            builder->length < builder->capacity ?
                builder->length : builder->capacity - 1U;
        builder->data[terminator] = '\0';
    }
}

static void builder_append_literal(tcd_kpm_builder_t *builder, const char *text)
{
    builder_append_bytes(builder, text, strlen(text));
}

static void builder_append_u32(tcd_kpm_builder_t *builder, uint32_t value)
{
    char buffer[32];
    const int length = snprintf(buffer, sizeof(buffer), "%u", (unsigned)value);
    if (length < 0 || (size_t)length >= sizeof(buffer)) {
        builder->overflow = true;
        return;
    }
    builder_append_bytes(builder, buffer, (size_t)length);
}

static void builder_append_u64(tcd_kpm_builder_t *builder, uint64_t value)
{
    char buffer[32];
    const int length = snprintf(
        buffer,
        sizeof(buffer),
        "%llu",
        (unsigned long long)value);
    if (length < 0 || (size_t)length >= sizeof(buffer)) {
        builder->overflow = true;
        return;
    }
    builder_append_bytes(builder, buffer, (size_t)length);
}

static void builder_append_i64(tcd_kpm_builder_t *builder, int64_t value)
{
    char buffer[32];
    const int length = snprintf(
        buffer,
        sizeof(buffer),
        "%lld",
        (long long)value);
    if (length < 0 || (size_t)length >= sizeof(buffer)) {
        builder->overflow = true;
        return;
    }
    builder_append_bytes(builder, buffer, (size_t)length);
}

static void builder_append_double(tcd_kpm_builder_t *builder, double value)
{
    char buffer[64];
    const int length = snprintf(buffer, sizeof(buffer), "%.17g", value);
    if (length < 0 || (size_t)length >= sizeof(buffer)) {
        builder->overflow = true;
        return;
    }
    builder_append_bytes(builder, buffer, (size_t)length);
}

static bool bounded_string_valid(const char *value, size_t capacity)
{
    const unsigned char *bytes = (const unsigned char *)value;
    size_t length = 0U;
    size_t index = 0U;

    while (length < capacity && bytes[length] != 0U) {
        ++length;
    }
    if (length == capacity) {
        return false;
    }

    while (index < length) {
        const unsigned char lead = bytes[index];
        uint32_t codepoint = 0U;
        size_t continuation_count = 0U;
        size_t offset = 0U;

        if (lead <= 0x7FU) {
            ++index;
            continue;
        }
        if (lead >= 0xC2U && lead <= 0xDFU) {
            codepoint = lead & 0x1FU;
            continuation_count = 1U;
        } else if (lead >= 0xE0U && lead <= 0xEFU) {
            codepoint = lead & 0x0FU;
            continuation_count = 2U;
        } else if (lead >= 0xF0U && lead <= 0xF4U) {
            codepoint = lead & 0x07U;
            continuation_count = 3U;
        } else {
            return false;
        }

        if (continuation_count > length - index - 1U) {
            return false;
        }
        for (offset = 1U; offset <= continuation_count; ++offset) {
            const unsigned char next = bytes[index + offset];
            if ((next & 0xC0U) != 0x80U) {
                return false;
            }
            codepoint = (codepoint << 6U) | (uint32_t)(next & 0x3FU);
        }
        if ((continuation_count == 1U && codepoint < 0x80U) ||
            (continuation_count == 2U && codepoint < 0x800U) ||
            (continuation_count == 3U && codepoint < 0x10000U) ||
            codepoint > 0x10FFFFU ||
            (codepoint >= 0xD800U && codepoint <= 0xDFFFU)) {
            return false;
        }
        index += continuation_count + 1U;
    }

    return true;
}

static bool optional_string_valid(bool present, const char *value, size_t capacity)
{
    return !present || bounded_string_valid(value, capacity);
}

static const char *record_kind_name(tcd_kpm_record_kind_t value)
{
    switch (value) {
    case TCD_KPM_RECORD_KIND_MEASUREMENT:
        return "measurement";
    case TCD_KPM_RECORD_KIND_DIAGNOSTIC:
        return "diagnostic";
    default:
        return NULL;
    }
}

static const char *structural_status_name(tcd_kpm_structural_status_t value)
{
    switch (value) {
    case TCD_KPM_STRUCTURAL_STATUS_OK:
        return "ok";
    case TCD_KPM_STRUCTURAL_STATUS_NO_VALUE:
        return "no_value";
    case TCD_KPM_STRUCTURAL_STATUS_LENGTH_MISMATCH:
        return "length_mismatch";
    case TCD_KPM_STRUCTURAL_STATUS_INVALID_INPUT:
        return "invalid_input";
    case TCD_KPM_STRUCTURAL_STATUS_UNSUPPORTED_UE_ID:
        return "unsupported_ue_id";
    case TCD_KPM_STRUCTURAL_STATUS_UNSUPPORTED_DESCRIPTOR:
        return "unsupported_descriptor";
    case TCD_KPM_STRUCTURAL_STATUS_UNSUPPORTED_VALUE_TYPE:
        return "unsupported_value_type";
    default:
        return NULL;
    }
}

static const char *descriptor_type_name(tcd_kpm_descriptor_type_t value)
{
    switch (value) {
    case TCD_KPM_DESCRIPTOR_NAME:
        return "name";
    case TCD_KPM_DESCRIPTOR_ID:
        return "id";
    case TCD_KPM_DESCRIPTOR_UNKNOWN:
        return "unknown";
    default:
        return NULL;
    }
}

static const char *value_type_name(tcd_kpm_value_type_t value)
{
    switch (value) {
    case TCD_KPM_VALUE_INTEGER:
        return "integer";
    case TCD_KPM_VALUE_REAL:
        return "real";
    case TCD_KPM_VALUE_NO_VALUE:
        return "no_value";
    case TCD_KPM_VALUE_UNKNOWN:
        return "unknown";
    default:
        return NULL;
    }
}

void tcd_kpm_canonical_record_init(tcd_kpm_canonical_record_t *record)
{
    if (record == NULL) {
        return;
    }
    memset(record, 0, sizeof(*record));
    record->record_kind = TCD_KPM_RECORD_KIND_INVALID;
    record->structural_status = TCD_KPM_STRUCTURAL_STATUS_INVALID;
    record->descriptor_type = TCD_KPM_DESCRIPTOR_UNKNOWN;
    record->value_type = TCD_KPM_VALUE_UNKNOWN;
}

static tcd_kpm_serialize_result_t invalid_record(
    const char **reason,
    const char *value)
{
    if (reason != NULL) {
        *reason = value;
    }
    return TCD_KPM_SERIALIZE_INVALID_RECORD;
}
tcd_kpm_serialize_result_t tcd_kpm_canonical_record_validate(
    const tcd_kpm_canonical_record_t *record,
    const char **reason)
{
    if (reason != NULL) {
        *reason = NULL;
    }
    if (record == NULL) {
        return TCD_KPM_SERIALIZE_INVALID_ARGUMENT;
    }
    if (record_kind_name(record->record_kind) == NULL) {
        return invalid_record(reason, "invalid_record_kind");
    }
    if (structural_status_name(record->structural_status) == NULL) {
        return invalid_record(reason, "invalid_structural_status");
    }
    if (descriptor_type_name(record->descriptor_type) == NULL) {
        return invalid_record(reason, "invalid_descriptor_type");
    }
    if (value_type_name(record->value_type) == NULL) {
        return invalid_record(reason, "invalid_value_type");
    }
    if (!bounded_string_valid(
            record->ue_id_type,
            TCD_KPM_UE_ID_TYPE_CAPACITY) ||
        record->ue_id_type[0] == '\0') {
        return invalid_record(reason, "invalid_ue_id_type");
    }
    if (!optional_string_valid(
            record->has_node_type,
            record->node_type,
            TCD_KPM_NODE_TYPE_CAPACITY) ||
        !optional_string_valid(
            record->has_node_id,
            record->node_id,
            TCD_KPM_NODE_ID_CAPACITY) ||
        !optional_string_valid(
            record->has_ue_id_value,
            record->ue_id_value,
            TCD_KPM_UE_ID_VALUE_CAPACITY) ||
        !optional_string_valid(
            record->has_measurement_name,
            record->measurement_name,
            TCD_KPM_MEASUREMENT_NAME_CAPACITY) ||
        !optional_string_valid(
            record->has_diagnostic_code,
            record->diagnostic_code,
            TCD_KPM_DIAGNOSTIC_CODE_CAPACITY) ||
        !optional_string_valid(
            record->has_diagnostic_message,
            record->diagnostic_message,
            TCD_KPM_DIAGNOSTIC_MESSAGE_CAPACITY)) {
        return invalid_record(reason, "invalid_utf8_or_unterminated_string");
    }
    if (!record->incomplete_flag_present && record->incomplete_flag) {
        return invalid_record(reason, "incomplete_flag_without_presence");
    }

    if (record->record_kind == TCD_KPM_RECORD_KIND_DIAGNOSTIC) {
        if (record->has_meas_info_index || record->has_meas_record_index) {
            return invalid_record(reason, "diagnostic_has_pair_indexes");
        }
        if (record->descriptor_type != TCD_KPM_DESCRIPTOR_UNKNOWN ||
            record->value_type != TCD_KPM_VALUE_UNKNOWN) {
            return invalid_record(reason, "diagnostic_has_descriptor_or_value_type");
        }
        if (record->has_measurement_name || record->has_measurement_id ||
            record->has_integer_value || record->has_real_value) {
            return invalid_record(reason, "diagnostic_has_measurement_value");
        }
        if (!record->has_diagnostic_code || record->diagnostic_code[0] == '\0') {
            return invalid_record(reason, "diagnostic_code_missing");
        }
        if (record->structural_status == TCD_KPM_STRUCTURAL_STATUS_OK ||
            record->structural_status == TCD_KPM_STRUCTURAL_STATUS_NO_VALUE) {
            return invalid_record(reason, "diagnostic_has_measurement_status");
        }
        if (record->structural_status ==
                TCD_KPM_STRUCTURAL_STATUS_LENGTH_MISMATCH &&
            record->meas_info_lst_len == record->meas_record_len) {
            return invalid_record(reason, "length_mismatch_lengths_equal");
        }
    } else {
        if (!record->has_meas_info_index || !record->has_meas_record_index ||
            record->meas_info_index != record->meas_record_index) {
            return invalid_record(reason, "measurement_pair_indexes_invalid");
        }
        if (record->structural_status != TCD_KPM_STRUCTURAL_STATUS_OK &&
            record->structural_status != TCD_KPM_STRUCTURAL_STATUS_NO_VALUE) {
            return invalid_record(reason, "measurement_has_diagnostic_status");
        }
        if (record->has_diagnostic_code || record->has_diagnostic_message) {
            return invalid_record(reason, "measurement_has_diagnostic_fields");
        }

        switch (record->descriptor_type) {
        case TCD_KPM_DESCRIPTOR_NAME:
            if (!record->has_measurement_name ||
                record->measurement_name[0] == '\0' ||
                record->has_measurement_id) {
                return invalid_record(reason, "name_descriptor_invalid");
            }
            break;
        case TCD_KPM_DESCRIPTOR_ID:
            if (!record->has_measurement_id || record->has_measurement_name) {
                return invalid_record(reason, "id_descriptor_invalid");
            }
            break;
        default:
            return invalid_record(reason, "measurement_descriptor_unknown");
        }

        switch (record->value_type) {
        case TCD_KPM_VALUE_INTEGER:
            if (!record->has_integer_value || record->has_real_value) {
                return invalid_record(reason, "integer_value_invalid");
            }
            if (record->structural_status != TCD_KPM_STRUCTURAL_STATUS_OK) {
                return invalid_record(reason, "integer_status_invalid");
            }
            break;
        case TCD_KPM_VALUE_REAL:
            if (!record->has_real_value || record->has_integer_value ||
                !isfinite(record->real_value)) {
                return invalid_record(reason, "real_value_invalid");
            }
            if (record->structural_status != TCD_KPM_STRUCTURAL_STATUS_OK) {
                return invalid_record(reason, "real_status_invalid");
            }
            break;
        case TCD_KPM_VALUE_NO_VALUE:
            if (record->has_integer_value || record->has_real_value ||
                record->structural_status != TCD_KPM_STRUCTURAL_STATUS_NO_VALUE) {
                return invalid_record(reason, "no_value_invalid");
            }
            break;
        default:
            return invalid_record(reason, "measurement_value_unknown");
        }
    }

    return TCD_KPM_SERIALIZE_OK;
}

const char *tcd_kpm_serialize_result_name(tcd_kpm_serialize_result_t result)
{
    switch (result) {
    case TCD_KPM_SERIALIZE_OK:
        return "ok";
    case TCD_KPM_SERIALIZE_INVALID_ARGUMENT:
        return "invalid_argument";
    case TCD_KPM_SERIALIZE_INVALID_RECORD:
        return "invalid_record";
    case TCD_KPM_SERIALIZE_BUFFER_TOO_SMALL:
        return "buffer_too_small";
    default:
        return "unknown";
    }
}

static tcd_kpm_serialize_result_t builder_result(
    tcd_kpm_builder_t *builder,
    size_t *required_length)
{
    if (required_length != NULL) {
        *required_length = builder->length;
    }
    return builder->overflow ?
        TCD_KPM_SERIALIZE_BUFFER_TOO_SMALL : TCD_KPM_SERIALIZE_OK;
}

static void csv_append_string(tcd_kpm_builder_t *builder, const char *value)
{
    const unsigned char *cursor = (const unsigned char *)value;
    builder_append_literal(builder, "\"");
    while (*cursor != 0U) {
        if (*cursor == (unsigned char)'\"') {
            builder_append_literal(builder, "\"\"");
        } else {
            const char byte = (char)*cursor;
            builder_append_bytes(builder, &byte, 1U);
        }
        ++cursor;
    }
    builder_append_literal(builder, "\"");
}

static void csv_separator(tcd_kpm_builder_t *builder)
{
    builder_append_literal(builder, ",");
}

static void csv_append_optional_string(
    tcd_kpm_builder_t *builder,
    bool present,
    const char *value)
{
    if (present) {
        csv_append_string(builder, value);
    }
}

static void csv_append_optional_u32(
    tcd_kpm_builder_t *builder,
    bool present,
    uint32_t value)
{
    if (present) {
        builder_append_u32(builder, value);
    }
}

static void csv_append_optional_u64(
    tcd_kpm_builder_t *builder,
    bool present,
    uint64_t value)
{
    if (present) {
        builder_append_u64(builder, value);
    }
}

static void csv_append_optional_bool(
    tcd_kpm_builder_t *builder,
    bool present,
    bool value)
{
    if (present) {
        builder_append_literal(builder, value ? "true" : "false");
    }
}

static void csv_append_optional_i64(
    tcd_kpm_builder_t *builder,
    bool present,
    int64_t value)
{
    if (present) {
        builder_append_i64(builder, value);
    }
}

static void csv_append_optional_double(
    tcd_kpm_builder_t *builder,
    bool present,
    double value)
{
    if (present) {
        builder_append_double(builder, value);
    }
}

static const char csv_header[] =
    "schema_version,record_kind,indication_sequence,receive_timestamp_us,"
    "kpm_header_timestamp_us,message_format,node_type,node_id,"
    "ue_report_index,ue_id_type,ue_id_value,meas_data_index,"
    "meas_info_index,meas_record_index,meas_data_lst_len,"
    "meas_info_lst_len,meas_record_len,incomplete_flag_present,"
    "incomplete_flag,structural_status,descriptor_type,measurement_name,"
    "measurement_id,value_type,integer_value,real_value,diagnostic_code,"
    "diagnostic_message\n";

tcd_kpm_serialize_result_t tcd_kpm_serialize_csv_header(
    char *destination,
    size_t destination_capacity,
    size_t *required_length)
{
    tcd_kpm_builder_t builder;
    if (destination == NULL && destination_capacity != 0U) {
        return TCD_KPM_SERIALIZE_INVALID_ARGUMENT;
    }
    builder_init(&builder, destination, destination_capacity);
    builder_append_literal(&builder, csv_header);
    return builder_result(&builder, required_length);
}
tcd_kpm_serialize_result_t tcd_kpm_serialize_csv_record(
    const tcd_kpm_canonical_record_t *record,
    char *destination,
    size_t destination_capacity,
    size_t *required_length)
{
    tcd_kpm_builder_t builder;
    const char *reason = NULL;
    const tcd_kpm_serialize_result_t validation =
        tcd_kpm_canonical_record_validate(record, &reason);

    (void)reason;
    if (destination == NULL && destination_capacity != 0U) {
        return TCD_KPM_SERIALIZE_INVALID_ARGUMENT;
    }
    if (validation != TCD_KPM_SERIALIZE_OK) {
        return validation;
    }

    builder_init(&builder, destination, destination_capacity);
    csv_append_string(&builder, TCD_KPM_CANONICAL_SCHEMA_VERSION);
    csv_separator(&builder);
    csv_append_string(&builder, record_kind_name(record->record_kind));
    csv_separator(&builder);
    builder_append_u64(&builder, record->indication_sequence);
    csv_separator(&builder);
    builder_append_u64(&builder, record->receive_timestamp_us);
    csv_separator(&builder);
    csv_append_optional_u64(
        &builder,
        record->has_kpm_header_timestamp_us,
        record->kpm_header_timestamp_us);
    csv_separator(&builder);
    builder_append_u32(&builder, record->message_format);
    csv_separator(&builder);
    csv_append_optional_string(&builder, record->has_node_type, record->node_type);
    csv_separator(&builder);
    csv_append_optional_string(&builder, record->has_node_id, record->node_id);
    csv_separator(&builder);
    csv_append_optional_u32(
        &builder,
        record->has_ue_report_index,
        record->ue_report_index);
    csv_separator(&builder);
    csv_append_string(&builder, record->ue_id_type);
    csv_separator(&builder);
    csv_append_optional_string(
        &builder,
        record->has_ue_id_value,
        record->ue_id_value);
    csv_separator(&builder);
    csv_append_optional_u32(
        &builder,
        record->has_meas_data_index,
        record->meas_data_index);
    csv_separator(&builder);
    csv_append_optional_u32(
        &builder,
        record->has_meas_info_index,
        record->meas_info_index);
    csv_separator(&builder);
    csv_append_optional_u32(
        &builder,
        record->has_meas_record_index,
        record->meas_record_index);
    csv_separator(&builder);
    builder_append_u32(&builder, record->meas_data_lst_len);
    csv_separator(&builder);
    builder_append_u32(&builder, record->meas_info_lst_len);
    csv_separator(&builder);
    builder_append_u32(&builder, record->meas_record_len);
    csv_separator(&builder);
    builder_append_literal(
        &builder,
        record->incomplete_flag_present ? "true" : "false");
    csv_separator(&builder);
    csv_append_optional_bool(
        &builder,
        record->incomplete_flag_present,
        record->incomplete_flag);
    csv_separator(&builder);
    csv_append_string(
        &builder,
        structural_status_name(record->structural_status));
    csv_separator(&builder);
    csv_append_string(&builder, descriptor_type_name(record->descriptor_type));
    csv_separator(&builder);
    csv_append_optional_string(
        &builder,
        record->has_measurement_name,
        record->measurement_name);
    csv_separator(&builder);
    csv_append_optional_u32(
        &builder,
        record->has_measurement_id,
        record->measurement_id);
    csv_separator(&builder);
    csv_append_string(&builder, value_type_name(record->value_type));
    csv_separator(&builder);
    csv_append_optional_i64(
        &builder,
        record->has_integer_value,
        record->integer_value);
    csv_separator(&builder);
    csv_append_optional_double(
        &builder,
        record->has_real_value,
        record->real_value);
    csv_separator(&builder);
    csv_append_optional_string(
        &builder,
        record->has_diagnostic_code,
        record->diagnostic_code);
    csv_separator(&builder);
    csv_append_optional_string(
        &builder,
        record->has_diagnostic_message,
        record->diagnostic_message);
    builder_append_literal(&builder, "\n");

    return builder_result(&builder, required_length);
}

static void json_append_string(tcd_kpm_builder_t *builder, const char *value)
{
    static const char hex[] = "0123456789abcdef";
    const unsigned char *cursor = (const unsigned char *)value;

    builder_append_literal(builder, "\"");
    while (*cursor != 0U) {
        const unsigned char byte = *cursor;
        switch (byte) {
        case (unsigned char)'\"':
            builder_append_literal(builder, "\\\"");
            break;
        case (unsigned char)'\\':
            builder_append_literal(builder, "\\\\");
            break;
        case (unsigned char)'\b':
            builder_append_literal(builder, "\\b");
            break;
        case (unsigned char)'\f':
            builder_append_literal(builder, "\\f");
            break;
        case (unsigned char)'\n':
            builder_append_literal(builder, "\\n");
            break;
        case (unsigned char)'\r':
            builder_append_literal(builder, "\\r");
            break;
        case (unsigned char)'\t':
            builder_append_literal(builder, "\\t");
            break;
        default:
            if (byte < 0x20U) {
                char escaped[6] = {'\\', 'u', '0', '0', '0', '0'};
                escaped[4] = hex[(byte >> 4U) & 0x0FU];
                escaped[5] = hex[byte & 0x0FU];
                builder_append_bytes(builder, escaped, sizeof(escaped));
            } else {
                const char character = (char)byte;
                builder_append_bytes(builder, &character, 1U);
            }
            break;
        }
        ++cursor;
    }
    builder_append_literal(builder, "\"");
}

static void json_key(tcd_kpm_builder_t *builder, const char *key, bool *first)
{
    if (!*first) {
        builder_append_literal(builder, ",");
    }
    *first = false;
    json_append_string(builder, key);
    builder_append_literal(builder, ":");
}

static void json_optional_string(
    tcd_kpm_builder_t *builder,
    bool present,
    const char *value)
{
    if (present) {
        json_append_string(builder, value);
    } else {
        builder_append_literal(builder, "null");
    }
}

static void json_optional_u32(
    tcd_kpm_builder_t *builder,
    bool present,
    uint32_t value)
{
    if (present) {
        builder_append_u32(builder, value);
    } else {
        builder_append_literal(builder, "null");
    }
}

static void json_optional_u64(
    tcd_kpm_builder_t *builder,
    bool present,
    uint64_t value)
{
    if (present) {
        builder_append_u64(builder, value);
    } else {
        builder_append_literal(builder, "null");
    }
}

static void json_optional_bool(
    tcd_kpm_builder_t *builder,
    bool present,
    bool value)
{
    if (present) {
        builder_append_literal(builder, value ? "true" : "false");
    } else {
        builder_append_literal(builder, "null");
    }
}

static void json_optional_i64(
    tcd_kpm_builder_t *builder,
    bool present,
    int64_t value)
{
    if (present) {
        builder_append_i64(builder, value);
    } else {
        builder_append_literal(builder, "null");
    }
}

static void json_optional_double(
    tcd_kpm_builder_t *builder,
    bool present,
    double value)
{
    if (present) {
        builder_append_double(builder, value);
    } else {
        builder_append_literal(builder, "null");
    }
}
tcd_kpm_serialize_result_t tcd_kpm_serialize_jsonl_record(
    const tcd_kpm_canonical_record_t *record,
    char *destination,
    size_t destination_capacity,
    size_t *required_length)
{
    tcd_kpm_builder_t builder;
    bool first = true;
    const char *reason = NULL;
    const tcd_kpm_serialize_result_t validation =
        tcd_kpm_canonical_record_validate(record, &reason);

    (void)reason;
    if (destination == NULL && destination_capacity != 0U) {
        return TCD_KPM_SERIALIZE_INVALID_ARGUMENT;
    }
    if (validation != TCD_KPM_SERIALIZE_OK) {
        return validation;
    }

    builder_init(&builder, destination, destination_capacity);
    builder_append_literal(&builder, "{");

    json_key(&builder, "schema_version", &first);
    json_append_string(&builder, TCD_KPM_CANONICAL_SCHEMA_VERSION);
    json_key(&builder, "record_kind", &first);
    json_append_string(&builder, record_kind_name(record->record_kind));
    json_key(&builder, "indication_sequence", &first);
    builder_append_u64(&builder, record->indication_sequence);
    json_key(&builder, "receive_timestamp_us", &first);
    builder_append_u64(&builder, record->receive_timestamp_us);
    json_key(&builder, "kpm_header_timestamp_us", &first);
    json_optional_u64(
        &builder,
        record->has_kpm_header_timestamp_us,
        record->kpm_header_timestamp_us);
    json_key(&builder, "message_format", &first);
    builder_append_u32(&builder, record->message_format);
    json_key(&builder, "node_type", &first);
    json_optional_string(&builder, record->has_node_type, record->node_type);
    json_key(&builder, "node_id", &first);
    json_optional_string(&builder, record->has_node_id, record->node_id);
    json_key(&builder, "ue_report_index", &first);
    json_optional_u32(
        &builder,
        record->has_ue_report_index,
        record->ue_report_index);
    json_key(&builder, "ue_id_type", &first);
    json_append_string(&builder, record->ue_id_type);
    json_key(&builder, "ue_id_value", &first);
    json_optional_string(
        &builder,
        record->has_ue_id_value,
        record->ue_id_value);
    json_key(&builder, "meas_data_index", &first);
    json_optional_u32(
        &builder,
        record->has_meas_data_index,
        record->meas_data_index);
    json_key(&builder, "meas_info_index", &first);
    json_optional_u32(
        &builder,
        record->has_meas_info_index,
        record->meas_info_index);
    json_key(&builder, "meas_record_index", &first);
    json_optional_u32(
        &builder,
        record->has_meas_record_index,
        record->meas_record_index);
    json_key(&builder, "meas_data_lst_len", &first);
    builder_append_u32(&builder, record->meas_data_lst_len);
    json_key(&builder, "meas_info_lst_len", &first);
    builder_append_u32(&builder, record->meas_info_lst_len);
    json_key(&builder, "meas_record_len", &first);
    builder_append_u32(&builder, record->meas_record_len);
    json_key(&builder, "incomplete_flag_present", &first);
    builder_append_literal(
        &builder,
        record->incomplete_flag_present ? "true" : "false");
    json_key(&builder, "incomplete_flag", &first);
    json_optional_bool(
        &builder,
        record->incomplete_flag_present,
        record->incomplete_flag);
    json_key(&builder, "structural_status", &first);
    json_append_string(
        &builder,
        structural_status_name(record->structural_status));
    json_key(&builder, "descriptor_type", &first);
    json_append_string(&builder, descriptor_type_name(record->descriptor_type));
    json_key(&builder, "measurement_name", &first);
    json_optional_string(
        &builder,
        record->has_measurement_name,
        record->measurement_name);
    json_key(&builder, "measurement_id", &first);
    json_optional_u32(
        &builder,
        record->has_measurement_id,
        record->measurement_id);
    json_key(&builder, "value_type", &first);
    json_append_string(&builder, value_type_name(record->value_type));
    json_key(&builder, "integer_value", &first);
    json_optional_i64(
        &builder,
        record->has_integer_value,
        record->integer_value);
    json_key(&builder, "real_value", &first);
    json_optional_double(
        &builder,
        record->has_real_value,
        record->real_value);
    json_key(&builder, "diagnostic_code", &first);
    json_optional_string(
        &builder,
        record->has_diagnostic_code,
        record->diagnostic_code);
    json_key(&builder, "diagnostic_message", &first);
    json_optional_string(
        &builder,
        record->has_diagnostic_message,
        record->diagnostic_message);

    builder_append_literal(&builder, "}\n");
    return builder_result(&builder, required_length);
}
