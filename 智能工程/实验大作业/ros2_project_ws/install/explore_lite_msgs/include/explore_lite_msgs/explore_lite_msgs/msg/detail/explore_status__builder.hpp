// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from explore_lite_msgs:msg/ExploreStatus.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "explore_lite_msgs/msg/explore_status.hpp"


#ifndef EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__BUILDER_HPP_
#define EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "explore_lite_msgs/msg/detail/explore_status__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace explore_lite_msgs
{

namespace msg
{

namespace builder
{

class Init_ExploreStatus_status
{
public:
  Init_ExploreStatus_status()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::explore_lite_msgs::msg::ExploreStatus status(::explore_lite_msgs::msg::ExploreStatus::_status_type arg)
  {
    msg_.status = std::move(arg);
    return std::move(msg_);
  }

private:
  ::explore_lite_msgs::msg::ExploreStatus msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::explore_lite_msgs::msg::ExploreStatus>()
{
  return explore_lite_msgs::msg::builder::Init_ExploreStatus_status();
}

}  // namespace explore_lite_msgs

#endif  // EXPLORE_LITE_MSGS__MSG__DETAIL__EXPLORE_STATUS__BUILDER_HPP_
