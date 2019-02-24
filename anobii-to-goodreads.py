from __future__ import print_function
import sys
import re
import csv, codecs, cStringIO


####### Customise here if needed

FINISHED = "Finito nel "
DROPPED = "Abbandonato nel "
READING = "In lettura dal "
ITA_MONTHS = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


####### do not change anything below this line

class UTF8Recoder:
	"""
	Iterator that reads an encoded stream and reencodes the input to UTF-8
	"""
	def __init__(self, f, encoding):
		self.reader = codecs.getreader(encoding)(f)
	
	def __iter__(self):
		return self
	
	def next(self):
		return self.reader.next().encode("utf-8")

class UnicodeReader:
	"""
	A CSV reader which will iterate over lines in the CSV file "f",
	which is encoded in the given encoding.
	"""
	
	def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
		f = UTF8Recoder(f, encoding)
		self.reader = csv.reader(f, dialect=dialect, **kwds)
	
	def next(self):
		row = self.reader.next()
		return [unicode(s, "utf-8") for s in row]
	
	def __iter__(self):
		return self

class UnicodeWriter:
	"""
	A CSV writer which will write rows to CSV file "f",
	which is encoded in the given encoding.
	"""
	
	def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
		# Redirect output to a queue
		self.queue = cStringIO.StringIO()
		self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
		self.stream = f
		self.encoder = codecs.getincrementalencoder(encoding)()

	def writerow(self, row):
		items = []
		for s in row:
			if type(s) == type(u"s"):
				items.append(s.encode("utf8"))
			else:
				items.append(s)

		self.writer.writerow(items)
		# Fetch UTF-8 output from the queue ...
		data = self.queue.getvalue()
		data = data.decode("utf-8")
		# ... and reencode it into the target encoding
		data = self.encoder.encode(data)
		# write to the target stream
		self.stream.write(data)
		# empty queue
		self.queue.truncate(0)

	def writerows(self, rows):
		for row in rows:
			self.writerow(row)



if __name__ == '__main__':
        if len(sys.argv) == 3:
                try:
                        in_file = open(sys.argv[1], "rb")
                        out_file = open(sys.argv[2], "wb")
                except IOError as ioe:
                        print("I/O error:", ioe, file=sys.stderr)
                        sys.exit()
        elif len(sys.argv) == 1:
                in_file = sys.stdin
                out_file = sys.stdout
                print("Using stdin / stdout", file=sys.stderr)
        else:
                print("Usage: %s [<input file> <output file>]\nIf no arguments are provided, the script uses stdin and stdout." % sys.argv[0], file=sys.stderr)
                sys.exit()
        stats = dict(read=0, gaveup=0, reading=0, toread=0)
        reader = UnicodeReader(in_file)
	reader.next() # first line is column titles
	target = []
	target.append(["Title","Author","Additional Authors","ISBN","ISBN13","My Rating","Average Rating","Publisher","Binding","Year Published",
                       "Original Publication Year","Date Read","Date Added","Bookshelves","My Review","Spoiler","Private Notes","Recommended For","Recommended By"])

	isbn_re = re.compile("\[([\w\d]+)\]")
        date_re = re.compile("\[([\dx]{4})-([\dx]{2})-([\dx]{2})\]")
        human_date_re = re.compile("([\d]{2})/(\w{3})/([\d]{4}) 00:00:00")
	for l in reader:
	        m = isbn_re.match(l[0])
	        if m is None or len(m.groups()) != 1:
	                print("Invalid ISBN in line ", l, file=sys.stderr)
	                continue
	        isbn = m.groups()[0]
		title = l[1]
	        if l[2] != "":
	                title += ": " + l[2]
		author = l[3]
		edition = l[4]
		pages = l[5]
		publisher = l[6]

		date_publ = ""
                m = date_re.match(l[7])
                if m is not None:
                        (year, month, day) = m.groups()
                        if day == 'xx':
                                day = 1
                        if month == 'xx':
                                month = 1
                        if year == 'xxxx':
                                year = 1970
                        date_publ = "%04d-%02d-%02d" % tuple(map(int, (year, month, day)))

		privnote = l[8]
		comment = l[10]

		status = l[11]
                if status.startswith(FINISHED):
                        date_read = status[len(FINISHED):]
                        tags = "read"
                        stats['read'] += 1
                elif status.startswith(DROPPED):
                        date_read = status[len(DROPPED):]
                        tags = "gave-up-on"
                        stats['gaveup'] += 1
                elif status.startswith(READING):
                        date_read = status[len(READING):]
                        tags = "currently-reading"
                        stats['reading'] += 1
                else:
                        date_read = ""
                        tags = "to-read"
                        stats['toread'] += 1
                if date_read != "" :
                        m = human_date_re.match(date_read)
                        if m is None or m.groups()[1] not in ITA_MONTHS:
                                print("Invalid date format:", date_read, file=sys.stderr)
                                date_read = ""
                        else:
                                (day, month, year) = m.groups()
                                month = ITA_MONTHS.index(month) + 1
                                date_read = "%04d-%02d-%02d" % (int(year), month, int(day))

                date_added = ""  # no date added information in Anobii's export file

		rating = l[12]
		
		tline = [title, author, "", isbn, "", rating, "", publisher, edition, "", date_publ, date_read, date_added, tags, comment, "", privnote, "", ""]
		target.append(tline)
	
	writer = UnicodeWriter(out_file, dialect='excel', quoting=csv.QUOTE_NONNUMERIC)
	writer.writerows(target)
	
	print("Done! Stats:", stats, file=sys.stderr)

