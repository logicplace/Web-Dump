#!/usr/bin/env python
#-*- coding:utf-8 -*-

import re
import os
import sys
import urllib
import urllib2
import mimetypes
from random import randint as rand
from urlparse import urlparse
from optparse import OptionParser, SUPPRESS_HELP

# TODO: Extensively test HTTP error handling

class CounterError(Exception): pass
class MarkerError(Exception): pass

class Counter(object):
	"""
	Handles counters in URLs
	"""

	# 1: Right-pad; 2: Padding char; 3: Width
	# 4: Name
	# 5: Order number (or l if linked); 6: 404 tolerance (or f if quit when found)
	# 7: Digits; 8: Lower bound; 9: Upper bound; 10: Reset behavior
	syntax = re.compile(
		r'(?:(-??)(.?)([0-9]+))?' # FORMATTING: [RIGHT-PAD] [PADDING-CHAR] WIDTH
		r'([a-zA-Z])'             # Name
		r'(?:'                    # HowTo
			r'(?:!([0-9]+|l))|'   # Order number or is a link
			r'(?:\*([0-9]+|f))|'  # 404 tolerance or quit when found
			r'(?:\[((?:[0-9]-[0-9]|[a-z]-[a-z]|[A-Z]-[A-Z]|\\-|\\|.)+)\])|' # Digits
			r'(?:\{((?:[^,}]+|\\,|\\}|\\)+)?,((?:[^,}]+|\\,|\\}|\\)+)?\})|' # Limits
			r'([+\-])'            # Don't reset the counter (second one is with returning)
		r')*'                     # HowTos can be in any order, and are entirely optional
	)

	digits_syntax = re.compile(r'([0-9a-zA-Z])-([0-9a-zA-Z])')

	escape = re.compile(r'\\(.)')

	@staticmethod
	def unescape_digits(mo): return mo.group(1) if mo.group(1) in "\\-" else mo.group(0)

	@staticmethod
	def unescape_limits(mo): return mo.group(1) if mo.group(1) in "\\,}" else mo.group(0)

	def __init__(self, counter, taken_orders):
		tokens = Counter.syntax.match(counter).groups(None)
		self.pad_right = bool(tokens[0])
		self.no_zero   = tokens[6] and tokens[6][0] == "*"
		self.digits    = (
			tokens[6][1:]
			if self.no_zero or tokens[6] and tokens[6][0] == "\\" else
			tokens[6] or "0123456789"
		)
		ranges = Counter.digits_syntax.split(self.digits)
		self.digits = ""
		for i in range(0, len(ranges) - 1, 3):
			self.digits += ranges[i]
			start, end = ord(ranges[i + 1]), ord(ranges[i + 2])
			for o in (range(start, end + 1) if end >= start else range(start, end - 1, -1)):
				self.digits += chr(o)
			#endfor
		#endfor
		self.digits += ranges[-1]
		self.digits = Counter.escape.sub(Counter.unescape_digits, self.digits)
		self.pad_char  = tokens[1] or self.digits[0]
		self.pad_width = (int(tokens[2]) if tokens[2] else None)
		self.name      = tokens[3]
		self.linked    = tokens[4] == "l"
		self.order     = None if self.linked else int(tokens[4] or 1)
		if self.order:
			while self.order in taken_orders: self.order += 1
			taken_orders.append(self.order)
		#endif
		self.on_found  = tokens[5] == "f"
		self.error     = None if self.on_found else (int(tokens[5]) if tokens[5] else None)
		self.value = self.lower = (
			Counter.escape.sub(Counter.unescape_limits, tokens[7])
			if tokens[7] else
			(self.digits[0] if self.no_zero else self.digits[1])
		)
		self.upper     = Counter.escape.sub(Counter.unescape_limits, tokens[8]) if tokens[8] else None
		self.reset     = {None: 0, "+": 1, "-": 2}[tokens[9]]

		self.first_error = None
		self.error_count = 0
	#enddef

	def link(self, counters):
		if self.linked:
			for x in counters:
				if x.name == self.name and not x.linked:
					self.linked = x
					return
				#endif
			#endfor
			raise CounterError(self.name, "Tried to link counter, but there was nothing to link with.")
		#endif
	#enddef

	def inc(self):
		"""
		Incriment value based on digits and etc.
		Return True if the next counter should be incrimented, False if not.
		"""

		if self.linked: return False

		# Check error status
		if self.error is not None and self.error_count > self.error:
			self.error_count = 0
			if self.reset == 0: self.value = self.lower
			elif self.reset == 2: self.value = self.first_error
			self.first_error = None
			return True
		elif self.on_found and self.error_count == 0:
			return True
		#endif

		# Check if this is at the max value
		if self.upper and self.value == self.upper:
			self.value = self.lower
			return True
		#endif

		# Otherwise, incriment the digits
		new_value, didnt_inc = "", True

		for i in range(len(self.value) - 1, -1, -1):
			if self.value[i] == self.digits[-1]:
				# Roll over all maxed digits.
				new_value = self.digits[0] + new_value
			else:
				# Incriment last digit, and copy whatever's left.
				new_value = (
					self.value[0:i]
					+ self.digits[self.digits.index(self.value[i]) + 1]
					+ new_value
				)
				didnt_inc = False
				break
			#endif
		#endfor

		# If we didn't incriment a final value (ie. all digits rolled over)
		# then prepend a new digit.
		if didnt_inc:
			if self.no_zero: new_value = self.digits[0] + new_value
			else: new_value = self.digits[1] + new_value
		#endif

		self.value = new_value
		return False
	#enddef

	def result(self, error):
		"""
		Deals with the result of the last query.
		"""
		if self.linked: return
		if error:
			if self.first_error is None: self.first_error = self.value
			self.error_count += 1
		else:
			self.first_error = None
			self.error_count = 0
		#endif
	#enddef

	def __unicode__(self):
		"""
		Returns string of value suitable for a URL
		"""
		if self.pad_width:
			padding = self.pad_char * max(self.pad_width - len(self.true_value()), 0)
			if self.pad_right: return urllib.quote(self.true_value()) + padding
			else: return padding + urllib.quote(self.true_value())
		else: return urllib.quote(self.true_value())
	#enddef

	def cont(self):
		"""
		Returns a string suitable for inclusion in a continuance operation
		"""
		if self.linked: return None
		return self.name + ":" + self.value
	#enddef

	def true_value(self):
		if self.linked: return self.linked.true_value()
		else: return self.value
	#enddef

	def debug(self):
		ret = u"%s:\n" % self.name
		ret += " Digits: %s\n" % self.digits
		if self.no_zero: ret += " There is no zero in this system\n"
		if self.pad_width: ret += ' Padding: "%s" to %s on %s\n' % (
			self.pad_char, self.pad_width, "right" if self.pad_right else "left"
		)
		if self.linked: ret += " Linked\n"
		else: ret += " Order: %i\n" % self.order
		if self.on_found: ret += " Reset on found\n"
		elif self.error: ret += " Error tolerance: %i\n" % self.error
		else: ret += " Error tolerance: infinite\n"
		ret += " Count between %s and %s\n" % (
			self.lower,
			self.upper if self.upper else "infinity"
		)
		if self.reset == 0: ret += " Reset on maxed or errors\n"
		elif self.reset == 1: ret += " Only reset when maxed\n"
		elif self.reset == 2: ret += " Reset completely when maxed, reset to first error on errors\n"
		ret += " Current value: %s\n" % self.true_value()
		if self.first_error: ret += " Error stats: %i starting from %s\n" % (self.error_count, self.first_error)

		return ret.rstrip()
	#enddef
#endclass

class Marker(object):
	"""
	Handles dynamic pieces of filenames
	"""

	# 1: Right-align; 2: Pad char; 3: Padding width; 4: Name
	# 5: Group index; 6: Unique index
	# 7: URL level index; 8: URL level final range index; 9: Continue to end marker
	syntax = re.compile(
		r'%'
			r'(?:(-??)(.?)([0-9]+))?'
			r'([a-zA-Z])'
		r'|#'
			r'([0-9]+)'
		r'|#(i)'
		r'|@(-?[0-9]+)(?:-(-?[0-9]+)|(\+))?'
	)

	def __init__(self, marker):
		self.marker = marker
		tokens = Marker.syntax.match(marker).groups(None)
		if tokens[4]:
			self.type = 2
			self.group = int(tokens[4])
		elif tokens[3]:
			self.type = 1
			self.pad_right = bool(tokens[0])
			self.pad_char = tokens[1] or ""
			self.pad_width = int(tokens[2]) if tokens[2] else None
			self.name = tokens[3]
		elif tokens[6]:
			self.type = 4
			self.index = int(tokens[6])
			if tokens[7]:
				self.end = int(tokens[7])
				if self.index < 0 and self.end > 0: self.end = -self.end
			else: self.end = None
			if tokens[8]: self.tail = True
			else: self.tail = False
		else: self.type = 3
	#enddef

	def form(self, groups, url):
		if self.type == 1:
			counter = None
			for x in counters:
				if x.name == self.name and not x.linked:
					counter = x
					break
				#endif
			#endfor
			if not counter: return ""
			if self.pad_width:
				padding = self.pad_char * max(self.pad_width - len(counter.true_value()), 0)
				if pad_right: return counter.true_value() + padding
				else: return padding + counter.true_value()
			else: return counter.true_value()
		elif self.type == 2: return groups[self.group]
		elif self.type == 3: return groups[0]
		elif self.type == 4:
			urlbits = (url[url.index("://") + 3:] if "://" in url else url).split("/")[1:]
			try:
				if self.tail: return "/".join(urlbits[self.index:])
				elif self.end is not None: return "/".join(urlbits[self.index : self.end])
				else: return urlbits[self.index]
			except IndexError:
				raise MarkerError(self.marker, "Indexing error on URL, only %i levels." % length(urlbits))
			#endtry
		#endif
	#enddef
#endclass

# 1: Counter
url_syntax = re.compile(r'(?<!%)%(?!%)((?:\[(?:\\.|[^\]])*\]|\{(?:\\.|[^\}])*\}|[^;])+);')
def parse_url(url):
	"""
	Parses the counters from the URL.
	Returns a list alternating literal text and counters.
	"""
	splitted = url_syntax.split(url)

	orders = []
	for i in range(len(splitted)):
		if i % 2 == 0: splitted[i] = splitted[i].replace("%%", "%")
		else: splitted[i] = Counter(splitted[i], orders)
	#endfor

	return splitted
#enddef

marker_syntax = re.compile(r'((?<!%)%(?:-??.?[0-9]+)?[a-zA-Z]|(?<!#)#[0-9]+|(?<!#)#i|(?<!@)@-?[0-9]+(?:--?[0-9]+|\+));?')
def parse_filename(filename):
	splitted = marker_syntax.split(filename)

	for i in range(len(splitted)):
		if i % 2 == 0: splitted[i] = splitted[i].replace("%%", "%").replace("##", "#").replace("@@", "@")
		else: splitted[i] = Marker(splitted[i])
	#endfor

	return splitted
#enddef

mime2ext_overrides = {
	"text/plain": ".txt",
	"image/jpeg": ".jpg",
}
def download_file(url, fileform, args, headers=[]):
	"""
	Download contents of page at url to filename
	Return if successful
	"""
	# Download the data
	data, mime = download_page(url, return_mime=True, headers=headers)
	if data is None: return False

	# Make filename if necessary
	if fileform:
		filename = ''.join(map(
			lambda y: y.form(args, url) if isinstance(y, Marker) else y,
			fileform
		))
	if not fileform:
		url = urllib.unquote(urlparse(url).path)
		filename = url[url.rfind("/") + 1:]
		if not options.dont_mime_ext and "." not in filename:
			if mime in mime2ext_overrides: filename += mime2ext_overrides[mime]
			else: filename += mimetypes.guess_extension(mime, False)
		#endif
	#endif

	# Ensure necessary directories exist
	try: os.makedirs(os.path.dirname(filename))
	except OSError as err:
		if err.errno == 17: pass
	#endtry

	# Write file
	print_info(u"   To: %s" % filename)
	f = open(filename, "w")
	f.write(data)
	f.close()
	return True
#enddef

def download_page(url, return_mime=False, return_baseurl=False, headers=[]):
	"""
	Download page and return contents
	"""
	print_info(u"   Downloading: %s" % url)
	try:
		opener = urllib2.build_opener()
		opener.addheaders.extend(headers)
		handle = opener.open(url)
		ret = handle.read()
		if return_mime: mime = (lambda x: x.getmaintype() + "/" + x.getsubtype())(handle.info())
		if return_baseurl: baseurl = handle.geturl()
		handle.close()
		if return_baseurl: return (ret, baseurl)
		if return_mime: return (ret, mime)
		return ret
	except urllib2.HTTPError as err:
		print_err(u"   HTTP Error: %i" % err.code)
	#endtry
	if return_mime or return_baseurl: return None, None
	return None
#enddef

def notNone(element): return element is not None

def ordinal(num):
	num = str(num)
	if not num: num == "0th"
	elif len(num) >= 2 and num[-2] == "1": num += "th"
	elif num[-1] == "1": num += "st"
	elif num[-1] == "2": num += "nd"
	elif num[-1] == "3": num += "rd"
	else: num += "th"
	return num
#enddef

def print_err(err): sys.stderr.write(str(err) + "\n")

def print_info(info):
	if options.print_urls or options.print_scans: sys.stderr.write(str(info) + "\n")
	else: print(info)
#enddef

def print_data(data): print(data)

def main():
	global options, counters
	parser = OptionParser(version="5",
		description="Dump v5 by Wa (logicplace.com)\n",
		usage="Usage: %prog [options] address [address...]"
	)
	parser.add_option("-o", "--folder", default=os.curdir,
		help="Set the output folder. Default: Current directory"
	)
	parser.add_option("-f", "--filename",
		help="Set the filename format. Default: Extracted from URL"
	)
	parser.add_option("-s", "--scan",
		help="Given URL is a webpage, that needs to be parsed for the link to"
		" download, found by the given regex. Default is to just download the url."
	)
	parser.add_option("-c", "--continue", dest="cont",
		help="Continue from the given string. Acceptable strings are shown"
		" before each download. Do not include the brackets."
	)
	parser.add_option("-p", "--print-urls", action="store_true",
		help="Rather than download anything, simply print the URLs. "
		"Note that this does not check for existence."
	)
	parser.add_option("-P", "--print-scans", action="store_true",
		help="Download the page, scan it for URLs, and only print those. "
		"Note that this does not check for existence of the files."
	)
	parser.add_option("-m", "--dont-mime-ext", action="store_true",
		help="When automatically making filenames, "
		"don't guess missing extensions by mime-type."
	)
	parser.add_option("-d", action="count", dest="debug",
		help=SUPPRESS_HELP
	)
	parser.add_option("-C", "--cookie", default="",
		help="Pass a cookie string. You can find this by going to the page and typing javascript:alert(document.cookie) in the address bar."
	)

	# Merge args from stdin with args from command line
	args = sys.argv
	if not sys.stdin.isatty():
		args = args + reduce(
			(lambda x, y: x + y),
			map((lambda x: x.rstrip().split(" ", 1)), sys.stdin.readlines())
		)
	#endif
	options, args = parser.parse_args(args)
	args = args[1:]

	if len(args) == 0 or args[0] in ["/?", "/h"]:
		parser.print_help()
		return 0
	#endif

	options.folder = os.path.normpath(options.folder)

	# Parse the given URLs
	parsed = map(parse_url, args)

	# Order the counters
	counters = []
	for url in parsed:
		counters.append(sorted(
			[url[i] for i in range(1, len(url), 2)],
			key=lambda x: x.order
		))
	#endfor

	# Split countinue string up
	start = 0
	if options.cont:
		continuing = dict(map(lambda x: tuple(x.split(":", 1)), options.cont.split(",")))
		if "link" in continuing: start = int(continuing["link"])
	#endif

	# Make sure things that need to be linked up are
	for counter in counters:
		for x in counter:
			x.link(counter)
			if options.cont and x.name in continuing: x.value = continuing[x.name]
		#endfor
	#endfor

	if options.debug == 2:
		for i, url in enumerate(parsed):
			print_info("=== URL: %s ===" % ''.join(map(
				(lambda x: x if type(x) in [str, unicode] else "%" + x.name + ";"),
				url
			)))
			print_info("\n".join([x.debug() for x in counters[i]]))
		#endfor
	#endif

	# Parse the given filename
	if options.filename: fileform = parse_filename(options.filename)
	else: fileform = None

	# TODO: Debug thing for filename

	# Compile the scan
	if options.scan:
		scan_group = re.match(r'(.*)\|([0-9]+)$', options.scan)
		if scan_group:
			scan = re.compile(scan_group.group(1))
			scan_group = int(scan_group.group(2))
		else:
			scan = re.compile(options.scan)
			scan_group = 0
		#endif
	else: scan = None

	# Make headers
	headers = []
	if options.cookie: headers.append(("Cookie", options.cookie))

	# TODO: Debug thing for headers 

	if options.debug: print "Starting from %s url" % ordinal(start)
	for idx, url_parts in enumerate(parsed):
		if idx < start: continue
		counter = counters[idx]
		increased = counter[0] if counter else None
		last = True # This is for static URLs that don't need to loop
		while True:
			# Construct URL string
			url = ''.join(map(unicode, url_parts))

			if options.print_urls: print_data(url)
			else:
				# Attempt download
				print_info("[%s]" % ",".join(
					(["link:%i" % idx] if len(parsed) > 1 else []) +
					filter(notNone, map(lambda x: x.cont(), counter))
				))
				if scan:
					page, baseurl = download_page(url, return_baseurl=True, headers=headers)
					if page is None: error = True
					else:
						error, i = False, 0
						baseurl, basepath = (lambda x: (
							"%s://%s" % (x.scheme, x.netloc),
							x.path[0:x.path.rfind("/")] + "/"
						))(urlparse(baseurl))
						for x in scan.finditer(page):
							args = [unicode(i)] + list(x.groups())
							download = x.group(scan_group)
							if "://" not in download:
								if download[0] == "/": download = baseurl + download
								else: download = baseurl + basepath + download
							#endif

							if options.print_scans: print_data(download)
							else: download_file(download, fileform, args, headers=headers + [("Referer", baseurl)])
							i += 1
						#endfor
					#endif
				else: error = not download_file(url, fileform, [], headers=headers)
				# TODO: Not sure how to distribute blame at the moment
				# So yeah this is just a trial I guess
				if increased: increased.result(error)
			#endif

			# Increase counters
			for increased in counter:
				last = increased.inc()
				if not last: break
			#endfor

			# If the last counter tries to increase the next counter, we're done
			if last: break
		#endwhile
	#endfor
#endif

if __name__ == "__main__":
	try: sys.exit(main())
	except CounterError as err: print_err("Fatal error in counter %s: %s" % err.args)
	except MarkerError as err: print_err("Fatal error in filename piece %s: %s" % err.args)
	except (EOFError, KeyboardInterrupt): print_err("\nProgram terminated")
#endif
