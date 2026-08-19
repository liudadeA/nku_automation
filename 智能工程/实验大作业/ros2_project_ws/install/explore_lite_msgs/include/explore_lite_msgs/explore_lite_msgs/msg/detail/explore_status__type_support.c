// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from explore_lite_msgs:msg/ExploreStatus.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "explore_lite_msgs/msg/detail/explore_status__rosidl_typesupport_introspection_c.h"
#include "explore_lite_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "explore_lite_msgs/msg/detail/explore_status__functions.h"
#include "explore_lite_msgs/msg/detail/explore_status__struct.h"


// Include directives for member types
// Member `status`
#include "rosidl_runtime_c/string_functions.h"

#ifdef __cplusplus
extern "C"
{
#endif

void explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  explore_lite_msgs__msg__ExploreStatus__init(message_memory);
}

void explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_fini_function(void * message_memory)
{
  explore_lite_msgs__msg__ExploreStatus__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_message_member_array[1] = {
  {
    "status",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_STRING,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is key
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(explore_lite_msgs__msg__ExploreStatus, status),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_message_members = {
  "explore_lite_msgs__msg",  // message namespace
  "ExploreStatus",  // message name
  1,  // number of fields
  sizeof(explore_lite_msgs__msg__ExploreStatus),
  false,  // has_any_key_member_
  explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_message_member_array,  // message members
  explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_init_function,  // function to initialize message memory (memory has to be allocated)
  explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_message_type_support_handle = {
  0,
  &explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_message_members,
  get_message_typesupport_handle_function,
  &explore_lite_msgs__msg__ExploreStatus__get_type_hash,
  &explore_lite_msgs__msg__ExploreStatus__get_type_description,
  &explore_lite_msgs__msg__ExploreStatus__get_type_description_sources,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_explore_lite_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, explore_lite_msgs, msg, ExploreStatus)() {
  if (!explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_message_type_support_handle.typesupport_identifier) {
    explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &explore_lite_msgs__msg__ExploreStatus__rosidl_typesupport_introspection_c__ExploreStatus_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
