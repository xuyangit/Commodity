#coding:utf-8
import urllib2
from bs4 import BeautifulSoup
import sys
import json
import datetime

import MySQLdb
conn = MySQLdb.connect(host='localhost', user='root',passwd='xuyang2008',db='commodity')

def get_html(_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'}
    req = urllib2.Request(url=_url, headers=headers)
    html = urllib2.urlopen(req).read()
    return html


if __name__=="__main__":

    brent_expiry = get_html("https://www.theice.com/products/219/Brent-Crude-Futures/expiry")
    soup = BeautifulSoup(brent_expiry, "html.parser", from_encoding="gb18030")
    be = open("brent_expiry.txt","w")
    ans = 0
    for tag in soup.find_all('th'):
        ans= ans+1
        be.write(unicode(tag.string).ljust(20))
    be.write("\n")
    temp = 0
    cursor = conn.cursor()
    settlementdate = ""
    contractmonth = ""
    productcode = ""
    type = "BRT"
    for tag in soup.find_all('td'):
        be.write(unicode(tag.string).ljust(20))
        temp = temp+1
        if temp==1:    #contract symbol
            contractmonth = tag.string
            productcode = tag.string
            contractmonth = "20"+contractmonth[3:5] + contractmonth[0:3]
            contractmonth = datetime.datetime.strptime(contractmonth, '%Y%b')
            contractmonth = contractmonth.strftime('%Y-%m-%d %H:%M:%S')
        if temp==3:   #settlementdate
            settlementdate = tag.string # settlementdate
            settlementdate = datetime.datetime.strptime(settlementdate, '%m/%d/%Y')
            settlementdate = settlementdate.strftime('%Y-%m-%d %H:%M:%S')
        if temp==ans:
            temp=0
            cursor = conn.cursor()
            cursor.execute("insert into info(productCode,contractMonth,settleDate,type) values ('%s', '%s', '%s', '%s')" % (productcode, contractmonth, settlementdate,type))
            conn.commit()
            cursor.close()
            be.write("\n")
    be.close()
    cursor.close()

    print "there"

    crude_expiry = get_html("http://www.cmegroup.com/trading/energy/crude-oil/light-sweet-crude_product_calendar_futures.html")
    soup = BeautifulSoup(crude_expiry, "html.parser", from_encoding="gb18030")
    print "here"
    contractmonth = ""
    productcode = ""
    settlementdate = ""
    type = "WTI"
    for tags in soup.find_all('tr')[2:]:
        tp = tags.find("th").contents
        contractmonth = tp[0]       #contract month
        contractmonth = datetime.datetime.strptime(contractmonth,'%b %Y')
        contractmonth = contractmonth.strftime('%Y-%m-%d %H:%M:%S')
        temp = ""
        productcode = tp[0][0:3] + tp[0][6:8]
        settlementdate = tp[6].string    #settlementdate
        settlementdate = datetime.datetime.strptime(settlementdate,'%d %b %Y')
        settlementdate = settlementdate.strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.cursor()
        cursor.execute("insert into info(productCode,contractMonth,settleDate,type) values ('%s', '%s', '%s', '%s')" % (productcode,contractmonth,settlementdate,type))
        conn.commit()
        cursor.close()
