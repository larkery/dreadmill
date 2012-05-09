#!/usr/bin/env python

from Dreadmill import Dreadmill
from History import History
import gobject
import gtk
import sys,os
import appindicator
import gnome.ui
import argparse

global CONVERSION_FACTOR, SPEED_STRING, DISTANCE_STRING
CONVERSION_FACTOR = 0.621371192
SPEED_STRING = "mph"
DISTANCE_STRING = "mi"

def convert(km):
	return km * CONVERSION_FACTOR

class App:
	def __init__(self,port=35353, debug=False):
		gnome.program_init("Dreadmill UI", "1.0")
		client = gnome.ui.master_client()
		command = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
		client.set_restart_style(gnome.ui.RESTART_IF_RUNNING)
		try: client.set_restart_command([command] + sys.argv[1:])
		except TypeError:
			client.set_restart_command(len(sys.argv), [command] + sys.argv[1:])
		client.connect('die', self.die)
		client.connect('save-yourself',  self.save_state)

		self.dreadmill = Dreadmill(port=port, debug=debug)
		self.history = History(self.dreadmill)
		
		# create window
		self.control_window = ControlWindow(self.dreadmill, self)
		# add app indicator
		self.indicator = Indicator(self.dreadmill, self)
		
		# hook callback for IO
		gobject.io_add_watch(self.dreadmill.get_socket(), gobject.IO_IN, self.prod_dreadmill, None)
		gobject.timeout_add_seconds(3, self.dreadmill.ping)

	def prod_dreadmill(self, source, condition, misc=None):
		self.dreadmill.socket_ready()
		return True

	def show_control_window(self):
		self.control_window.show()

	def main(self):
		gtk.main()

	def get_distance_today(self):
		return self.history.get_distance_today()

	def destroy(self):
		self.history.sync()
		self.history.close()
		gtk.main_quit()

	def die(self, *args):
		self.destroy()

	def save_state(self, *args):
		self.history.sync()

class Indicator:
	def __init__(self, dreadmill, app):
		self.resume_to_speed = 0
		self.dreadmill = dreadmill
		self.app = app
		icon_path = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + "indicator.png"
		self.indicator = appindicator.Indicator("dreadmill", icon_path,
			appindicator.CATEGORY_APPLICATION_STATUS)
		self.indicator.set_status(appindicator.STATUS_ACTIVE)

		menu = gtk.Menu()
		quit_item = gtk.MenuItem("Quit")
		quit_item.connect("activate", self.quit_app)
		quit_item.show()

		show_window = gtk.MenuItem("Show Controls...")
		show_window.connect("activate", self.show_controls)
		show_window.show()
		menu.append(show_window)

		pause = gtk.MenuItem("Pause")
		pause.connect("activate", self.pause_or_resume)
		pause.show()
		menu.append(pause)

		set_speed = gtk.MenuItem("Set Speed")
		set_speed.show()
		menu.append(set_speed)
		
		speed_menu = gtk.Menu()
		set_speed.set_submenu(speed_menu)
		speed_menu.show()
		
		halt_item = gtk.MenuItem("Halt")
		halt_item.show()

		halt_item.connect("activate", lambda w:self.dreadmill.halt())

		speed_menu.append(halt_item)
		sep = gtk.SeparatorMenuItem()
		sep.show()		
		speed_menu.append(sep)
		for i in range(5, 55, 5):
			k = i/10.0
			speed_item = gtk.MenuItem("%.1fkph" % k)
			speed_item.show()
			speed_menu.append(speed_item)
			
			speed_item.connect("activate", lambda w, s:self.dreadmill.set_speed(s), k)


		sep = gtk.SeparatorMenuItem()
		sep.show()		
		menu.append(sep)

		menu.append(quit_item)
		self.indicator.set_menu(menu)
		gobject.timeout_add_seconds(1, self.update_distance_label)

	def quit_app(self, widget, data=None):
		self.app.destroy()

	def show_controls(self, widget, data=None):
		self.app.show_control_window()

	def update_distance_label(self):
		self.indicator.set_label("%.2f%s" % (convert(self.app.get_distance_today()), DISTANCE_STRING))
		return True

	def pause_or_resume(self, widget, data=None):
		if self.dreadmill.get_speed() == 0:
			self.dreadmill.set_speed(self.resume_to_speed)
			widget.set_label("Pause")
		else:
			self.resume_to_speed = self.dreadmill.get_speed()
			self.dreadmill.halt()
			widget.set_label("Resume (%.2f%s)" % (convert(self.resume_to_speed), SPEED_STRING))

class ControlWindow:
	def __init__(self, dreadmill, app):
		settings = gtk.settings_get_default()
		settings.props.gtk_button_images = True

		self.app = app
		self.dreadmill = dreadmill
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect("delete-event", self.delete)
		self.window.connect("destroy", self.destroy)
		self.speed_label = gtk.Label("stopped")
		self.distance_label = gtk.Label("0.00%s" % DISTANCE_STRING)
		
		im = gtk.Image()
		im.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_BUTTON)
		stop = gtk.Button()
		stop.set_image(im)
		slower = gtk.Button()
		im = gtk.Image()
		im.set_from_stock(gtk.STOCK_REMOVE, gtk.ICON_SIZE_BUTTON)
		slower.set_image(im)
		faster = gtk.Button()
		im = gtk.Image()
		im.set_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON)
		faster.set_image(im)

		stop.connect("clicked", lambda x,y: dreadmill.halt(), None)
		slower.connect("clicked", lambda x,y:dreadmill.slower(), None)
		faster.connect("clicked", lambda x,y:dreadmill.faster(), None)

		box = gtk.HBox(True, 2)
		box.pack_start(stop, False, True, 0)
		stop.show()
		box.pack_start(slower, False, True, 0)
		slower.show()
		box.pack_start(self.speed_label, False, True, 0)
		self.speed_label.show()
		box.pack_start(faster, False, True, 0)
		faster.show()
		

		top_box = gtk.VBox(False, 2)
		top_box.pack_start(box, False, True, 0)

		table = gtk.Table(rows=2, columns=4)

		top_box.pack_start(table, True, True, 2)
		table.show()
		lbl =gtk.Label("Day:")
		lbl.set_alignment(1, .5)
		table.attach(lbl, 0, 1, 0, 1)

		lbl.show()

		self.distance_label.set_alignment(0.1, .5)
		table.attach(self.distance_label, 1, 2, 0, 1)

		lbl =gtk.Label("Week:")
		lbl.set_alignment(1, .5)
		table.attach(lbl, 2, 3, 0, 1)
		lbl.show()

		self.week_label = gtk.Label("0" + DISTANCE_STRING)
		table.attach(self.week_label, 3, 4, 0, 1)
		self.week_label.set_alignment(0.1, .5)
		self.week_label.show()

		lbl =gtk.Label("Month:")
		lbl.set_alignment(1, .5)
		table.attach(lbl, 0, 1, 1, 2)
		lbl.show()

		self.month_label = gtk.Label("0" + DISTANCE_STRING)
		table.attach(self.month_label, 1, 2, 1, 2)
		self.month_label.set_alignment(0.1, .5)
		self.month_label.show()

		lbl =gtk.Label("All:")
		lbl.set_alignment(1, .5)
		table.attach(lbl, 2, 3, 1, 2)
		lbl.show()

		self.all_label = gtk.Label("0" + DISTANCE_STRING)
		table.attach(self.all_label, 3, 4, 1, 2)
		self.all_label.set_alignment(0.1, .5)
		self.all_label.show()

		self.distance_label.show()

		self.window.add(top_box)
		top_box.show()
		box.show()

		self.window.set_keep_above(True)
		self.window.set_resizable(False)
		self.window.set_title("DREADMILL")

	def show(self):
		if self.window.get_property("visible"):
			return
		# add timer
		gobject.timeout_add_seconds(1, self.update_distance)
		self.update_speed(self.dreadmill)
		self.dreadmill.add_speed_callback(self.update_speed)
		self.window.show()

	def update_speed(self, dreadmill):
		speed = dreadmill.get_speed()
		if speed == None:
			self.speed_label.set_text("no conn")
		elif speed == 0:
			self.speed_label.set_text("stopped")
		else:
			self.speed_label.set_text("%.2f%s" % (convert(speed), SPEED_STRING))

	def update_distance(self):
		self.distance_label.set_text("%.2f%s" % (convert(self.app.history.get_distance_today()), DISTANCE_STRING))
		self.week_label.set_text("%.2f%s" % (convert(self.app.history.get_distance_week()), DISTANCE_STRING))
		self.month_label.set_text("%.2f%s" % (convert(self.app.history.get_distance_month()), DISTANCE_STRING))
		self.all_label.set_text("%.2f%s" % (convert(self.app.history.get_total_distance()), DISTANCE_STRING))
		return self.window.get_property("visible") # disable timer if window invisible

	def delete(self, widget, data=None):
		self.window.hide()
		self.dreadmill.remove_speed_callback(self.update_speed)
		return True

	def destroy(self, widget, data=None):
		pass

def main(args):
	parser = argparse.ArgumentParser(description="Argument parser for dreadmill")
	parser.add_argument('-D', action='store_true', default=False, dest="debug")
	parser.add_argument('-p', action='store', default=35353, type=int, dest="port")
	
	parsed = parser.parse_args(args[1:])

	app = App(port=parsed.port, debug=parsed.debug)
	app.main()

if __name__ == "__main__":
	main(sys.argv)
