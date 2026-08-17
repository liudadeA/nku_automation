// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from explore_lite_msgs:msg/ExploreStatus.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "explore_lite_msgs/msg/explore_status.h"


#ifndef EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__STRUCT_H_
#define EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// Constants defined in the message

/// Constant 'EXPLORATION_STARTED'.
static const char * const explore_lite_msgs__msg__ExploreStatus__EXPLORATION_STARTED = "exploration_started";

/// Constant 'EXPLORATION_IN_PROGRESS'.
static const char * const explore_lite_msgs__msg__ExploreStatus__EXPLORATION_IN_PROGRESS = "exploration_in_progress";

/// Constant 'EXPLORATION_PAUSED'.
static const char * const explore_lite_msgs__msg__ExploreStatus__EXPLORATION_PAUSED = "exploration_paused";

/// Constant 'EXPLORATION_COMPLETE'.
static const char * const explore_lite_msgs__msg__ExploreStatus__EXPLORATION_COMPLETE = "exploration_complete";

/// Constant 'RETURNING_TO_ORIGIN'.
static const char * const explore_lite_msgs__msg__ExploreStatus__RETURNING_TO_ORIGIN = "returning_to_origin";

/// Constant 'RETURNED_TO_ORIGIN'.
static const char * const explore_lite_msgs__msg__ExploreStatus__RETURNED_TO_ORIGIN = "returned_to_origin";

// Include directives for member types
// Member 'status'
#include "rosidl_runtime_c/string.h"

/// Struct defined in msg/ExploreStatus in the package explore_lite_msgs.
/**
  * Exploration status constants
  * EXPLORATION_STARTED: Exploration has begun (published on initialization)
  * EXPLORATION_IN_PROGRESS: Exploration resumed after pause
  * EXPLORATION_PAUSED: Exploration manually stopped via /explore/resume topic
  * EXPLORATION_COMPLETE: No frontiers remaining, exploration finished
  * RETURNING_TO_ORIGIN: Robot navigating back to initial pose (if return_to_init: true)
  * RETURNED_TO_ORIGIN: Robot successfully reached initial pose
 */
typedef struct explore_lite_msgs__msg__ExploreStatus
{
  /// Current exploration status
  rosidl_runtime_c__String status;
} explore_lite_msgs__msg__ExploreStatus;

// Struct for a sequence of explore_lite_msgs__msg__ExploreStatus.
typedef struct explore_lite_msgs__msg__ExploreStatus__Sequence
{
  explore_lite_msgs__msg__ExploreStatus * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} explore_lite_msgs__msg__ExploreStatus__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__STRUCT_H_
