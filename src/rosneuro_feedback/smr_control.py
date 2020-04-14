#!/usr/bin/python

from smr_utilities import *

class SmrControl(object):
	def __init__(self):

		##### Configure publisher #####
		self.event_pub = rospy.Publisher("/events/bus", NeuroEvent, queue_size=1000)

		##### Configure subscriber #####
		rospy.Subscriber("/integrator/integrated_neuroprediction", NeuroOutput, self.receive_probabilities)

		##### Configure protocol #####
		self.n_classes = rospy.get_param('~n_classes')
		self.n_trials = rospy.get_param('~n_trials')
		self.threshold = rospy.get_param('~threshold')
		self.values = numpy.zeros(self.n_classes)

		self.timings_begin = rospy.get_param('~timings_begin')
		self.timings_fixation = rospy.get_param('~timings_fixation')
		self.timings_cue = rospy.get_param('~timings_cue')
		self.timings_feedback_update = rospy.get_param('~timings_feedback_update')
		self.timings_boom = rospy.get_param('~timings_boom')
		self.timings_end = rospy.get_param('~timings_end')

	def receive_probabilities(self, msg):
		self.values = msg.softpredict.data

	def reset_bci(self):
		rospy.wait_for_service('/integrator/reset')
		resbci = rospy.ServiceProxy('/integrator/reset', Empty)
    		try:
			resbci()
			return True
   		except rospy.ServiceException, e:
        		print "Service call failed: %s"
			return False

	def run(self):

		##### Configure GUI engine #####
		gui = SMRGUI(rospy.get_param('~window_height'),rospy.get_param('~window_width'),rospy.get_param('~window_scale'))
		gui.init_bars(self.n_classes)
		gui.draw()

		print("[smr2class] Protocol starts")
		cv2.waitKey(self.timings_begin)

		exit = False
		while not exit:
			##### Continuous feedback #####
			self.values = numpy.zeros(self.n_classes)
			hit = False
			self.reset_bci()
			rospy.sleep(0.050)
			publish_neuro_event(self.event_pub, CFEEDBACK)

			while not hit:
				#rospy.spin()
				for c in range(self.n_classes):
					value = normalize_probabilities(self.values[c], self.threshold, 1/float(self.n_classes))
					gui.set_value_bars(value, c)
					if value >= 1.0: 
						hit = True
						break
				if check_exit(cv2.waitKey(self.timings_feedback_update)): exit=True
			publish_neuro_event(self.event_pub, CFEEDBACK+OFF)

			##### Boom #####
			gui.set_alpha_bars(0.8, c)
			cv2.waitKey(100)
			if c == idx:
				publish_neuro_event(self.event_pub, TARGETHIT)
				if check_exit(cv2.waitKey(self.timings_boom)): exit=True
				publish_neuro_event(self.event_pub, TARGETHIT+OFF)
			else:
				publish_neuro_event(self.event_pub, TARGETMISS)
				if check_exit(cv2.waitKey(self.timings_boom)): exit=True
				publish_neuro_event(self.event_pub, TARGETMISS+OFF)
			gui.reset_bars()
			gui.remove_cue()

			if exit:
				print("User asked to quit")
				break

		print("[smr2class] Protocol ends")
		cv2.waitKey(self.timings_end)