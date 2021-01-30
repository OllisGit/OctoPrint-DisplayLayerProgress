# coding=utf-8
# from __future__ import absolute_import
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re

#################### START: copied from octorprint 1.4.x for 1.3.x compatible reason

import sys
from past.builtins import basestring, unicode


def to_bytes(s_or_u, encoding="utf-8", errors="strict"):
	# type: (Union[unicode, bytes], str, str) -> bytes
	"""Make sure ``s_or_u`` is a bytestring."""
	if s_or_u is None:
		return s_or_u

	if not isinstance(s_or_u, basestring):
		s_or_u = str(s_or_u)

	if isinstance(s_or_u, unicode):
		return s_or_u.encode(encoding, errors=errors)
	else:
		return s_or_u

def to_unicode(s_or_u, encoding="utf-8", errors="strict"):
	# type: (Union[unicode, bytes], str, str) -> unicode
	"""Make sure ``s_or_u`` is a unicode string."""
	if s_or_u is None:
		return s_or_u

	if not isinstance(s_or_u, basestring):
		s_or_u = str(s_or_u)

	if isinstance(s_or_u, bytes):
		return s_or_u.decode(encoding, errors=errors)
	else:
		return s_or_u


def to_native_str(s_or_u):
	# type: (Union[unicode, bytes]) -> str
	"""Make sure ``s_or_u`` is a 'str'."""
	if sys.version_info[0] == 2:
		return to_bytes(s_or_u)
	else:
		return to_unicode(s_or_u)

#################### END


# see https://www.safaribooksonline.com/library/view/python-cookbook-2nd/0596007973/ch01s19.html
def multiple_replace(text, adict):
    rx = re.compile('|'.join(map(re.escape, adict)))
    def one_xlat(match):
        return adict[match.group(0)]
    return rx.sub(one_xlat, text)

# see https://stackoverflow.com/questions/4048651/python-function-to-convert-seconds-into-minutes-hours-and-days/4048773
def secondsToText(secs, hideSeconds=False):
    result = ""
    days = secs // 86400
    hours = (secs - days * 86400) // 3600
    minutes = (secs - days * 86400 - hours * 3600) // 60
    seconds = secs - days * 86400 - hours * 3600 - minutes * 60
    if (days > 0):
        if (hideSeconds == True):
            result = "{}d".format(days) + "{}h".format(hours) + "{}m".format(minutes)
        else:
            result = "{}d".format(days) + "{}h".format(hours) + "{}m".format(minutes) + "{}s".format(seconds)
    elif (hours > 0):
        if (hideSeconds == True):
            result = "{}h".format(hours) + "{}m".format(minutes)
        else:
            result = "{}h".format(hours) + "{}m".format(minutes) + "{}s".format(seconds)
    elif (minutes > 0):
        if (hideSeconds == True):
            result = "{}m".format(minutes)
        else:
            result = "{}m".format(minutes) + "{}s".format(seconds)
    elif (seconds >= 0):
        result = "{}s".format(seconds)

    # result = ("{}d".format(days) if days else "") + \
    #          ("{}h".format(hours) if hours else "") + \
    #          ("{}m".format(minutes) if not days and minutes else "") + \
    #          ("{}s".format(seconds) if not days and not hours and seconds else "0s")
    return result


from string import Formatter
from datetime import timedelta

# see https://stackoverflow.com/questions/538666/python-format-timedelta-to-string
def strfdelta(tdelta, fmt='{D:02}d {H:02}h {M:02}m {S:02}s', inputtype='timedelta'):
    if type(tdelta) is not timedelta:
        return ''
    """Convert a datetime.timedelta object or a regular number to a custom-
    formatted string, just like the stftime() method does for datetime.datetime
    objects.

    The fmt argument allows custom formatting to be specified.  Fields can
    include seconds, minutes, hours, days, and weeks.  Each field is optional.

    Some examples:
        '{D:02}d {H:02}h {M:02}m {S:02}s' --> '05d 08h 04m 02s' (default)
        '{W}w {D}d {H}:{M:02}:{S:02}'     --> '4w 5d 8:04:02'
        '{D:2}d {H:2}:{M:02}:{S:02}'      --> ' 5d  8:04:02'
        '{H}h {S}s'                       --> '72h 800s'

    The inputtype argument allows tdelta to be a regular number instead of the
    default, which is a datetime.timedelta object.  Valid inputtype strings:
        's', 'seconds',
        'm', 'minutes',
        'h', 'hours',
        'd', 'days',
        'w', 'weeks'
    """

    # Convert tdelta to integer seconds.
    if inputtype == 'timedelta':
        remainder = int(tdelta.total_seconds())
    elif inputtype in ['s', 'seconds']:
        remainder = int(tdelta)
    elif inputtype in ['m', 'minutes']:
        remainder = int(tdelta)*60
    elif inputtype in ['h', 'hours']:
        remainder = int(tdelta)*3600
    elif inputtype in ['d', 'days']:
        remainder = int(tdelta)*86400
    elif inputtype in ['w', 'weeks']:
        remainder = int(tdelta)*604800

    f = Formatter()
    desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
    possible_fields = ('W', 'D', 'H', 'M', 'S')
    constants = {'W': 604800, 'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    values = {}
    for field in possible_fields:
        if field in desired_fields and field in constants:
            values[field], remainder = divmod(remainder, constants[field])
    return f.format(fmt, **values)




import os
def getLastLinesFromFile(file_name, N):
    # Create an empty list to keep the track of last N lines
    list_of_lines = []
    # Open file for reading in binary mode
    with open(file_name, 'rb') as read_obj:
        # Move the cursor to the end of the file
        read_obj.seek(0, os.SEEK_END)
        # Create a buffer to keep the last read line
        buffer = bytearray()
        # Get the current position of pointer i.e eof
        pointer_location = read_obj.tell()
        # Loop till pointer reaches the top of the file
        while pointer_location >= 0:
            # Move the file pointer to the location pointed by pointer_location
            read_obj.seek(pointer_location)
            # Shift pointer location by -1
            pointer_location = pointer_location -1
            # read that byte / character
            new_byte = read_obj.read(1)
            # If the read byte is new line character then it means one line is read
            if new_byte == b'\n':
                # Save the line in list of lines
                list_of_lines.append(buffer.decode()[::-1])
                # If the size of list reaches N, then return the reversed list
                if len(list_of_lines) == N:
                    return list(reversed(list_of_lines))
                # Reinitialize the byte array to save next line
                buffer = bytearray()
            else:
                # If last read character is not eol then add it in buffer
                buffer.extend(new_byte)
        # As file is read completely, if there is still data in buffer, then its first line.
        if len(buffer) > 0:
            list_of_lines.append(buffer.decode()[::-1])
    # return the reversed list
    return list(reversed(list_of_lines))








### TEST-ZONE
#day = 0
#hour = 0
#minute = 1
#second = 31

#seconds = day * 24 * 60 * 60 +  hour * 60 * 60 +  minute * 60  + second
#print(secondsToText(None, seconds) )

# import octoprint.util
# # gcode_line_as_str = "M117 Priming Filamentâ{¦"
# gcode_line_as_bytes = b'M117 Priming Filament\xe2{\xa6\n'
# print (gcode_line_as_bytes)
#
# # gcode_encoded = gcode_line_as_bytes.decode('ISO-8859-1')
# # print (gcode_encoded)
#
# unicode_line = octoprint.util.to_unicode(gcode_line_as_bytes, errors="replace")
# # --> BOOOM: UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe2 in position 21: invalid continuation byte
# print(unicode_line)

# line = ";LAYER:1234"
# gcode_to_add = "M117 INDICATOR-Layer[layer_num]\n"
#
# layerNumber = line[7:]
# newGcode_to_add = gcode_to_add.replace("[layer_num]", layerNumber, 1)
#
# print( layerNumber)
# print( newGcode_to_add)
