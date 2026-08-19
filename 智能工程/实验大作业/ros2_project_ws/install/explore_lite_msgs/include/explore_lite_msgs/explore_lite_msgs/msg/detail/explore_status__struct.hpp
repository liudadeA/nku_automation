// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from explore_lite_msgs:msg/ExploreStatus.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "explore_lite_msgs/msg/explore_status.hpp"


#ifndef EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__STRUCT_HPP_
#define EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__explore_lite_msgs__msg__ExploreStatus __attribute__((deprecated))
#else
# define DEPRECATED__explore_lite_msgs__msg__ExploreStatus __declspec(deprecated)
#endif

namespace explore_lite_msgs
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct ExploreStatus_
{
  using Type = ExploreStatus_<ContainerAllocator>;

  explicit ExploreStatus_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->status = "";
    }
  }

  explicit ExploreStatus_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : status(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->status = "";
    }
  }

  // field types and members
  using _status_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _status_type status;

  // setters for named parameter idiom
  Type & set__status(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->status = _arg;
    return *this;
  }

  // constant declarations
  static const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> EXPLORATION_STARTED;
  static const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> EXPLORATION_IN_PROGRESS;
  static const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> EXPLORATION_PAUSED;
  static const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> EXPLORATION_COMPLETE;
  static const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> RETURNING_TO_ORIGIN;
  static const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> RETURNED_TO_ORIGIN;

  // pointer types
  using RawPtr =
    explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator> *;
  using ConstRawPtr =
    const explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__explore_lite_msgs__msg__ExploreStatus
    std::shared_ptr<explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__explore_lite_msgs__msg__ExploreStatus
    std::shared_ptr<explore_lite_msgs::msg::ExploreStatus_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const ExploreStatus_ & other) const
  {
    if (this->status != other.status) {
      return false;
    }
    return true;
  }
  bool operator!=(const ExploreStatus_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct ExploreStatus_

// alias to use template instance with default allocator
using ExploreStatus =
  explore_lite_msgs::msg::ExploreStatus_<std::allocator<void>>;

// constant definitions
template<typename ContainerAllocator>
const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>
ExploreStatus_<ContainerAllocator>::EXPLORATION_STARTED = "exploration_started";
template<typename ContainerAllocator>
const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>
ExploreStatus_<ContainerAllocator>::EXPLORATION_IN_PROGRESS = "exploration_in_progress";
template<typename ContainerAllocator>
const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>
ExploreStatus_<ContainerAllocator>::EXPLORATION_PAUSED = "exploration_paused";
template<typename ContainerAllocator>
const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>
ExploreStatus_<ContainerAllocator>::EXPLORATION_COMPLETE = "exploration_complete";
template<typename ContainerAllocator>
const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>
ExploreStatus_<ContainerAllocator>::RETURNING_TO_ORIGIN = "returning_to_origin";
template<typename ContainerAllocator>
const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>
ExploreStatus_<ContainerAllocator>::RETURNED_TO_ORIGIN = "returned_to_origin";

}  // namespace msg

}  // namespace explore_lite_msgs

#endif  // EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__STRUCT_HPP_
