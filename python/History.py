import os
import sqlite3

from Dreadmill import Dreadmill

class History:
	def __init__(self, dreadmill, filename=os.path.expanduser("~/.dreadmill.db")):
		self.sync_value = 0
		self.dreadmill = dreadmill;
		create_schema = not(os.path.exists(filename))
		self.database = sqlite3.connect(filename)
		self.cursor = self.database.cursor()
		if create_schema:
			self.create_schema()
		
	def add_record(self, distance):
		self.cursor.execute('''insert into distances (finished, distance) values (julianday('now'), ?)''', (distance,))

	def create_schema(self):
		self.cursor.execute('''create table distances (finished datetime, distance real)''')

	def close(self):
		self.cursor.close()
		self.database.commit()
		self.database.close()

	def sync(self):
		d = self.dreadmill.get_distance()
		r = d - self.sync_value
		if r == 0: return
		self.add_record(r)
		self.sync_value = d
		self.database.commit()

	def get_distance_today(self):
		past_value = self.cursor.execute('''select sum(distance) from distances where finished > julianday(date('now', 'start of day'))''').fetchall()[0][0] 
		if not(past_value): return  (self.dreadmill.get_distance() - self.sync_value)
		else: return past_value   + (self.dreadmill.get_distance() - self.sync_value)

	def get_distance_week(self):
		past_value = self.cursor.execute('''select sum(distance) from distances where finished > julianday(date('now', '-6 days', 'weekday 1', 'start of day'))''').fetchall()[0][0] 
		if not(past_value): return  (self.dreadmill.get_distance() - self.sync_value)
		else: return past_value   + (self.dreadmill.get_distance() - self.sync_value)

	def get_distance_month(self):
		past_value = self.cursor.execute('''select sum(distance) from distances where finished > julianday(date('now', 'start of month'))''').fetchall()[0][0] 
		if not(past_value): return  (self.dreadmill.get_distance() - self.sync_value)
		else: return past_value   + (self.dreadmill.get_distance() - self.sync_value)

	def get_total_distance(self):
		past_value = self.cursor.execute('''select sum(distance) from distances''').fetchall()[0][0] 
		if not(past_value): return  (self.dreadmill.get_distance() - self.sync_value)
		else: return past_value   + (self.dreadmill.get_distance() - self.sync_value)
