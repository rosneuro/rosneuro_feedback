cmake_minimum_required(VERSION 2.8.3)
project(rosneuro_feedback)

## Find catkin macros and libraries
## if COMPONENTS list like find_package(catkin REQUIRED COMPONENTS xyz)
## is used, also find other catkin packages
find_package(catkin REQUIRED COMPONENTS
  rospy
  rosneuro_msgs
)

catkin_python_setup()
