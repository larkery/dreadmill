# dreadmill application object
# controls comms and database - no UI

import socket
import time

def speed2byte(speed):
	if (speed < 0.5):
		return 0
	else:
		return 1 + int(round((speed - 0.5)*20.0))

def byte2speed(byte):
	if byte == 0:
		return 0.0
	else:
		return 0.5 + (byte - 1) / 20.0

class Dreadmill:
	"""A single instance of this should be used in any app; it interfaces with the treadmill controller"""
	def __init__(self, port=35353, debug=False):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.bind( ('', port) )
		self.remote_address = None
		self.speed = None
		self.speed_changed_time = 0
		self.distance = 0
		self.speed_callbacks = []
		self.debug = debug

	def socket_ready(self):
		"""This is the socket poll callback; hook this into whatever event loop to poll on the socket"""
		data, address = self.socket.recvfrom(5)
		if len(data)>1 and (data[0], data[1]) == ('T', 'S'):
			if self.debug: print "Received ", ','.join(map(str, map(ord, data))), 'from', address
			if self.remote_address == None:
				self.remote_address = address
				if self.debug: print "Connected to ", address
			if self.remote_address == address:
				# process data
				if len(data) > 2:
					speed_byte = ord(data[2])
					speed = byte2speed(speed_byte)
					if self.debug: print 'new speed', speed, speed_byte
					self._update_speed(speed)
				else:
					print 'packet is too short!'

	def get_socket(self):
		"""Provides access to the socket, for use with the poll callback"""
		return self.socket

	def remove_speed_callback(self, callback):
		self.speed_callbacks.remove(callback)
	
	def add_speed_callback(self, callback):
		"""Add a callback for when the speed changes"""
		self.speed_callbacks.append(callback)

	def _update_speed(self, new_speed):
		"""update speed and trigger callbacks - probably only for internal use"""
		if new_speed == self.speed:
			return
		now = time.time()		
		self.distance = self.get_distance(at=now)
		self.speed_changed_time = now
		self.speed = new_speed
		for cb in self.speed_callbacks:
			cb(self)

	def get_speed(self):
		"""Get the current speed"""
		return self.speed

	def get_distance(self, at=None):
		"""Get the distance walked as the mill has been operating"""
		if self.speed == None:
			return 0
		if not(at):
			at = time.time()
		return self.distance + self.speed * ((at - self.speed_changed_time) / (3600.0))

	def send_packet(self, data):
		if self.remote_address:
			self.socket.sendto("TC" + data, self.remote_address)

	def set_speed(self, new_speed):
		byte = speed2byte(new_speed)
		if self.debug: print 'setting new speed', new_speed, byte
		if byte == 0:
			self.halt()
		else:
			self.send_packet('s' + chr(byte))

	def ping(self):
		if self.debug: print 'ping!'
		self.send_packet('p');
		return True

	def halt(self):
		"""Stop the mill"""
		self.send_packet('h')

	def faster(self):
		"""Tell the mill to go 0.1mph faster"""
		current = self.get_speed()
		if current == 0:
			self.set_speed(0.5);
		else:
			self.set_speed(current+0.1)

	def slower(self):
		"""Tell the mill to go 0.1mph slower"""
		current = self.get_speed()
		if current > 0.5:
			self.set_speed(current - 0.1);
		else:
			self.halt()

	def available(self):
		"""Returns true if a treadmill controller has been seen on the network"""
		return not(self.remote_address == None)
