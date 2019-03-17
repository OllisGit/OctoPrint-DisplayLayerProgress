# coding=utf-8
from __future__ import absolute_import

import re

# see https://www.safaribooksonline.com/library/view/python-cookbook-2nd/0596007973/ch01s19.html
def multiple_replace(text, adict):
    rx = re.compile('|'.join(map(re.escape, adict)))
    def one_xlat(match):
        return adict[match.group(0)]
    return rx.sub(one_xlat, text)

# see https://stackoverflow.com/questions/4048651/python-function-to-convert-seconds-into-minutes-hours-and-days/4048773
def secondsToText(secs):
    days = secs // 86400
    hours = (secs - days * 86400) // 3600
    minutes = (secs - days * 86400 - hours * 3600) // 60
    seconds = secs - days * 86400 - hours * 3600 - minutes * 60

    result = ("{}d".format(days) if days else "") + \
             ("{}h".format(hours) if hours else "") + \
             ("{}m".format(minutes) if not days and minutes else "") + \
             ("{}s".format(seconds) if not days and not hours and seconds else "")
    return result

#day = 0
#hour = 0
#minute = 1
#second = 31

#seconds = day * 24 * 60 * 60 +  hour * 60 * 60 +  minute * 60  + second
#print(secondsToText(None, seconds) )


#myformat = "{:.2f}"
#myvalue = 3.141592
#myoutput = myformat.format(myvalue)
#print(myoutput)
