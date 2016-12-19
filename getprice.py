import urllib2
import json
import pymysql.cursors
from datetime import datetime
from bs4 import BeautifulSoup

sqlCli = pymysql.connect(host='localhost',
                         user='root',
                         password='xuyang2008',
                         db='commodity',
                         charset='utf8mb4',
                         cursorclass=pymysql.cursors.DictCursor)

def get_html(_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'}
    req = urllib2.Request(url=_url, headers=headers)
    html = urllib2.urlopen(req).read()
    return html

def getWtiDayPrice(ahead):
    
def getBrtDayPrice(ahead):
    marketData = json.loads(get_html("https://www.theice.com/marketdata/DelayedMarkets.shtml?getContractsAsJson=&productId=254&hubId=403"))
    for data in marketData:
        marketId = data['marketId']
        prices = json.loads(get_html("https://www.theice.com/marketdata/DelayedMarkets.shtml?getHistoricalChartDataAsJson=&marketId={}&historicalSpan=1".format(marketId)))
        productCode = data['marketStrip']
        bars = prices['bars'][len(prices['bars']) - ahead:]
        for bar in bars:
            day = datetime.strptime(bar[0], "%a %b %d %H:%M:%S %Y")
            day = datetime.strftime(day, "%Y-%m-%d")
            price = bar[1]
            try:
                with sqlCli.cursor() as cursor:
                    sql = "insert into `dayprice` (type, productCode, day, price) values ('{}', '{}', '{}', {}) on duplicate key update price={}".format("BRT", productCode, day, price, price)
                    cursor.execute(sql)
                    sqlCli.commit()
            finally:
                print ""

def getBrtNewestPrice():
    prices = json.loads(get_html("https://www.theice.com/marketdata/DelayedMarkets.shtml?getContractsAsJson=&productId=254&hubId=403"))
    for quote in prices:
        productCode = quote['marketStrip']
        productType = "BRT"
        price = quote['lastPrice']
        try:
            with sqlCli.cursor() as cursor:
                sql = "insert into `contractprice` (type, productCode, price) values ('{}', '{}', {}) on duplicate key update price={}".format(productType, productCode, price, price)
                cursor.execute(sql)
                sqlCli.commit()
        finally:
            print ""
def getWtiNewestPrice():
    prices = json.loads(get_html("http://www.cmegroup.com/CmeWS/mvc/Quotes/Future/425/G?pageSize=50&_=1481173476449"))['quotes']
    for quote in prices:
        date = quote['expirationMonth']
        productCode = date[0:3] + date[6:8]
        productType = "WTI"
        price = quote['priorSettle']
        try:
            with sqlCli.cursor() as cursor:
                sql = "insert into `contractprice` (type, productCode, price) values ('{}', '{}', {}) on duplicate key update price={}".format(productType, productCode, price, price)
                cursor.execute(sql)
                sqlCli.commit()
        finally:
            print ""
if __name__=="__main__":
   #getWtiNewestPrice()
   #getBrtNewestPrice()
    getBrtDayPrice(5)
