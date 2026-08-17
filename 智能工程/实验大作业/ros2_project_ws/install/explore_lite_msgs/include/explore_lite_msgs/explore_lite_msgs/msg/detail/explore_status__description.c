// generated from rosidl_generator_c/resource/idl__description.c.em
// with input from explore_lite_msgs:msg/ExploreStatus.idl
// generated code does not contain a copyright notice

#include "explore_lite_msgs/msg/detail/explore_status__functions.h"

ROSIDL_GENERATOR_C_PUBLIC_explore_lite_msgs
const rosidl_type_hash_t *
explore_lite_msgs__msg__ExploreStatus__get_type_hash(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_type_hash_t hash = {1, {
      0xee, 0x04, 0x10, 0x81, 0x3d, 0x9a, 0x50, 0x19,
      0xaa, 0x6b, 0x29, 0x69, 0x18, 0x7a, 0x8a, 0xa0,
      0x0f, 0x59, 0x3a, 0x76, 0xaa, 0xc6, 0x20, 0xf0,
      0x5c, 0xc0, 0xa5, 0x1c, 0xb5, 0xa4, 0xbc, 0x5c,
    }};
  return &hash;
}

#include <assert.h>
#include <string.h>

// Include directives for referenced types

// Hashes for external referenced types
#ifndef NDEBUG
#endif

static char explore_lite_msgs__msg__ExploreStatus__TYPE_NAME[] = "explore_lite_msgs/msg/ExploreStatus";

// Define type names, field names, and default values
static char explore_lite_msgs__msg__ExploreStatus__FIELD_NAME__status[] = "status";

static rosidl_runtime_c__type_description__Field explore_lite_msgs__msg__ExploreStatus__FIELDS[] = {
  {
    {explore_lite_msgs__msg__ExploreStatus__FIELD_NAME__status, 6, 6},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_STRING,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
};

const rosidl_runtime_c__type_description__TypeDescription *
explore_lite_msgs__msg__ExploreStatus__get_type_description(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static bool constructed = false;
  static const rosidl_runtime_c__type_description__TypeDescription description = {
    {
      {explore_lite_msgs__msg__ExploreStatus__TYPE_NAME, 35, 35},
      {explore_lite_msgs__msg__ExploreStatus__FIELDS, 1, 1},
    },
    {NULL, 0, 0},
  };
  if (!constructed) {
    constructed = true;
  }
  return &description;
}

static char toplevel_type_raw_source[] =
  "# Exploration status constants\n"
  "# EXPLORATION_STARTED: Exploration has begun (published on initialization)\n"
  "# EXPLORATION_IN_PROGRESS: Exploration resumed after pause\n"
  "# EXPLORATION_PAUSED: Exploration manually stopped via /explore/resume topic\n"
  "# EXPLORATION_COMPLETE: No frontiers remaining, exploration finished\n"
  "# RETURNING_TO_ORIGIN: Robot navigating back to initial pose (if return_to_init: true)\n"
  "# RETURNED_TO_ORIGIN: Robot successfully reached initial pose\n"
  "\n"
  "string EXPLORATION_STARTED=exploration_started\n"
  "string EXPLORATION_IN_PROGRESS=exploration_in_progress\n"
  "string EXPLORATION_PAUSED=exploration_paused\n"
  "string EXPLORATION_COMPLETE=exploration_complete\n"
  "string RETURNING_TO_ORIGIN=returning_to_origin\n"
  "string RETURNED_TO_ORIGIN=returned_to_origin\n"
  "\n"
  "# Current exploration status\n"
  "string status";

static char msg_encoding[] = "msg";

// Define all individual source functions

const rosidl_runtime_c__type_description__TypeSource *
explore_lite_msgs__msg__ExploreStatus__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static const rosidl_runtime_c__type_description__TypeSource source = {
    {explore_lite_msgs__msg__ExploreStatus__TYPE_NAME, 35, 35},
    {msg_encoding, 3, 3},
    {toplevel_type_raw_source, 793, 793},
  };
  return &source;
}

const rosidl_runtime_c__type_description__TypeSource__Sequence *
explore_lite_msgs__msg__ExploreStatus__get_type_description_sources(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_runtime_c__type_description__TypeSource sources[1];
  static const rosidl_runtime_c__type_description__TypeSource__Sequence source_sequence = {sources, 1, 1};
  static bool constructed = false;
  if (!constructed) {
    sources[0] = *explore_lite_msgs__msg__ExploreStatus__get_individual_type_description_source(NULL),
    constructed = true;
  }
  return &source_sequence;
}
