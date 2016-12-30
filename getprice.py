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
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
codes = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]
years = [17, 18, 19, 20, 21, 22]
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
        url = "https://core-api.barchart.com/v1/historical/get?" + "symbol={}&fields=tradeTime.format(m%2Fd%2Fy)%2CopenPrice%2ChighPrice%2ClowPrice%2ClastPrice%".format(quoteCode)+"2Cvolume%2CopenInterest%2CsymbolCode%2CsymbolType&"+"startDate={}&endDate={}&".format("2016-12-01", ahead)+"type=eod&orderDir=desc&limit=100&meta=field.shortName%2Cfield.type%2Cfield.description&page=1&raw=1"
        print url
        priceData = json.loads(get_html(url))['data']
        for price in priceData:
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
def getBrtDayPrice(ahead):
    for year in years:
         for i in range(1, 13):
             quoteCode = "QA" + codes[i - 1] + "{}".format(year)
             productCode = months[i - 1] + "{}".format(year)
             priceData = json.loads(get_html("https://core-api.barchart.com/v1/historical/get?" + 
                                        "symbol={}&fields=tradeTime.format(m%2Fd%2Fy)%2CopenPrice%2ChighPrice%2ClowPrice%2ClastPrice%".format(quoteCode)
                                        +"2Cvolume%2CopenInterest%2CsymbolCode%2CsymbolType&"
                                        +"startDate={}&endDate={}&".format("2016-12-01", ahead)
                                        +"type=eod&orderDir=desc&limit=100&meta=field.shortName%2Cfield.type%2Cfield.description&page=1&raw=1"))['data']
             if(len(priceData) == 1):
                 continue
             for price in priceData:
                tradeTime = price['tradeTime']
                lastPrice = price['lastPrice']
                tradeTime = datetime.strptime(tradeTime, "%m/%d/%y")
                tradeTime = datetime.strftime(tradeTime, "%Y-%m-%d")
                try:
                    with sqlCli.cursor() as cursor:
                        sql = "insert into `dayprice` (type, productCode, day, price) values ('{}', '{}', '{}', {}) on duplicate key update price={}".format(
                            "BRT", productCode, tradeTime, lastPrice, lastPrice)
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
        productCode = date[0] + date[1:3].lower() + date[6:8]
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
    pv = 0
    deltaDays = (endDay - startDay).days
    try:
        with sqlCli.cursor() as cursor:
            sql = "select * from `future`"
            cursor.execute(sql)
            res = cursor.fetchall()
            for r in res:
                lastpv = 0
                for d in range(deltaDays):
                    nowDay = datetime.strftime(startDay + timedelta(d), "%Y-%m-%d")
                    sql = "select * from `dayprice` where type = '{}' and productCode = '{}' and datediff(day, '{}') <= 0 order by day".format(r['productType'], r['productCode'], nowDay)
                    cursor.execute(sql)
                    result = cursor.fetchall()
                    pv = (result[len(result)-1]['price'] - r['price']) * r['quantity']
                    sql = "insert into `hispv`(`tradeId`, `day`, `pv`, `userId`, `productCode`, `productType`) values ('{}', '{}', {}, '{}', '{}', '{}') on duplicate key update pv = {}".format(
                      r['tradeId'], nowDay, pv, r['userId'], r['productCode'], r['productType'], pv)
                    cursor.execute(sql)
                    pl = pv - lastpv
                    lastpv = pv
                    if(deltaDays != 0):
                        sql = "insert into `pl`(`tradeId`, `day`, `pl`, `userId`, `productCode`, `productType`) values ('{}', '{}', {}, '{}', '{}', '{}') on duplicate key update pl = {}".format(
                          r['tradeId'], nowDay, pl, r['userId'], r['productCode'], r['productType'], pl)
                        cursor.execute(sql)
            sql = "select * from `swap`"
            cursor.execute(sql)
            res = cursor.fetchall()
            for r in res:
                lastpv = 0
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
                    if(r['buyOrSell'] == 0):
                        pv = -pv
                    pl = pv - lastpv
                    lastpv = pv
                    if(deltaDays != 0):
                        sql = "insert into `pl`(`tradeId`, `day`, `pl`, `userId`, `productCode`, `productType`) values ('{}', '{}', {}, '{}', '{}', '{}') on duplicate key update pl = {}".format(
                          r['tradeId'], nowDay, pl, r['userId'], r['productCode'], r['productType'], pl)
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
                if(tp == None):
                    continue
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
                    if(result == None):
                        continue
                    pv = (result['price'] - r['price']) * r['quantity']
                else:
                    quanPerDay = r['quantity'] / r['wdays']
                    for res in result:
                        pv += res['price'] * quanPerDay
                    sql = "select * from `contractprice` where type = '{}' and productCode = '{}'".format(r['productType'], r['productCode'])
                    cursor.execute(sql)
                    result = cursor.fetchone()
                    if(result == None):
                        continue
                    pv = pv + (r['wdays'] - rows) * quanPerDay * result['price'] - r['price'] * quanPerDay * r['wdays']
                if(r['buyOrSell'] == 0):
                    pv = -pv
                sql = "update `risk` set pv = {} where tradeId = '{}' and productCode = '{}' and productType = '{}'".format(pv, r['tradeId'], r['productCode'], r['productType'])
                cursor.execute(sql)
                sql = "insert into `hispv`(`tradeId`, `day`, `pv`, `userId`, `productCode`, `productType`) values ('{}', '{}', {}, '{}', '{}', '{}') on duplicate key update pv = {}".format(
                      r['tradeId'], datetime.strftime(datetime.now(), "%Y-%m-%d"), pv, r['userId'], r['productCode'], r['productType'], pv)
                cursor.execute(sql)
            sqlCli.commit()
    finally:
        pass

if __name__=="__main__":
    getWtiNewestPrice()
    getBrtNewestPrice()
    getBrtDayPrice(datetime.strftime(datetime.now(), "%Y-%m-%d"))
    getWtiDayPrice(datetime.strftime(datetime.now(), "%Y-%m-%d"))
    simulatePV()
    updatePV()
