#!/usr/bin/python
# -*- coding: utf-8 -*-

import cgi
import cgitb
import sys
sys.path.append('/home/naoya/airalarm')
import airalarmconf
import datetime

cgitb.enable() # dislpy error on browser


### Get Post Data
### Todo: data check
form = cgi.FieldStorage()


### HTML ###

print "Content-type:text/html; charset=UTF-8"
print

print """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>AirAlarm</title>
    <meta name="viewport" content="width:device-width,initial-scale=1.0">
    <link rel="shortcut icon" href="/image/icon_115860_256.jpg">    
  </head>
  
  <body>
    <h2><img src="/image/icon_115860_256.jpg" alt="" width=18 height=19> セット完了</h2>

    <div>
      <p>アラーム機能: {0}</p>
      <p>設定時刻:　　 {1}</p>
    </div>
    <Hr Width="100%">

    <div>
      <p>温度調整機能: {2}</p>
      <p>設定温度:　　 {3} 度</p>
    </div>
    <Hr Width="100%">

    <div>
      <p>バックライト: {4}</p>
      <p>表示モード:　 {5}</p>
    </div>
    <Hr Width="100%">
      
    <div>
      <form method="POST" action="/cgi-bin/main.cgi">
        <input type="submit" value="戻る">
      </form>
    </div>
    <Hr Width="100%">
    
  </body>
</html>""".format(form["alarm_sw"].value, form["alarm_time"].value,\
                   form["ctrl_sw"].value, form["ctrl_temp"].value,\
                   form["disp_sw"].value, form["disp_mode"].value)


### send Post Data to main.py via plain text
print "<!-" # comment out
obj = airalarmconf.AirAlarmConf()
obj.alarmOn = True if form["alarm_sw"].value=="ON" else False
obj.alarmTime = datetime.datetime.strptime(form["alarm_time"].value, '%H:%M')
obj.ctrlOn = True if form["ctrl_sw"].value=="ON" else False
obj.ctrlTemp = int(form["ctrl_temp"].value)
obj.dispOn = True if form["disp_sw"].value=="ON" else False
obj.dispMode = form["disp_mode"].value
obj.writeConf() # write configuration file and set flag
print "-->"
