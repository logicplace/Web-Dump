#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os
import re
import urllib2
import traceback
from random import randint as rand

sOutFolder = "./"
sFileFormat = "*"
reLinkSearch = None
iDebugLevel = 0

def cast(x,y,bCanBeNone=True):
	if type(y) in [list,tuple]:
		tOrig = type(x)
		x = list(x)
		for iI in range(min(len(x),len(y))):
			if x[iI] is not None or not bCanBeNone:
				x[iI] = y[iI](x[iI])
			#endif
		#endfor
		return tOrig(x)
	elif type(y) is type:
		return y(x)
	else:
		raise TypeError("Second argument must be a type or list of types.")
	#endif
#enddef

def EnsureIndex(lX,iLen,vVal=None):
	if iLen >= len(lX):
		lX.extend([vVal] * (iLen+1 - len(lX)))
	#endif
#enddef

def IncVia(sNum,sDigits):
	bDoBreak = False
	for iI in range(len(sNum)-1,-1,-1):
		iIdx = sDigits.find(sNum[iI])
		if iIdx == len(sDigits)-1:
			if sDigits[0] == '\0': iIdx = 1
			else: iIdx = 0
		else:
			iIdx += 1
			bDoBreak = True
		#endif
		sNum = sNum[:iI] + sDigits[iIdx] + sNum[iI+1:]
		if bDoBreak: break
	#endfor
	if not bDoBreak: sNum = sDigits[min(1,len(sDigits))] + sNum
	return sNum
#enddef

reFmtOnly = re.compile(r'(?<!%)%(?!%)(?:(-)??(.)?([0-9]+))?([a-zA-Z])')
def Format(sStr,dNumMap):
	global reFmtOnly
	def _Format(moX):
		bRPad,sPadChar,iWidth,sName = cast(
			moX.groups(),
			[bool,str,int,str]
		)
		if bRPad is None: bRPad = False
		if sPadChar is None:
			sPadChar = dNumMap[sName][2][2][0]
			if sPadChar == '\0': sPadChar = ""
		#endif
		if iWidth is None: iWidth = 1

		sRet = dNumMap[sName][0]
		iDiff = iWidth-len(sRet)
		if iDiff > 0:
			sX = sPadChar * iDiff
			if bRPad: sRet = sRet + sX
			else: sRet = sX + sRet
		#endif
		return sRet
	#enddef
	return reFmtOnly.sub(_Format,sStr).replace("%%","%")
#enddef

def DownloadFile(sUrl,dNumMap):
	global sOutFolder,sFileFormat,reLinkSearch,iDebugLevel
	lGroups=None
	try:
		if reLinkSearch is not None:
			hUrl = urllib2.urlopen(sUrl)
			sPage = hUrl.read()
			hUrl.close()
			moLink = reLinkSearch.search(sPage)
			if moLink is not None:
				sUrl = moLink.group(0)
				lGroups = [""] + list(moLink.groups())
			else:
				sys.stderr.write("Link not found in: %s\n" % sUrl)
				return 1
			#endif
		#endif
		if sFileFormat == "*": sFilename = sUrl[sUrl.rfind("/")+1:]
		else:
			sFilename = Format(sFileFormat,dNumMap)
			if lGroups is not None:
				for iX in range(len(lGroups)):
					sFilename = sFilename.replace("#"+str(iX),lGroups[iX])
				#endfor
			#endif
			sFilename = sFilename.replace("%%","%").replace("##","#")
		#endif
		sFilename = sOutFolder + sFilename
		print("[%s]" % (','.join(map(lambda x: x+":"+dNumMap[x][0],dNumMap))))
		print("   Downloading: %s" % sUrl)
		print("   To: %s" % sFilename)
		try: os.makedirs(sFilename[0:sFilename.rfind("/")])
		except OSError as err:
			if err.errno != 17: raise
		#endtry
		hOut = open(sFilename,'wb')
		hUrl = urllib2.urlopen(sUrl)
		hOut.write(hUrl.read())
		hUrl.close()
		hOut.close()
		return 0
	except urllib2.HTTPError as err:
		print("   HTTP Error: %i" % err.code)
		#if err.code == 404: return 1
		return 1
	except urllib2.URLError:
		traceback.print_exc()
		return 2
	except KeyboardInterrupt:
		sys.exit()
	except:
		traceback.print_exc()
		return 3
	#endtry
#enddef

def main():
	global sOutFolder, sFileFormat, reLinkSearch, iDebugLevel
	# Compound stdin and command line as arguments
	lArgs = []
	if not sys.stdin.isatty():
		lTemp = sys.stdin.readlines()
		lArgs.append(lTemp[0])
		for sX in lTemp[1:]:
			lArgs.extend(sX.strip().split(" ",1))
		#endfor
	#endif
	if len(sys.argv) > 1: lArgs.extend(sys.argv[1:])

	# TODO: Check stdin if no args are passed
	if len(lArgs) == 0 or re.match(r'[\-/]([?h]|-?help)',lArgs[0]):
		print("Dump v3 by Wa (logicplace.com)\n"+
			("%s url [options]\n" % re.match("(?:.*/)?([^/]+)(?:\.py)?"
			" -o  Set the output folder. Default: Current directory\n"
			" -f  Set the fileformat. Default: Extracted from URL\n"
			" -s  Given URL is a webpage, that needs to be parsed for the link to download,\n"
			"     found by the given regex. Default is to just download the url.\n"
			" -c  Continue from the given string. Acceptable strings are shown before each\n"
			"     download. Do not include the brackets.\n"
			"See readme for detailed syntax information."
			, sys.argv[0]).group(1))
		)
	else:
		# Enumerate command line
		sUrlFormat = lArgs[0]
		sContinue = ""
		for iI in range(1,len(lArgs),2):
			if   lArgs[iI] == "-o": sOutFolder = lArgs[iI+1]
			elif lArgs[iI] == "-f": sFileFormat = lArgs[iI+1]
			elif lArgs[iI] == "-s": reLinkSearch = re.compile(lArgs[iI+1])
			elif lArgs[iI] == "-d": iDebugLevel = int(lArgs[iI+1])
			elif lArgs[iI] == "-c": sContinue = lArgs[iI+1]
		#endfor

		# TODO: OS independant
		if sOutFolder[-1] not in ['/','\\']: sOutFolder += '/'

		# Evaluate URL
		lUrlFormat = re.split(r'(?<!%)%(?!%)((?:[^;\[\{]+|\[.*?(?<!\\)\]|\{.*?(?<!\\)\})+);',sUrlFormat)
		dNumMap = {}
		lOrder = [None] * ((len(lUrlFormat)-1) / 2)
		reCounter = re.compile(
			r'(-??.?[0-9]+)?' + # FORMATTING: [RIGHT-PAD] [PADDING-CHAR] WIDTH
			r'([a-zA-Z])' + # Name
			r'(?:' + # HowTo
				r'(?:!([0-9]+|l))|' + # Order number or is a link
				r'(?:\*([0-9]+|f))|' + # 404 tolerance or quit when found
				r'(?:\[((?:[0-9]-[0-9]|[a-z]-[a-z]|[A-Z]-[A-Z]|\\-|\\|.)+)\])|' + # Digits
				r'(?:\{((?:[^,}]+|\\,|\\}|\\)+)?,((?:[^,}]+|\\,|\\}|\\)+)?\})|' + # Limits
				r'(\+|-)' + # Don't reset the counter (second one is with returning)
			r')*' # HowTos can be in any order, and are entirely optional
		)

		def _Digits(moX):
			iS,iF = tuple(map(ord,moX.group(0).split('-')))
			return ''.join(map(chr,range(min(iS,iF),max(iS,iF)+1,1)))
		#enddef

		for iI in range(1,len(lUrlFormat),2):
			moCounter = reCounter.match(lUrlFormat[iI])
			if moCounter is None:
				sys.stderr.write("Counter format invalid: %%%s;" % lUrlFormat[iI])
				return
			#endif
			sFmt,sName,sOrder,s404,sDigits,sMin,sMax,sReset = moCounter.groups()
			if sOrder != 'l':
				if sDigits is None: sDigits = '0123456789'
				if sDigits[0] == '*': sDigits = '\0' + sDigits[1:]
				elif sDigits[0:2] == '\\*': sDigits = sDigits[1:]
				sDigits = re.sub(r'[0-9]-[0-9]|[a-z]-[a-z]|[A-Z]-[A-Z]',_Digits,sDigits).replace("\\-","-").replace("\\\\","\\")
				if sOrder is None: sOrder = str((iI+1) / 2)
				if s404 is None: s404 = '0'
				if sMin is None: sMin = sDigits[min(1,len(sDigits))]
				if s404 == 'f':
					i404 = None
					bQuitOnFound = True
				else:
					i404 = int(s404)
					bQuitOnFound = False
				#endif

				dNumMap[sName] = [
					sMin,[0,''], # Current index
					[sMin,sMax,sDigits], # Starting, Maximum or None for infinite, Digit list
					#[bRPad,sPadChar,iWidth], # Formatting
					[bQuitOnFound,i404], # Existence handling
					["None","+","-"].index(str(sReset))
				]

				iOrder = int(sOrder)
				EnsureIndex(lOrder,iOrder)
				lOrder[iOrder] = sName
			#endif

			if sFmt is None: sFmt = ""
			lUrlFormat[iI] = sFmt + sName
		#endfor

		sUrlFormat = ""
		for iI in range(1,len(lUrlFormat),2):
			sUrlFormat += lUrlFormat[iI-1] + "%" + lUrlFormat[iI]
		#endfor
		sUrlFormat += lUrlFormat[-1]

		# Collapse lOrder
		for iI in range(lOrder.count(None)): lOrder.remove(None)

		# Parse and apply continuance
		def _Continue(moX):
			sName,sCont = moX.groups()
			dNumMap[sName][0] = sCont
		#enddef
		re.sub(r'(?:^|,)([a-zA-Z]):([^,]+)',_Continue,sContinue)

		# Begin dumpage!
		if iDebugLevel >= 2:
			print('(Debug) sUrlFormat = "%s"' % sUrlFormat)
			print('(Debug) lOrder = "%s"' % lOrder)
			print('(Debug) dNumMap = "%s"' % dNumMap)
		#endif
		sLastInc = lOrder[0]
		while True:
			# Construct URL and download
			sUrl = Format(sUrlFormat,dNumMap)
			iRet = 0
			if iDebugLevel >= 3:
				if iDebugLevel >= 4: iRet = rand(0,1)
				print('(Debug) sUrl = "%s"%s' % (sUrl,{True:" (404)",False:""}[bool(iRet)]))
			else: iRet = DownloadFile(sUrl,dNumMap)

			# Increase 404s (errors, technically) if necessary
			if iRet != 0:
				dNumMap[sLastInc][1][0] += 1
				if dNumMap[sLastInc][1][1] == '':
					dNumMap[sLastInc][1][1] = dNumMap[sLastInc][0]
				#endif
			else:
				# Reset 404s
				dNumMap[sLastInc][1][0] = 0
				dNumMap[sLastInc][1][1] = ''
			#endif

			bDid404Out = False
			# Check 404s on sLastInc
			if  (dNumMap[sLastInc][3][0] and dNumMap[sLastInc][1][0] == 0) or \
			(not dNumMap[sLastInc][3][0] and dNumMap[sLastInc][3][1] != 0 and \
			dNumMap[sLastInc][1][0] >= dNumMap[sLastInc][3][1]):
				if iDebugLevel >= 2: print('(Debug) Counter %s met its 404 critria' % sLastInc)
				iIdx = lOrder.index(sLastInc)
				# Last counter 404'd out
				if iIdx == len(lOrder)-1: break
				# Restart counter (if allowed)
				if dNumMap[sLastInc][4] == 0: dNumMap[sLastInc][0] = dNumMap[sLastInc][2][0]
				elif dNumMap[sLastInc][4] == 2: dNumMap[sLastInc][0] = dNumMap[sLastInc][1][1]
				# Reset 404s
				dNumMap[sLastInc][1][0] = 0
				dNumMap[sLastInc][1][1] = ''
				# Prepare to inc the next counter
				sLastInc = lOrder[iIdx+1]
				bDid404Out = True
			#endif
			# Check if maximum has been reached
			bBroken = False
			for iI in range(lOrder.index(sLastInc) if bDid404Out else 0,len(lOrder)):
				sI = lOrder[iI]
				sLastInc = sI
				if dNumMap[sI][0] == dNumMap[sI][2][1]: # If cur == max:
					if iDebugLevel >= 2: print('(Debug) Counter %s maxed out' % sI)
					# Restart counter
					dNumMap[sI][0] = dNumMap[sI][2][0]
				else:
					bBroken = True
					break
				#endif
			#endfor
			if not bBroken: break # Max for last counter was reached

			# Inc sLastInc
			dNumMap[sLastInc][0] = IncVia(dNumMap[sLastInc][0],dNumMap[sLastInc][2][2])
		#endwhile
	#endif
#enddef

main()
