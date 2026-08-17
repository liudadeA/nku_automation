// generated from rosidl_typesupport_fastrtps_c/resource/idl__rosidl_typesupport_fastrtps_c.h.em
// with input from explore_lite_msgs:msg/ExploreStatus.idl
// generated code does not contain a copyright notice
#ifndef EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__ROSIDL_TYPESUPPORT_FASTRTPS_C_H_
#define EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__ROSIDL_TYPESUPPORT_FASTRTPS_C_H_


#include <stddef.h>
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_interface/macros.h"
#include "explore_lite_msgs/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "explore_lite_msgs/msg/detail/explore_status__struct.h"
#include "fastcdr/Cdr.h"

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_explore_lite_msgs
bool cdr_serialize_explore_lite_msgs__msg__ExploreStatus(
  const explore_lite_msgs__msg__ExploreStatus * ros_message,
  eprosima::fastcdr::Cdr & cdr);

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_explore_lite_msgs
bool cdr_deserialize_explore_lite_msgs__msg__ExploreStatus(
  eprosima::fastcdr::Cdr &,
  explore_lite_msgs__msg__ExploreStatus * ros_message);

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_explore_lite_msgs
size_t get_serialized_size_explore_lite_msgs__msg__ExploreStatus(
  const void * untyped_ros_message,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_explore_lite_msgs
size_t max_serialized_size_explore_lite_msgs__msg__ExploreStatus(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_explore_lite_msgs
bool cdr_serialize_key_explore_lite_msgs__msg__ExploreStatus(
  const explore_lite_msgs__msg__ExploreStatus * ros_message,
  eprosima::fastcdr::Cdr & cdr);

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_explore_lite_msgs
size_t get_serialized_size_key_explore_lite_msgs__msg__ExploreStatus(
  const void * untyped_ros_message,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_explore_lite_msgs
size_t max_serialized_size_key_explore_lite_msgs__msg__ExploreStatus(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_explore_lite_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, explore_lite_msgs, msg, ExploreStatus)();

#ifdef __cplusplus
}
#endif

#endif  // EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__ROSIDL_TYPESUPPORT_FASTRTPS_C_H_
