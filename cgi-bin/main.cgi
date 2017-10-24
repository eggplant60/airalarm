#!/usr/bin/python
# -*- coding: utf-8 -*-

import cgitb
import sys
sys.path.append('/home/naoya/airalarm')
import airalarmconf


###
def retConfStr(conf):
    b2s = lambda tf: ("selected" if tf else "")
    return [b2s(conf.alarmOn), b2s(not(conf.alarmOn)),\
            conf.alarmTime.strftime('%H:%M'),\
            b2s(conf.ctrlOn), b2s(not(conf.ctrlOn)),\
            str(conf.ctrlTemp),\
            b2s(conf.dispOn), b2s(not(conf.dispOn)),\
            b2s(conf.dispMode=="ALARM"), b2s(conf.dispMode=="CTRL")]



### MAIN ###
cgitb.enable() # dislpy error on browser

print "Content-type:text/html; charset=UTF-8"
print

print "<!-" # comment out standard stream of retConfStr()
http_data = retConfStr(airalarmconf.AirAlarmConf())
print "-->"

### HTML ###
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
    <!-- Title -->
    <h2><img src="/image/icon_115860_256.jpg" alt="" width=18 height=19> AirAlarm 設定</h2>
    
    <form name="form1" method="POST" action="/cgi-bin/submit.cgi">


      <div>
	<p>アラーム機能:
	  <select name="alarm_sw">
	    <option value="ON" {0[0]}>ON</option>
	    <option value="OFF" {0[1]}>OFF</option>
	  </select>
	</p>
	<p>
	  設定時刻: <input name="alarm_time" type="time" style="width:80px" value={0[2]}>
	</p>
      </div>
      <Hr Width="100%">
      <!-- ------------------------------------------ -->

      <div>
	<p>温度調整機能: 
	  <select name="ctrl_sw">
	    <option value="ON" {0[3]}>ON</option>
	    <option value="OFF" {0[4]}>OFF</option>
	  </select>
	</p>
	<p>
	  設定温度: <input name="ctrl_temp" type="number" style="width:40px" value={0[5]}>
        </p>
      </div>
      <Hr Width="100%">
      <!-- ------------------------------------------ -->
      
      <div>
	<p>バックライト: 
	  <select name="disp_sw">
	    <option value="ON" {0[6]}>ON</option>
	    <option value="OFF" {0[7]}>OFF</option>
	  </select>
	</p>
	<p>表示方式: 
          <select name="disp_mode">
	    <option value="ALARM" {0[8]}>アラーム</option>
	    <option value="CTRL" {0[9]}>温湿度計</option>
	  </select>
        </p>
      </div>
      <Hr Width="100%">
      <!-- ------------------------------------------ -->

      <div>
        <input type="submit" value="セット">
      </div>
      <Hr Width="100%">
      <!-- ------------------------------------------ -->

    </form>
    
  </body>
</html>""".format(http_data)
