#!/usr/bin/env python

import sys,os
import gtk
import socket
import gobject
import time
import sqlite3

CONFIG_PATH=os.path.expanduser("~/.dreadmill.db")

class TreadmillUI:
	def __init__(self, sock, dreadmill):
		global CONFIG_PATH
		print CONFIG_PATH
		create_database = not(os.path.exists(CONFIG_PATH))
		self.database = sqlite3.connect(CONFIG_PATH)
		if create_database:
			cursor = self.database.cursor()
			cursor.execute('''create table distances (finished datetime, distance real)''')
			cursor.close()

		self.sock = sock
		self.dreadmill = dreadmill
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect("delete-event", self.delete)
		self.window.connect("destroy", self.destroy)
		self.current_speed = 0
		self.distance = 0
		self.first_time_for_speed = None

		minus = gtk.Button('-')
		self.label = gtk.Label('stopped')

		self.distance_label = gtk.Label("0mi")

		plus = gtk.Button('+')

		stop = gtk.Button('x')

		minus.connect("clicked", self.send_message, '-')
		plus.connect("clicked", self.send_message, '+')
		stop.connect("clicked", self.send_message, 'h')
		
		box = gtk.HBox(True, 2)

		box.pack_start(stop, False, True, 0)
		stop.show()

		box.pack_start(minus, False, True, 0)
		minus.show()

		box.pack_start(self.label, False, True, 0)
		self.label.show()
		
		box.pack_start(plus, False, True, 0)
		plus.show()

		box.pack_start(self.distance_label, False, True, 2)
		self.distance_label.show()

		self.window.add(box)

		box.show()
		self.window.show()

		gobject.io_add_watch(sock, gobject.IO_IN, self.handle_data, None)
		gobject.timeout_add_seconds(1, self.refresh_distance_label)

	def refresh_distance_label(self):
		self.distance_label.set_text("%.2fmi" % self.get_distance_estimate())
		return True

	def update_speed(self, new_speed):
		# set the speed, and handle the current distance estimate
		now = time.time()
		if not(self.first_time_for_speed):
			self.first_time_for_speed = now
		else:
			if new_speed != self.current_speed:
				self.distance = self.distance + self.current_speed * (now - self.first_time_for_speed) / 3600.0
				self.current_speed = new_speed
				self.first_time_for_speed = now
				if self.current_speed == 0:
					self.label.set_text("stopped")
				else:
					self.label.set_text(str(self.current_speed)+"mph")
				self.refresh_distance_label()
	
	def get_distance_estimate(self):
		return self.distance + self.current_speed * (time.time() - self.first_time_for_speed) / 3600.0

	def handle_data(self, source, condition, foo=None):
		data, addr = source.recvfrom(4)
		if addr == self.dreadmill:
			if len(data) == 2:
				self.update_speed(0.0)
			else:
				speed = (ord(data[2])+4)/10.0
				self.update_speed(speed)

		return True

	def send_message(self, widget, msg):
		self.sock.sendto( "TC" + msg, self.dreadmill )

	def delete(self, widget, data=None):
		md = gtk.MessageDialog(self.window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Halt the treadmill as well as quitting?")
		result = md.run()
		md.destroy()
		if result == gtk.RESPONSE_YES:
			self.send_message(None, 'h')
		return False

	def destroy(self, widget, data=None):
		cursor = self.database.cursor()
		distance = self.get_distance_estimate()
		print distance
		cursor.execute('''insert into distances (finished, distance) values (julianday('now'), ?)''', (distance,) )
		cursor.close()
		self.database.commit()
		self.database.close()
		gtk.main_quit()
	
	def main(self):
		gtk.main()

def main(args):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	sock.bind( ('', 35353) )

	data, addr = sock.recvfrom(4)
	if (data[0] == 'T' and data[1] == 'S'):
		print 'found', addr

		ui = TreadmillUI(sock, addr)
		ui.main()

if __name__=="__main__":
	main(sys.argv)
