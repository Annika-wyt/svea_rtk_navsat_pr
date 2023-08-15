#! /usr/bin/env python3

import numpy as np

import rospy

import tf
import tf2_ros
import tf2_geometry_msgs
from tf import transformations 
from tf.transformations import euler_from_quaternion, quaternion_from_euler
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from sensor_msgs.msg import NavSatFix
from geometry_msgs.msg import PoseWithCovarianceStamped, TransformStamped, Point, Quaternion, PoseStamped, Vector3
from aruco_msgs.msg import Marker

#TODO: conditions for static gps and active gps

class static_svea_gps:

    def __init__(self):
        #initalize the node 
        rospy.init_node('static_svea_gps')

        #get parameters
        self.aruco_pose_topic = rospy.get_param("~aruco_pose_topic", "aruco_pose")
        #self.aruco_id = rospy.get_param("~aruco_id", [[11, 13]])
        self.aruco_id = [11, 13]
        #self.aruco_pose = rospy.get_param("") #TODO: set the pose for aruco marker
        self.aruco_pose = [[-2.615, 0, 0], [1.17, 2.305, 0]]
        self.aruco_ori = [[1.57, 0, 1.57], [1.57, 0, 0]]
        #Subscriber
        rospy.Subscriber(self.aruco_pose_topic, Marker, self.aruco_callback)
        
        #Publisher
        self.global_set_pose_pub = rospy.Publisher("/global/set_pose", PoseWithCovarianceStamped, queue_size=1) #publish to set_pose service provided by robot localization to reset the position

        #Variable
        self.frame = 'aruco' + str(self.aruco_id)
        self.lin_cov = 1e-6
        self.ang_cov = 1e-6

        #Transformation
        self.buffer = tf2_ros.Buffer(rospy.Duration(10))
        self.listener = tf2_ros.TransformListener(self.buffer)
        self.br = tf2_ros.TransformBroadcaster()

    def run(self):
        rospy.spin()

    def aruco_callback(self, msg):
        if msg.id in self.aruco_id:
            try:
    #            rospy.loginfo("Received ARUCO")

                inverse_transform = self.buffer.lookup_transform('aruco' + str(msg.id), "base_link", msg.header.stamp, rospy.Duration(0.5)) #frame_id: aruco, child_frame_id: baselink
                adjust_orientation = TransformStamped()
                adjust_orientation.header = msg.header
                adjust_orientation.header.frame_id = "map"
                adjust_orientation.child_frame_id = 'aruco' + str(msg.id)
                rospy.loginfo(f"translation used: index{self.aruco_id.index(msg.id)} \t {self.aruco_pose[self.aruco_id.index(msg.id)]}")
                adjust_orientation.transform.translation = Vector3(*self.aruco_pose[self.aruco_id.index(msg.id)])
                q = quaternion_from_euler(*self.aruco_ori[self.aruco_id.index(msg.id)])
                adjust_orientation.transform.rotation = Quaternion(*q)

                inverse_posestamped = PoseStamped()
                inverse_posestamped.pose.position = inverse_transform.transform.translation
                inverse_posestamped.pose.orientation = inverse_transform.transform.rotation   

                position = tf2_geometry_msgs.do_transform_pose(inverse_posestamped, adjust_orientation) #frame_id = map child_frame: baselink
                position.pose.position.z = 0.0
    #            rospy.loginfo(f"position \n {position}")
                
                self.publish_pose(position.pose.position, position.pose.orientation, msg.header.stamp)
    #            self.broadcast_aruco(position.pose.position, position.pose.orientation, msg.header.stamp)
            except Exception as e:
                rospy.loginfo(f"Exception: \n {e}")
                
    def publish_pose(self, translation, quaternion, time):
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = time
        msg.header.frame_id = "map"
        msg.pose.pose.position = translation
        msg.pose.pose.orientation = quaternion
        msg.pose.covariance = self.set_covariance()
        self.global_set_pose_pub.publish(msg)

    def broadcast_aruco(self, translation, quaternion, time):
        msg = TransformStamped()
        msg.header.stamp = time
        msg.header.frame_id = "map"
        msg.child_frame_id = "basebase"
        msg.transform.translation = translation
        msg.transform.rotation = quaternion
        self.br.sendTransform(msg)

    def set_covariance(self):
        return [self.lin_cov, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, self.lin_cov, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, self.lin_cov, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, self.ang_cov, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, self.ang_cov, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, self.ang_cov]

if __name__ == '__main__':
    static_svea_gps().run()