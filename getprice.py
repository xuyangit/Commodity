import urllib2
import json
import pymysql.cursors
from datetime import datetime, timedelta
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
#here ahead is end date
def getWtiDayPrice(ahead):
    marketData = json.loads(get_html("http://www.cmegroup.com/CmeWS/mvc/Quotes/Future/425/G?pageSize=50&_=1481173476449"))['quotes']
    for data in marketData:
        quoteCode = data['quoteCode']
        productCode = data['expirationMonth']
        productCode = productCode[0] + productCode[1:3].lower()+ productCode[6:8]
        if(productCode[3] == '2'):
            quoteCode = quoteCode[0:3] + '2' + quoteCode[3]
        priceData = json.loads(get_html("https://core-api.barchart.com/v1/historical/get?" + 
                                        "symbol={}&fields=tradeTime.format(m%2Fd%2Fy)%2CopenPrice%2ChighPrice%2ClowPrice%2ClastPrice%".format(quoteCode)
                                        +"2Cvolume%2CopenInterest%2CsymbolCode%2CsymbolType&"
                                        +"startDate={}&endDate={}&".format("2016-12-01", ahead)
                                        +"type=eod&orderDir=desc&limit=100&meta=field.shortName%2Cfield.type%2Cfield.description&page=1&raw=1"))['data']
        for price in priceData:
            print price
            tradeTime = price['tradeTime']
            lastPrice = price['lastPrice']
            tradeTime = datetime.strptime(tradeTime, "%m/%d/%y")
            tradeTime = datetime.strftime(tradeTime, "%Y-%m-%d")
            try:
                with sqlCli.cursor() as cursor:
                    sql = "insert into `dayprice` (type, productCode, day, price) values ('{}', '{}', '{}', {}) on duplicate key update price={}".format(
                        "WTI", productCode, tradeTime, lastPrice, lastPrice)
                    cursor.execute(sql)
                    sqlCli.commit()
            finally:
                pass
#here ahead is start date          
def getBrtDayPrice(ahead):
    marketData = json.loads(get_html("https://www.theice.com/marketdata/DelayedMarkets.shtml?getContractsAsJson=&productId=254&hubId=403"))
    startDay = datetime.strptime(ahead, "%Y-%m-%d")
    for data in marketData:
        marketId = data['marketId']
        prices = json.loads(get_html("https://www.theice.com/marketdata/DelayedMarkets.shtml?getHistoricalChartDataAsJson=&marketId={}&historicalSpan=1".format(marketId)))
        productCode = data['marketStrip']
        bars = prices['bars']
        for bar in bars:
            day = datetime.strptime(bar[0], "%a %b %d %H:%M:%S %Y")
            if((day - startDay).days >= 0):
                day = datetime.strftime(day, "%Y-%m-%d")
                price = bar[1]
                try:
                    with sqlCli.cursor() as cursor:
                        sql = "insert into `dayprice` (type, productCode, day, price) values ('{}', '{}', '{}', {}) on duplicate key update price={}".format("BRT", productCode, day, price, price)
                        cursor.execute(sql)
                        sqlCli.commit()
                finally:
                    pass

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
            pass
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
            pass
def simulatePV():
    startDay = datetime.strptime("2016-12-01", "%Y-%m-%d")
    endDay = datetime.now()
    deltaDays = (endDay - startDay).days
    try:
        with sqlCli.cursor() as cursor:
            sql = "select * from `future`"
            cursor.execute(sql)
            res = cursor.fetchall()
            for r in res:
                for d in range(deltaDays):
                    nowDay = datetime.strftime(startDay + timedelta(d), "%Y-%m-%d")
                    sql = "select * from `dayprice` where type = '{}' and productCode = '{}' and datediff(day, '{}') <= 0 order by day".format(r['productType'], r['productCode'], nowDay)
                    cursor.execute(sql)
                    result = cursor.fetchall()
                    pv = (result[len(result)-1]['price'] - r['price']) * r['quantity']
                    sql = "insert into `hispv`(`tradeId`, `day`, `pv`, `userId`, `productCode`, `productType`) values ('{}', '{}', {}, '{}', '{}', '{}') on duplicate key update pv = {}".format(
                      r['tradeId'], nowDay, pv, r['userId'], r['productCode'], r['productType'], pv)
                    cursor.execute(sql)
            sql = "select * from `swap`"
            cursor.execute(sql)
            res = cursor.fetchall()
            for r in res:
                for d in range(deltaDays):
                    delta = datetime.strptime(str(r['startDate']), "%Y-%m-%d") - (startDay + timedelta(d))
                    if(delta.days <= 0):
                        nowDay = datetime.strftime(startDay + timedelta(d), "%Y-%m-%d")
                        sql = "select * from `dayprice` where datediff(day, '{}') <= 0 and type = '{}' and productCode = '{}' order by day".format(nowDay, r['productType'], r['productCode'])
                        rows = cursor.execute(sql)
                        result = cursor.fetchall()
                        pv = 0
                        quanPerDay = r['quantity'] / r['wdays']
                        for res in result:
                            pv += res['price'] * quanPerDay
                        pv = pv + (r['wdays'] - rows) * quanPerDay * result[len(result) - 1]['price'] - r['price'] * quanPerDay * r['wdays']
                        sql = "insert into `hispv`(`tradeId`, `day`, `pv`, `userId`, `productCode`, `productType`) values ('{}', '{}', {}, '{}', '{}', '{}') on duplicate key update pv = {}".format(
                        r['tradeId'], nowDay, pv, r['userId'], r['productCode'], r['productType'], pv)
                        cursor.execute(sql)
                    else:
                        nowDay = datetime.strftime(startDay + timedelta(d), "%Y-%m-%d")
                        sql = "select * from `dayprice` where datediff(day, '{}') <= 0 and type = '{}' and productCode = '{}' order by day".format(nowDay, r['productType'], r['productCode'])
                        cursor.execute(sql)
                        result = cursor.fetchall()
                        pv = (result[len(result) - 1]['price'] - r['price']) * r['quantity'] 
                        sql = "insert into `hispv`(`tradeId`, `day`, `pv`, `userId`, `productCode`, `productType`) values ('{}', '{}', {}, '{}', '{}', '{}') on duplicate key update pv = {}".format(
                        r['tradeId'], nowDay, pv, r['userId'], r['productCode'], r['productType'], pv)
                        cursor.execute(sql)
            sqlCli.commit()
    finally:
        pass
def updatePV():
    try:
        with sqlCli.cursor() as cursor:
            sql = "select * from `future`"
            cursor.execute(sql)
            res = cursor.fetchall()
            for r in res:
                sql = "select * from `contractprice` where type = '{}' and productCode = '{}'".format(r['productType'], r['productCode'])
                cursor.execute(sql)
                tp = cursor.fetchone()
                pv = (tp['price'] - r['price']) * r['quantity']
                sql = "update `risk` set pv = {} where tradeId = '{}'".format(pv, r['tradeId'])
                cursor.execute(sql)
                sql = "insert into `hispv`(`tradeId`, `day`, `pv`, `userId`, `productCode`, `productType`) values ('{}', '{}', {}, '{}', '{}', '{}') on duplicate key update pv = {}".format(
                      r['tradeId'], datetime.strftime(datetime.now(), "%Y-%m-%d"), pv, r['userId'], r['productCode'], r['productType'], pv)
                cursor.execute(sql)
            sql = "select * from `swap`"
            cursor.execute(sql)
            res = cursor.fetchall()
            for r in res:
                sql = "select * from `dayprice` where datediff(day, '{}') >= 0 and type = '{}' and productCode = '{}'".format(r['startDate'], r['productType'], r['productCode'])
                rows = cursor.execute(sql)
                result = cursor.fetchall()
                pv = 0
                if(rows == 0):
                    sql = "select * from `contractprice` where type = '{}' and productCode = '{}'".format(r['productType'], r['productCode'])
                    cursor.execute(sql)
                    result = cursor.fetchone()
                    pv = (result['price'] - r['price']) * r['quantity']
                else:
                    quanPerDay = r['quantity'] / r['wdays']
                    for res in result:
                        pv += res['price'] * quanPerDay
                    sql = "select * from `contractprice` where type = '{}' and productCode = '{}'".format(r['productType'], r['productCode'])
                    cursor.execute(sql)
                    result = cursor.fetchone()
                    pv = pv + (r['wdays'] - rows) * quanPerDay * result['price'] - r['price'] * quanPerDay * r['wdays']
                sql = "update `risk` set pv = {} where tradeId = '{}' and productCode = '{}' and productType = '{}'".format(pv, r['tradeId'], r['productCode'], r['productType'])
                cursor.execute(sql)
                sql = "insert into `hispv`(`tradeId`, `day`, `pv`, `userId`, `productCode`, `productType`) values ('{}', '{}', {}, '{}', '{}', '{}') on duplicate key update pv = {}".format(
                      r['tradeId'], datetime.strftime(datetime.now(), "%Y-%m-%d"), pv, r['userId'], r['productCode'], r['productType'], pv)
                cursor.execute(sql)
            sqlCli.commit()
    finally:
        pass

if __name__=="__main__":
##    getWtiNewestPrice()
##    getBrtNewestPrice()
##    getBrtDayPrice("2016-12-01")
##    getWtiDayPrice(datetime.strftime(datetime.now(), "%Y-%m-%d"))
    simulatePV()
    updatePV()
