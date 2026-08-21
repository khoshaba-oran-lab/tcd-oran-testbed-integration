/*
 * Licensed to the OpenAirInterface (OAI) Software Alliance under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The OpenAirInterface Software Alliance licenses this file to You under
 * the OAI Public License, Version 1.1  (the "License"); you may not use this file
 * except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.openairinterface.org/?page_id=698
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *-------------------------------------------------------------------------------
 * For more information about the OpenAirInterface (OAI) Software Alliance:
 *      contact@openairinterface.org
 */

#include "../../../../src/xApp/e42_xapp_api.h"
#include "../../../../src/sm/rc_sm/ie/ir/ran_param_struct.h"
#include "../../../../src/sm/rc_sm/ie/ir/ran_param_list.h"
#include "../../../../src/util/time_now_us.h"
#include "../../../../src/util/alg_ds/ds/lock_guard/lock_guard.h"
#include "../../../../src/sm/rc_sm/rc_sm_id.h"
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

static
int sci_oran_prompt12_max_prb_ratio_pct(void)
{
  const char* raw = getenv("SCI_ORAN_MAX_PRB_RATIO");

  if (raw == NULL || raw[0] == '\0') {
    fprintf(stderr,
            "[xApp]: SCI_ORAN_MAX_PRB_RATIO is required\n");
    exit(EXIT_FAILURE);
  }

  errno = 0;
  char* end = NULL;
  long value = strtol(raw, &end, 10);

  if (errno != 0 ||
      end == raw ||
      *end != '\0' ||
      (value != 25 &&
       value != 50 &&
       value != 75 &&
       value != 100)) {
    fprintf(stderr,
            "[xApp]: invalid SCI_ORAN_MAX_PRB_RATIO=%s; "
            "allowed values are 25,50,75,100\n",
            raw);
    exit(EXIT_FAILURE);
  }

  return (int)value;
}

static
e2sm_rc_ctrl_hdr_frmt_1_t gen_rc_ctrl_hdr_frmt_1(ue_id_e2sm_t ue_id, uint32_t ric_style_type, uint16_t ctrl_act_id)
{
  e2sm_rc_ctrl_hdr_frmt_1_t dst = {0};

  // 6.2.2.6
  dst.ue_id = cp_ue_id_e2sm(&ue_id);

  dst.ric_style_type = ric_style_type;
  dst.ctrl_act_id = ctrl_act_id;

  return dst;
}

static
e2sm_rc_ctrl_hdr_t gen_rc_ctrl_hdr(e2sm_rc_ctrl_hdr_e hdr_frmt, ue_id_e2sm_t ue_id, uint32_t ric_style_type, uint16_t ctrl_act_id)
{
  e2sm_rc_ctrl_hdr_t dst = {0};

  if (hdr_frmt == FORMAT_1_E2SM_RC_CTRL_HDR) {
    dst.format = FORMAT_1_E2SM_RC_CTRL_HDR;
    dst.frmt_1 = gen_rc_ctrl_hdr_frmt_1(ue_id, ric_style_type, ctrl_act_id);
  } else {
    assert(0!=0 && "not implemented the fill func for this ctrl hdr frmt");
  }

  return dst;
}

static
void gen_rrm_policy_ratio_group(
    lst_ran_param_t* RRM_Policy_Ratio_Group,
    int max_prb_ratio_pct)
{
  // Prompt12 parameterized runtime actuator.
  // PLMN=00101, SST=1, MIN_PRB=0.
  // MAX_PRB ratio is explicitly selected from {25,50,75,100}.

  RRM_Policy_Ratio_Group->ran_param_struct.sz_ran_param_struct = 3;
  RRM_Policy_Ratio_Group->ran_param_struct.ran_param_struct =
      calloc(3, sizeof(seq_ran_param_t));
  assert(RRM_Policy_Ratio_Group->ran_param_struct.ran_param_struct != NULL &&
         "Memory exhausted");

  seq_ran_param_t* RRM_Policy =
      &RRM_Policy_Ratio_Group->ran_param_struct.ran_param_struct[0];
  RRM_Policy->ran_param_id = RRM_Policy_8_4_3_6;
  RRM_Policy->ran_param_val.type = STRUCTURE_RAN_PARAMETER_VAL_TYPE;
  RRM_Policy->ran_param_val.strct = calloc(1, sizeof(ran_param_struct_t));
  assert(RRM_Policy->ran_param_val.strct != NULL && "Memory exhausted");

  RRM_Policy->ran_param_val.strct->sz_ran_param_struct = 1;
  RRM_Policy->ran_param_val.strct->ran_param_struct =
      calloc(1, sizeof(seq_ran_param_t));
  assert(RRM_Policy->ran_param_val.strct->ran_param_struct != NULL &&
         "Memory exhausted");

  seq_ran_param_t* RRM_Policy_Member_List =
      &RRM_Policy->ran_param_val.strct->ran_param_struct[0];
  RRM_Policy_Member_List->ran_param_id = RRM_Policy_Member_List_8_4_3_6;
  RRM_Policy_Member_List->ran_param_val.type = LIST_RAN_PARAMETER_VAL_TYPE;
  RRM_Policy_Member_List->ran_param_val.lst =
      calloc(1, sizeof(ran_param_list_t));
  assert(RRM_Policy_Member_List->ran_param_val.lst != NULL &&
         "Memory exhausted");

  RRM_Policy_Member_List->ran_param_val.lst->sz_lst_ran_param = 1;
  RRM_Policy_Member_List->ran_param_val.lst->lst_ran_param =
      calloc(1, sizeof(lst_ran_param_t));
  assert(RRM_Policy_Member_List->ran_param_val.lst->lst_ran_param != NULL &&
         "Memory exhausted");

  lst_ran_param_t* RRM_Policy_Member =
      &RRM_Policy_Member_List->ran_param_val.lst->lst_ran_param[0];

  RRM_Policy_Member->ran_param_struct.sz_ran_param_struct = 2;
  RRM_Policy_Member->ran_param_struct.ran_param_struct =
      calloc(2, sizeof(seq_ran_param_t));
  assert(RRM_Policy_Member->ran_param_struct.ran_param_struct != NULL &&
         "Memory exhausted");

  seq_ran_param_t* PLMN_Identity =
      &RRM_Policy_Member->ran_param_struct.ran_param_struct[0];
  PLMN_Identity->ran_param_id = PLMN_Identity_8_4_3_6;
  PLMN_Identity->ran_param_val.type =
      ELEMENT_KEY_FLAG_FALSE_RAN_PARAMETER_VAL_TYPE;
  PLMN_Identity->ran_param_val.flag_false =
      calloc(1, sizeof(ran_parameter_value_t));
  assert(PLMN_Identity->ran_param_val.flag_false != NULL &&
         "Memory exhausted");

  PLMN_Identity->ran_param_val.flag_false->type =
      OCTET_STRING_RAN_PARAMETER_VALUE;

  const uint8_t plmn_00101[3] = {0x00, 0xf1, 0x10};

  PLMN_Identity->ran_param_val.flag_false->octet_str_ran.len =
      sizeof(plmn_00101);
  PLMN_Identity->ran_param_val.flag_false->octet_str_ran.buf =
      calloc(sizeof(plmn_00101), sizeof(uint8_t));
  assert(PLMN_Identity->ran_param_val.flag_false->octet_str_ran.buf != NULL &&
         "Memory exhausted");

  memcpy(
      PLMN_Identity->ran_param_val.flag_false->octet_str_ran.buf,
      plmn_00101,
      sizeof(plmn_00101));

  seq_ran_param_t* S_NSSAI =
      &RRM_Policy_Member->ran_param_struct.ran_param_struct[1];
  S_NSSAI->ran_param_id = S_NSSAI_8_4_3_6;
  S_NSSAI->ran_param_val.type = STRUCTURE_RAN_PARAMETER_VAL_TYPE;
  S_NSSAI->ran_param_val.strct = calloc(1, sizeof(ran_param_struct_t));
  assert(S_NSSAI->ran_param_val.strct != NULL && "Memory exhausted");

  S_NSSAI->ran_param_val.strct->sz_ran_param_struct = 1;
  S_NSSAI->ran_param_val.strct->ran_param_struct =
      calloc(1, sizeof(seq_ran_param_t));
  assert(S_NSSAI->ran_param_val.strct->ran_param_struct != NULL &&
         "Memory exhausted");

  seq_ran_param_t* SST =
      &S_NSSAI->ran_param_val.strct->ran_param_struct[0];
  SST->ran_param_id = SST_8_4_3_6;
  SST->ran_param_val.type = ELEMENT_KEY_FLAG_FALSE_RAN_PARAMETER_VAL_TYPE;
  SST->ran_param_val.flag_false = calloc(1, sizeof(ran_parameter_value_t));
  assert(SST->ran_param_val.flag_false != NULL && "Memory exhausted");

  SST->ran_param_val.flag_false->type = OCTET_STRING_RAN_PARAMETER_VALUE;
  SST->ran_param_val.flag_false->octet_str_ran.len = 1;
  SST->ran_param_val.flag_false->octet_str_ran.buf =
      calloc(1, sizeof(uint8_t));
  assert(SST->ran_param_val.flag_false->octet_str_ran.buf != NULL &&
         "Memory exhausted");

  SST->ran_param_val.flag_false->octet_str_ran.buf[0] = 0x01;

  seq_ran_param_t* Min_PRB_Policy_Ratio =
      &RRM_Policy_Ratio_Group->ran_param_struct.ran_param_struct[1];
  Min_PRB_Policy_Ratio->ran_param_id = Min_PRB_Policy_Ratio_8_4_3_6;
  Min_PRB_Policy_Ratio->ran_param_val.type =
      ELEMENT_KEY_FLAG_FALSE_RAN_PARAMETER_VAL_TYPE;
  Min_PRB_Policy_Ratio->ran_param_val.flag_false =
      calloc(1, sizeof(ran_parameter_value_t));
  assert(Min_PRB_Policy_Ratio->ran_param_val.flag_false != NULL &&
         "Memory exhausted");

  Min_PRB_Policy_Ratio->ran_param_val.flag_false->type =
      INTEGER_RAN_PARAMETER_VALUE;
  Min_PRB_Policy_Ratio->ran_param_val.flag_false->int_ran = 0;

  seq_ran_param_t* Max_PRB_Policy_Ratio =
      &RRM_Policy_Ratio_Group->ran_param_struct.ran_param_struct[2];
  Max_PRB_Policy_Ratio->ran_param_id = Max_PRB_Policy_Ratio_8_4_3_6;
  Max_PRB_Policy_Ratio->ran_param_val.type =
      ELEMENT_KEY_FLAG_FALSE_RAN_PARAMETER_VAL_TYPE;
  Max_PRB_Policy_Ratio->ran_param_val.flag_false =
      calloc(1, sizeof(ran_parameter_value_t));
  assert(Max_PRB_Policy_Ratio->ran_param_val.flag_false != NULL &&
         "Memory exhausted");

  Max_PRB_Policy_Ratio->ran_param_val.flag_false->type =
      INTEGER_RAN_PARAMETER_VALUE;
  Max_PRB_Policy_Ratio->ran_param_val.flag_false->int_ran =
      max_prb_ratio_pct;
}

static
void gen_rrm_policy_ratio_list(
    seq_ran_param_t* RRM_Policy_Ratio_List,
    int max_prb_ratio_pct)
{
  const int num_slice = 1;

  RRM_Policy_Ratio_List->ran_param_id = RRM_Policy_Ratio_List_8_4_3_6;
  RRM_Policy_Ratio_List->ran_param_val.type = LIST_RAN_PARAMETER_VAL_TYPE;
  RRM_Policy_Ratio_List->ran_param_val.lst =
      calloc(1, sizeof(ran_param_list_t));
  assert(RRM_Policy_Ratio_List->ran_param_val.lst != NULL &&
         "Memory exhausted");

  RRM_Policy_Ratio_List->ran_param_val.lst->sz_lst_ran_param = num_slice;
  RRM_Policy_Ratio_List->ran_param_val.lst->lst_ran_param =
      calloc(num_slice, sizeof(lst_ran_param_t));
  assert(RRM_Policy_Ratio_List->ran_param_val.lst->lst_ran_param != NULL &&
         "Memory exhausted");

  gen_rrm_policy_ratio_group(
      &RRM_Policy_Ratio_List->ran_param_val.lst->lst_ran_param[0],
      max_prb_ratio_pct);
}


static
e2sm_rc_ctrl_msg_frmt_1_t gen_rc_ctrl_msg_frmt_1_slice_level_PRB_quota(
    int max_prb_ratio_pct)
{
  e2sm_rc_ctrl_msg_frmt_1_t dst = {0};

  // 8.4.3.6
  // RRM Policy Ratio List, LIST (len 1)
  // > RRM Policy Ratio Group, STRUCTURE (len 4)
  // >>  RRM Policy, STRUCTURE (len 1)
  // >>> RRM Policy Member List, LIST (len 1)
  // >>>> RRM Policy Member, STRUCTURE (len 2)
  // >>>>> PLMN Identity, ELEMENT
  // >>>>> S-NSSAI, STRUCTURE (len 2)
  // >>>>>> SST, ELEMENT
  // >>>>>> SD, ELEMENT
  // >> Min PRB Policy Ratio, ELEMENT
  // >> Max PRB Policy Ratio, ELEMENT
  // >> Dedicated PRB Policy Ratio, ELEMENT


  // RRM Policy Ratio List, LIST
  dst.sz_ran_param = 1;
  dst.ran_param = calloc(1, sizeof(seq_ran_param_t));
  assert(dst.ran_param != NULL && "Memory exhausted");
  gen_rrm_policy_ratio_list(
      &dst.ran_param[0],
      max_prb_ratio_pct);

  return dst;
}

static
e2sm_rc_ctrl_msg_t gen_rc_ctrl_msg(
    e2sm_rc_ctrl_msg_e msg_frmt,
    int max_prb_ratio_pct)
{
  e2sm_rc_ctrl_msg_t dst = {0}; 

  if (msg_frmt == FORMAT_1_E2SM_RC_CTRL_MSG) {
    dst.format = msg_frmt;
    dst.frmt_1 = gen_rc_ctrl_msg_frmt_1_slice_level_PRB_quota(
        max_prb_ratio_pct);
  } else {
    assert(0!=0 && "not implemented the fill func for this ctrl msg frmt");
  }

  return dst;
}

static
ue_id_e2sm_t gen_rc_ue_id(ue_id_e2sm_e type)
{
  ue_id_e2sm_t ue_id = {0};
  if (type == GNB_UE_ID_E2SM) {
    ue_id.type = GNB_UE_ID_E2SM;
    // TODO
    ue_id.gnb.amf_ue_ngap_id = 0;
    ue_id.gnb.guami.plmn_id.mcc = 1;
    ue_id.gnb.guami.plmn_id.mnc = 1;
    ue_id.gnb.guami.plmn_id.mnc_digit_len = 2;
    ue_id.gnb.guami.amf_region_id = 0;
    ue_id.gnb.guami.amf_set_id = 0;
    ue_id.gnb.guami.amf_ptr = 0;
  } else {
    assert(0!=0 && "not supported UE ID type");
  }
  return ue_id;
}

int main(int argc, char *argv[])
{
  const int max_prb_ratio_pct =
      sci_oran_prompt12_max_prb_ratio_pct();

  printf("[xApp]: REQUESTED_MAX_PRB_RATIO_PCT=%d\n",
         max_prb_ratio_pct);

  fr_args_t args = init_fr_args(argc, argv);
  defer({ free_fr_args(&args); });

  //Init the xApp
  init_xapp_api(&args);
  sleep(1);

  e2_node_arr_xapp_t nodes = e2_nodes_xapp_api();
  defer({ free_e2_node_arr_xapp(&nodes); });
  assert(nodes.len > 0);
  printf("Connected E2 nodes = %d\n", nodes.len);

  //////////// 
  // START RC 
  ////////////
  
  // RC Control
  // CONTROL Service Style 2: Radio Resource Allocation Control
  // Action ID 6: Slice-level PRB quota
  // E2SM-RC Control Header Format 1
  // E2SM-RC Control Message Format 1
  rc_ctrl_req_data_t rc_ctrl = {0};
  ue_id_e2sm_t ue_id = gen_rc_ue_id(GNB_UE_ID_E2SM);

  rc_ctrl.hdr = gen_rc_ctrl_hdr(FORMAT_1_E2SM_RC_CTRL_HDR, ue_id, 2, Slice_level_PRB_quotal_7_6_3_1);
  rc_ctrl.msg = gen_rc_ctrl_msg(
      FORMAT_1_E2SM_RC_CTRL_MSG,
      max_prb_ratio_pct);

  int64_t st = time_now_us();
  assert(nodes.len == 1 &&
         "Prompt11R requires exactly one E2 node");

  printf("[xApp]: ACTUATOR_CONTRACT="
         "PLMN00101_SST1_MIN0_MAX%d\n",
         max_prb_ratio_pct);
  printf("[xApp]: CONTROL_REQUEST_COUNT=1\n");

  control_sm_xapp_api(&nodes.n[0].id, SM_RC_ID, &rc_ctrl);
  printf("[xApp]: Control Loop Latency: %ld us\n", time_now_us() - st);
  free_rc_ctrl_req_data(&rc_ctrl);

  //////////// 
  // END RC 
  //////////// 

  sleep(5);


  //Stop the xApp
  while(try_stop_xapp_api() == false)
    usleep(1000);

  printf("Test xApp run SUCCESSFULLY\n");

}

