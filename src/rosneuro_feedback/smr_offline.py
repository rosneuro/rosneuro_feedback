#!/usr/bin/python
import cv2
import rospy
import rospkg
import os
import random
import math
import numpy
import smr_utilities
from rosneuro_msgs.msg import NeuroEvent
from draw.GUI import SMRGUI


class SmrOffline(object):
	def __init__(self):

		##### Configure publisher #####
		self.event_pub = rospy.Publisher("/events/bus", NeuroEvent, queue_size=1000)

	def run(self):
		
		##### Configure protocol #####
		sequence = config_trials(rospy.get_param('~n_classes'),rospy.get_param('~n_trials'))

		##### Configure GUI engine #####
		gui = SMRGUI(rospy.get_param('~window_height'),rospy.get_param('~window_width'),rospy.get_param('~window_scale'))
		gui.init_bars(rospy.get_param('~n_classes'))
		gui.draw()

		print("[smr2class] Protocol starts")
		cv2.waitKey(rospy.get_param('~timings_begin'))

		exit = False
		for i,idx in enumerate(sequence):
			print("Trial " + str(i+1) + "/" + str(len(sequence)) + " [" + CLASSES[idx] + "]")

			##### Fixation #####
			publish_neuro_event(self.event_pub, FIXATION)
			gui.add_fixation()
			cv2.waitKey(rospy.get_param('~timings_fixation'))
			publish_neuro_event(self.event_pub, FIXATION+OFF)
			gui.remove_fixation()

			##### Cue #####
			publish_neuro_event(self.event_pub,CLASS_EVENTS[idx])
			gui.add_cue(idx)
			cv2.waitKey(rospy.get_param('~timings_cue'))
			publish_neuro_event(self.event_pub, CLASS_EVENTS[idx]+OFF)

			##### Continuous feedback #####
			Period = random.randrange(rospy.get_param('~timings_feedback_min'), rospy.get_param('~timings_feedback_max'))
			F = 1.0/(4.0 * Period);

			t = 0
			publish_neuro_event(self.event_pub, CFEEDBACK)
			while t < Period:
				value = math.sin(2.0*math.pi*t*F)
				gui.set_value_bars(value, idx)
				t = t + rospy.get_param('~timings_feedback_update')
				if check_exit(cv2.waitKey(rospy.get_param('~timings_feedback_update'))): exit=True
			publish_neuro_event(self.event_pub, CFEEDBACK+OFF)

			##### Boom #####
			gui.set_alpha_bars(0.8, idx)
			if check_exit(cv2.waitKey(rospy.get_param('~timings_boom'))): exit=True
			gui.reset_bars()
			gui.remove_cue()

			if check_exit(cv2.waitKey(rospy.get_param('~timings_iti'))): exit=True
			if exit:
				print("User asked to quit")
				break

		print("[smr2class] Protocol ends")
		cv2.waitKey(rospy.get_param('~timings_end'))