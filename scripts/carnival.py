#!/usr/bin/python
import cv2
import rospy
import numpy
import random
from std_msgs.msg import *
from cnbiros_bci.msg import TidMessage


# Event class
class Event:
	begin = 1500
	iccue = 600
	icphase = 601
	inccue = 602
	incphase = 603
	end = 1700

	flagIC = False
	flagINC1 = False
	flagINC2 = False

	duration = 0;

	
	def talker(self):
		self.pub = rospy.Publisher("/rostid_ros2cnbi", TidMessage, queue_size=1000) #CNBIROS_BCI_TID_ROS2CNBI
		self.rosidm = TidMessage()
		self.rosidm.header.frame_id = "base_link" #CNBIROS_BCI_TID_FRAMEID
		self.rosidm.version         = "0.0.1" #CNBIROS_BCI_TID_VERSION
		self.rosidm.family 		   = 0 #IDMessage.FamilyBiosig
		self.rosidm.description 	   = "ros_tidsender"
		self.rosidm.event 		   = 666
		self.rosidm.pipe			   = "/bus"

	

# Player class draws just a blue dot
class Player:
	def __init__(self, width, height):
		self.width = width
		self.height = height

		self.size = 20
		self.pos = numpy.int32((width / 2, height - 20))

	def draw(self, canvas):
		half_extent = (self.size / 2, self.size / 2)
		pt1 = tuple(self.pos - half_extent)
		pt2 = tuple(self.pos + half_extent)
		cv2.line(canvas, (self.width / 2, 0), tuple(self.pos), (0, 128, 64))
		cv2.rectangle(canvas, pt1, pt2, (255, 0, 0), -1)


# Block to be shooted
class Block:
	def __init__(self, pos, id):
		block_width = rospy.get_param('~block_width', 40)
		block_height = rospy.get_param('~block_height', 20)
		block_speed = rospy.get_param('~block_speed', 1)

		self.screen_width = rospy.get_param('~screen_width', 640)
		self.size = numpy.int32((block_width, block_height))
		self.pos = numpy.float32(pos)
		self.speed = block_speed
		self.color = None
		self.id = id

	def set_color(self, color):
		if self.color is None:
			self.color = color

	def draw(self, canvas):
		is_missed = self.pos[0] + self.size[0] < self.screen_width / 2
		if is_missed and self.color is None:
			self.color = (0, 0, 255)

		pt1 = tuple((self.pos - self.size / 2).astype(numpy.int32))
		pt2 = tuple((self.pos + self.size / 2).astype(numpy.int32))

		color = (255, 255, 255) if self.color is None else self.color
		cv2.rectangle(canvas, pt1, pt2, color, -1)

	def update(self):
		self.pos[0] -= self.speed


# Bullet or cannonball
class Bullet:
	def __init__(self, pos):
		bullet_width = rospy.get_param('bullet_width', 10)
		self.size = numpy.int32((bullet_width, 4000))
		self.pos = numpy.int32((pos[0], pos[1]))
		self.speed = 500
		self.hit = False

	def draw(self, canvas):
		return
		pt1 = tuple(self.pos - self.size / 2)
		pt2 = tuple(self.pos + self.size / 2)
		cv2.rectangle(canvas, pt1, pt2, (0, 255, 128), 2)

	def update(self):
		self.pos[1] -= self.speed

	# if the bullet left the screen
	def gone(self):
		return self.pos[1] < self.size[1]

	# test if the bullet hits with a block
	def hit_test(self, block):
		m1 = self.pos - self.size / 2
		m2 = self.pos + self.size / 2
		e1 = block.pos - block.size / 2
		e2 = block.pos + block.size / 2

		ret = m1[0] <= e2[0] and e1[0] <= m2[0] and m1[1] <= e2[1] and e1[1] <= m2[1]

		self.hit = self.hit or ret

		return ret


# Game class
class Game:
	def __init__(self, event):
		self.over = False
		self.end = False
		self.event = event
		self.width = rospy.get_param('~screen_width', 640)
		self.height = rospy.get_param('~screen_height', 480)
		self.scale = rospy.get_param('~screen_scale', 3)
		self.next_block_time = rospy.Time(0)
		self.start_event_time = rospy.Time(0)

		self.player = Player(self.width, self.height)
		self.cluster_id_source = 1
		self.blocks = []
		self.bullets = []

		self.block_interval_mean = rospy.get_param('~block_interval_mean', 3.5)
		self.block_interval_stddev = rospy.get_param('~block_interval_stddev', 1.0)
		self.block_interval_min = rospy.get_param('~block_interval_min', 2.0)
		self.block_interval_max = rospy.get_param('~block_interval_max', 5.0)
		self.cluster_id_max = rospy.get_param('~trials_number', 15)

		self.flag_new_cluster = True

		self.input = False

	# if the game is over
	def is_over(self):
		return self.over

	def time_until_next_block(self):
		time = numpy.random.normal(self.block_interval_mean, self.block_interval_stddev)
		time = min(self.block_interval_max, max(self.block_interval_min, time))
		return rospy.Duration(time)

	# generate a big block consisting of small pieces
	def generate_block_cluster(self, width, height):
		block_width = rospy.get_param('~block_width', 40)
		cluster_size_min = rospy.get_param('~cluster_size_min', 10)
		cluster_size_max = rospy.get_param('~cluster_size_max', 20)
		num_blocks = random.randrange(cluster_size_min, cluster_size_max)

		pos_x = [width + x * block_width for x in range(num_blocks)]
		blocks = [Block((x, 30), self.cluster_id_source) for x in pos_x]
		self.cluster_id_source += 1

		return 	blocks

	def draw(self):
		canvas = numpy.zeros((self.height, self.width, 3), numpy.uint8)

		for block in self.blocks:
			block.draw(canvas)

		for bullet in self.bullets:
			bullet.draw(canvas)

		self.player.draw(canvas)

		canvas = cv2.resize(canvas, (canvas.shape[1] * self.scale, canvas.shape[0] * self.scale))
		cv2.imshow('canvas', canvas)

	def check_end(self):
		if self.cluster_id_source > self.cluster_id_max:
			self.end = True
		if self.end and not len(self.blocks) > 0:
			print("END")
			################################
			self.event.rosidm.header.stamp    = rospy.Time.now()
			self.event.rosidm.event 		   = Event.end
			self.event.pub.publish(self.event.rosidm)
			################################

			cv2.waitKey(2000)
			self.over = True

	def update(self):
		# you can get block states like:
		block_positions = [x.pos for x in self.blocks]
		block_ids = [x.id for x in self.blocks]

		# spawn new block cluster !!!! IC-CUE event !!!!
		if rospy.Time.now() > self.next_block_time and not self.end and self.flag_new_cluster:
			Event.duration = rospy.Time.now() - self.start_event_time
			self.start_event_time = rospy.Time.now()
			print(Event.duration.to_sec())
			print("IC-CUE 600")
			################################
			self.event.rosidm.header.stamp    = rospy.Time.now()
			self.event.rosidm.event 		   = Event.iccue
			self.event.pub.publish(self.event.rosidm)
			################################
			Event.flagIC = False
			#self.next_block_time = rospy.Time.now() + self.time_until_next_block()
			cluster = self.generate_block_cluster(self.width, self.height)
			self.blocks.extend(cluster)
			self.flag_new_cluster = False

		# update game elements
		for block in self.blocks:
			block.update()
		# erase blocks who left the screen
		self.blocks = [x for x in self.blocks if x.pos[0] > -block.size[0]] # why not 0 ??? # -100
		block_ids = [x.id for x in self.blocks]
		
		if len(self.blocks) > 0:
			
			block_width = rospy.get_param('~block_width', 40)

			# !!!! IC-PHASE event !!!!
			first_block_idx = block_ids.index(max(block_ids))
			if self.blocks[first_block_idx].pos[0] - block_width / 2 < self.width / 2 and not Event.flagIC:
				Event.duration = rospy.Time.now() - self.start_event_time
				self.start_event_time = rospy.Time.now()
				print(Event.duration.to_sec())
				print("IC-PHASE 601")
				################################
				self.event.rosidm.header.stamp    = rospy.Time.now()
				self.event.rosidm.event 		   = Event.icphase
				self.event.pub.publish(self.event.rosidm)
				################################
				Event.flagIC = True
				Event.flagINC1 = False
		
			# !!!! INC-CUE event !!!! 
			if self.blocks[-1].pos[0] + block_width / 2 < self.width and not Event.flagINC1:
				Event.duration = rospy.Time.now() - self.start_event_time
				self.start_event_time = rospy.Time.now()
				print(Event.duration.to_sec())
				print("INC-CUE 602")
				################################
				self.event.rosidm.header.stamp    = rospy.Time.now()
				self.event.rosidm.event 		   = Event.inccue
				self.event.pub.publish(self.event.rosidm)
				################################
				Event.flagINC1 = True
				Event.flagINC2 = False

			# !!!! INC-PHASE event !!!!
			if self.blocks[-1].pos[0] + block_width / 2 < self.width / 2 and not Event.flagINC2:
				self.next_block_time = rospy.Time.now() + self.time_until_next_block()
				Event.duration = rospy.Time.now() - self.start_event_time
				self.start_event_time = rospy.Time.now()
				print(Event.duration.to_sec())
				print("INC-PHASE 603")
				################################
				self.event.rosidm.header.stamp    = rospy.Time.now()
				self.event.rosidm.event 		   = Event.incphase
				self.event.pub.publish(self.event.rosidm)
				################################
				Event.flagINC2 = True
				self.flag_new_cluster = True

		for bullet in self.bullets:
			bullet.update()

			# remove blocks colliding with a bullet
			for block in self.blocks:
				if bullet.hit_test(block):
					block.set_color((0, 255, 0))

			# show a red block when the player shoots even there is no block
			if bullet.gone() and not bullet.hit:
				self.blocks.append(Block((self.width / 2 - 1, 30), id=-1))
				self.blocks[-1].set_color((0, 0, 255))
		self.bullets = [x for x in self.bullets if not x.gone()]

		# key input
		key = cv2.waitKey(5)
		if self.input or key == ord(' '):
			self.bullets.append(Bullet(self.player.pos))
		if key == 0x1b:
			self.over = True

		self.input = False

		self.check_end()

	# message callback to receive input signals
	def callback(self, msg):
		self.input = True
		


# entry point
def main():
	event = Event()
	event.talker()
	rospy.init_node('carnival')

	game = Game(event)
	sub = rospy.Subscriber('/shoot', Empty, game.callback)

	game.draw()
	game.start_event_time = rospy.Time.now()	
	print("BEGIN")
	################################
	event.rosidm.header.stamp    = rospy.Time.now()
	event.rosidm.event 		   = Event.begin
	event.pub.publish(event.rosidm)
	################################
	cv2.waitKey(3000)

	while not game.is_over() and not rospy.is_shutdown():
		game.draw()
		game.update()


if __name__ == '__main__':
	main()
