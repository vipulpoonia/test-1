from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd

TERMINALS = {
	"New Bridge Landing":{"abbrev": "NH", "freq":3600},
	"Newark Broad St":{"abbrev": "ND", "freq":1800},
	"Ridgewood":{"abbrev": "RW", "freq":3600},
	"South Amboy":{"abbrev": "CH", "freq":3600},
	"Plainfield":{"abbrev": "PF", "freq":3600},
	"Newark Penn":{"abbrev": "NP", "freq":300},
	"Peapack":{"abbrev": "PC", "freq":3600},
	"Murray Hill":{"abbrev": "MH", "freq":3600},
	"Newark Airport":{"abbrev": "NA", "freq":900},
	"Bay Head":{"abbrev": "BH", "freq":3600},
	"Maplewood":{"abbrev": "MW", "freq":3600},
	"Rahway":{"abbrev": "RH", "freq":1800},
	"Bay St (Montclair)":{"abbrev": "MC", "freq":3600},
	"Long Branch":{"abbrev": "LB", "freq":3600},
	"Princeton Junction":{"abbrev": "PJ", "freq":900},
	"Waldwick":{"abbrev": "WK", "freq":3600},
	"Philadelphia":{"abbrev": "PH", "freq":300},
	"Princeton":{"abbrev": "PR", "freq":3600},
	"Montclair State University":{"abbrev": "UV", "freq":3600},
	"High Bridge":{"abbrev": "HG", "freq":3600},
	"Hackettstown":{"abbrev": "HQ", "freq":1800},
	"Lake Hopatcong":{"abbrev": "HP", "freq":3600},
	"Hoboken":{"abbrev": "HB", "freq":1800},
	"Gladstone":{"abbrev": "GL", "freq":3600},
	"Raritan":{"abbrev": "RA", "freq":1800},
	"New Brunswick":{"abbrev":  "NB", "freq":1800},
	"Suffern":{"abbrev": "SF", "freq":3600},
	"Dover":{"abbrev": "DO", "freq":1800},
	"Trenton":{"abbrev": "TR", "freq":300},
	"Metropark":{"abbrev": "MP", "freq":1800},
	"Bernardsville":{"abbrev":  "BV", "freq":3600},
	"Atlantic City Rail Terminal":{"abbrev": "AC", "freq":3600},
	"Spring Valley":{"abbrev":  "SV", "freq":3600},
	"Summit":{"abbrev": "ST", "freq":3600},
	"Mount Olive":{"abbrev":  "OL", "freq":3600},
	"Jersey Ave":{"abbrev": "JA", "freq":3600},
	"New York Penn":{"abbrev": "NY", "freq":300},
	"Port Jervis":{"abbrev": "PO", "freq":1800}
}

TRAIN_COLUMN = 4
LINE_COLUMN = 3
RAIL_DATA = "./rail_data/"

trip_stops = pd.DataFrame()

class Amtrak:
	url = "http://dv.njtransit.com/mobile/train_stops.aspx?train="
	freq = 60
	buffer_mins = 30 #research time between philly and trenton

	def __init__(self, train_id, line):
		self.id = train_id
		self.line = line
		self.created_at = datetime.now()

		self.data = []
		# self.t_scrape = self.get_t_scrape()
		self.type = "Amtrak"
		self.scrape_count = 0

	def __str__(self):
		return "Train #{}, {}".format(self.id, self.line)


class NJTransit:
	url = "http://dv.njtransit.com/mobile/train_stops.aspx?train="
	freq = 60
	buffer_mins = 2

	def __init__(self, train_id, line):
		self.id = train_id.zfill(4)
		self.line = line
		self.created_at = datetime.now()
		self.scrape_count = 0
		self.data = []
		self.type = "NJ Transit"

		self.t_scrape = self.get_t_scrape()

	def __str__(self):
		return "Train #{}, {}, next scrape: {}".format(self.id, self.line, self.t_scrape)

	# def get_type(self):
	# 	try:
	# 		is_int = int(self.id) 
	# 		return "NJ Transit"
	# 	except ValueError: 
	# 		return "Amtrak"

	def parse_table(self, soup):
		table = soup.find('table')
		return [td.text for timedelta in table.find_all('td')]

	def stop_scraping(self):
		stop = True

	def schedule_datetime(self, scheduled):
		hours, minutes, seconds = scheduled.split(":")
		hours, minutes, seconds = int(hours), int(minutes), int(seconds)
		midnight = datetime(year=self.created_at.year,\
							month=self.created_at.month,
							day=self.created_at.day)
		return midnight + timedelta(hours=hours, minutes=minutes)

	def get_t_scrape(self):
		if self.scrape_count == 0:
			if self.type == "NJ Transit":
				try:
					scheduled = trip_stops[trip_stops['block_id'] == self.id]['arrival_time'].iloc[0]
					scheduled = self.schedule_datetime(scheduled) - timedelta(minutes=self.buffer_mins)
					if datetime.now() > scheduled:
						scheduled = datetime.now()
					return scheduled
				except:
					print "exception for", self.id, self.line
					return datetime.now()
		else:
			return self.t_scrape + timedelta(seconds=self.freq)

	def scrape(self):
		now = datetime.now()
		try:
			resp = requests.get(self.url + self.id, timeout=3)
			if resp.status_code == 200:
				self.scrape_count = self.scrape_count + 1
				soup = BeautifulSoup(resp.text, "html")
				status = self.parse_table(soup)
				self.data.append([now, status])
				self.t_scrape = self.get_t_scrape()
		except requests.exceptions.ReadTimeout:
			pass


class TerminalScraper:
	terminal_url = "http://dv.njtransit.com/mobile/tid-mobile.aspx?sid="

	def __init__(self):
		self.time = datetime.now()
		self.terminals = TERMINALS
		for term, info in self.terminals.iteritems():
			info['t_scrape'] = self.time

		self.current_trains = {}
		self.completed_trains = {}

	def parse_table(self, soup):
		tables = soup.find_all('table')
		if not len(tables):
			return []
		else:
			trains = []
			for table in tables:
				if table.parent.name == 'td':
					row = table
					cells = row.find_all('td')
					trains.append({'train_id': cells[TRAIN_COLUMN].text, 
								   'line': cells[LINE_COLUMN].text})
		return trains

	#TODO: change scrape time here
	def get_departures(self, abbrev):
		try:
			resp = requests.get(self.terminal_url + abbrev, timeout=3)
			if resp.status_code == 200:
				soup = BeautifulSoup(resp.text, "html")
				return self.parse_table(soup)
			else:
				return []
		except requests.exceptions.ReadTimeout:
			print "request for", abbrev, "timed out"


	def get_train_type(self, train_id):
		try:
			is_int = int(train_id) 
			return "NJ Transit"
		except ValueError: 
			return "Amtrak"


	def find_new_trains(self, trains):
		new_trains = []
		for train in trains:
			if not train['train_id'] in self.current_trains:
				new_trains.append(train)
		return new_trains

	def create_new_trains(self, trains):
		for train in trains:
			train_type = self.get_train_type(train['train_id'])
			if train_type == "NJ Transit":
				train_obj = NJTransit(train['train_id'], train['line'])
			else:
				train_obj = Amtrak(train['train_id'], train['line'])
			self.current_trains[train['train_id']] = train_obj
			print train_obj

	def scrape_terminals(self, terminals):
		all_trains = []
		for name in terminals:
			terminal = self.terminals[name]
			trains = self.get_departures(terminal['abbrev'])
			# print terminal, trains
			#TODO: get unique
			self.terminals[name]['t_scrape'] = terminal['t_scrape'] + timedelta(seconds = terminal['freq'])
			all_trains = all_trains + trains
		return all_trains

	#TODO: implement
	def scrape_trains(self, trains):
		pass
		
	def run(self):
		loop_count = 1
		while True:
			self.time = datetime.now()

			#identify terminals to scrape
			scrape_terms = []
			for term, info in self.terminals.iteritems():
				if (info['t_scrape'] <= self.time):
					scrape_terms.append(term)

			all_trains = self.scrape_terminals(scrape_terms)
			new_trains = self.find_new_trains(all_trains)
			self.create_new_trains(new_trains)
			#identify trains to scrape
			# scrape_trains = []
			# for train, info in self.current_trains.iteritems():
			# 	if (info['t_scrape'] <= self.time):
			# 		scrape_trains.append(train)

			# self.scrape_trains(scrape_trains)

			print "loop count:", loop_count
			loop_count = loop_count + 1
			time.sleep(10)

def main():
	global trip_stops

	trips = pd.read_csv(RAIL_DATA + 'trips.txt')
	stop_times = pd.read_csv(RAIL_DATA + 'stop_times.txt')
	trip_stops = stop_times.merge(trips, on=['trip_id'])

	scraper = TerminalScraper()
	scraper.run()


if __name__ == "__main__":
    main()

