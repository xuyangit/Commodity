from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import Response
from flask import json
from flask import redirect, url_for
from flask import make_response
from datetime import date, datetime, timedelta
import time
import jwt
import calendar
import pymysql.cursors
from dateutil import rrule

app = Flask(__name__)
sqlCli = pymysql.connect(host='localhost',
                         user='root',
                         password='xuyang2008',
                         db='commodity',
                         charset='utf8mb4',
                         cursorclass=pymysql.cursors.DictCursor)

def workdays(start, end, holidays=0, days_off=None):
    if days_off is None:
        days_off = 5,6
    workdays = [x for x in range(7) if x not in days_off]
    days = rrule.rrule(rrule.DAILY, dtstart=start, until=end,byweekday=workdays)
    return days.count() - holidays

@app.route("/")
@app.route("/home")
def home():
    return render_template("Home.html")

@app.route("/swapTran", methods = ["POST"])
def swapTran():
    raw = []
    totaldays = 0
    userid = request.cookies.get('userid')
    if(userid != None and userid != ''):
        counterpart = request.form['counterpart']
        buyOrSell = request.form['buyOrSell']
        quantity = request.form['lotOfSwap']
        price = request.form['priceOfSwap']
        productType = request.form['productType']
        startDate = request.form['startDate']
        endDate = request.form['endDate']
        debug = None
        if(counterpart == None or counterpart == ""):
            return jsonify(err = "Please enter the counterpart", data = "")
        if(quantity == None or quantity == ""):
            return jsonify(err = "Please enter the lots", data = "")
        elif(price == None or price == ""):
            return jsonify(err = "Please enter the price", data = "")
        price = float(price)
        quantity = int(quantity)
        if(price <= 0):
            return jsonify(err = "The price should be a positive number", data = "")
        if(startDate == None or startDate == ""):
            return jsonify(err = "Please enter the startDate", data = "")
        elif(endDate == None or endDate == ""):
            return jsonify(err = "Please enter the endDate", data = "")
        if(buyOrSell == "Buy"):
            buyOrSell = 1
        else:
            buyOrSell = 0
        (startYear, startMonth, endYear, endMonth) = (int(startDate.split('-')[0]), int(startDate.split('-')[1]),
                                                      int(endDate.split('-')[0]), int(endDate.split('-')[1]))
        tradeId = jwt.encode({'userid' : userid, 'time' : str(datetime.now())}, 'secret', algorithm = 'HS256')
        try:
            with sqlCli.cursor() as cursor:
                sql = "select min(settleDate) as settleDate, productCode from `info` where datediff(settleDate, '{}') >= 0 and type = '{}'".format(
                       endDate + "-" + str(calendar.monthrange(endYear, endMonth)[1]) + " 00:00:00", productType)
                cursor.execute(sql)
                tpResult = cursor.fetchone()
                sql = "select settleDate, productCode from `info` where datediff(settleDate, '{}') >= 0 \
                       and datediff(settleDate, '{}') <= 0 and type = '{}' order by settleDate".format(
                    startDate + "-01 00:00:00", endDate + "-" + str(calendar.monthrange(endYear, endMonth)[1]) + " 00:00:00", productType)
                rows = cursor.execute(sql)
                result = cursor.fetchall()
                debug = result
                if(tpResult != None and not tpResult in result):
                    result.append(tpResult)
                    rows += 1
                lastday = date(startYear, startMonth, 1)
                settleDay = None
                for i in range(rows):
                    if(i == rows - 1):
                        settleDay = date(endYear, endMonth, calendar.monthrange(endYear, endMonth)[1])
                    else:
                        settleDay = date(result[i]['settleDate'].year, result[i]['settleDate'].month, result[i]['settleDate'].day)
                    wdays = workdays(lastday, settleDay, 0)
                    if(wdays == 0 and (settleDay - lastday).days < 0):
                        continue
                    totaldays = totaldays + wdays
                    raw.append({"wdays" : wdays, "productCode" : result[i]['productCode'], "startday" : lastday, "endday": settleDay})
                    lastday = settleDay + timedelta(1)
            quanPerDay = 1000 * quantity / totaldays
            with sqlCli.cursor() as cursor:
                for r in raw:
                    if(r['wdays'] != 0):
                        
                        sql = "insert into `swap` values ('{}', {}, {}, '{}', '{}', {}, '{}', '{}', '{}', '{}')".format(
                        counterpart, buyOrSell, price, productType + " " + r['productCode'], userid, quanPerDay * r['wdays'],
                        r['startday'].strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        r['endday'].strftime("%Y-%m-%d"), tradeId)
                        cursor.execute(sql)
                        sqlCli.commit()
                        sql = "select * from `dayprice` where datediff(day, '{}') >= 0 and type = '{}' and productCode = '{}'".format(r['startday'], productType, r['productCode'])
                        rows = cursor.execute(sql)
                        result = cursor.fetchall()
                        pv = 0
                        if(rows == 0):
                            sql = "select * from 'contractprice' where type = '{}' and productCode = '{}'".format(productType, r['productCode'])
                            cursor.execute(sql)
                            result = cursor.fetchall()
                            pv = (result['price'] - price) * quanPerDay * r['wdays']
                        else:
                            for res in result:
                                pv += res['price'] * quanPerDay
                            sql = "select * from 'contractprice' where type = '{}' and productCode = '{}'".format(productType, r['productCode'])
                            cursor.execute(sql)
                            result = cursor.fetchall()
                            pv = pv + (r['wdays'] - rows) * quanPerDay * result['price'] - price * quanPerDay * r['wdays']
                        sql = "insert into `risk`(`tradeId`, `quantity`, `type`, `productType`, `productCode`, `pv`, `userid`) values ('{}', {}, {}, '{}', '{}', {}, '{}')".format(
                        tradeId, quanPerDay * r['wdays'], 0, productType, r['productCode'], pv, userid)
                        cursor.execute(sql)
                        sqlCli.commit()
        except Exception, e:
            return jsonify(err = "Trade fails because of database error, please retry", data = "")
        finally:
            return jsonify(err = "", average = 1000.0 * quantity / totaldays, data = raw, deb = debug)
        
@app.route("/futureTran", methods = ["POST"])
def futureTran():
    userid = request.cookies.get('userid')
    if(userid != None and userid != ''):
        productType = request.form['futureType']
        quantity = request.form['lotOfFuture']
        price = request.form['priceOfFuture']
        futureCode = request.form['futureCode']
        if(quantity == None or quantity == ""):
            return jsonify(err = "Please enter the lots", risk = "")
        elif(price == None or price == ""):
            return jsonify(err = "Please enter the price", risk = "")
        price = float(price)
        quantity = int(quantity)
        if(price <= 0):
            return jsonify(err = "The price should be a positive number", risk = "")
        tradeId = jwt.encode({'userid' : userid, 'time' : str(datetime.now())}, 'secret', algorithm = 'HS256')
        try:
            with sqlCli.cursor() as cursor:
                sql = "insert into `future` values ({}, {}, '{}', '{}', '{}', '{}')".format(
                    quantity, price, productType + " " + futureCode, userid,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tradeId)
                cursor.execute(sql)
            sqlCli.commit()
        except:
            return jsonify(err = "Trade fails because of database error, please retry", risk = "")
        finally:
            return jsonify(err = "", risk = "{}".format(quantity))
        
@app.route("/getUserInfo")
def getUserInfo():
    userid = request.cookies.get('userid')
    result = None
    if(userid != None and userid != ''):
        try:
            with sqlCli.cursor() as cursor:
                sql = "select * from `user` where id = '{}'".format(userid)
                cursor.execute(sql)
                result = cursor.fetchone()
        finally:
            if(result != None):
                return jsonify(name = result['firstname'] + ' ' + result['lastname'],
                               email = result['eaddress'],
                               userName = result['id'])
    else:
        return redirect(url_for("login"))

@app.route("/login")
def login():
    return render_template("Login.html")

@app.route("/tradehistory", methods = ["POST"])
def tradeHistory():
    userid = request.cookies.get('userid')
    futureResult = []
    swapResult = []
    res = {"future" : futureResult, "swap" : swapResult}
    if(userid != None and userid != ''):
        try:
            with sqlCli.cursor() as cursor:
                sql = "select * from `future` where userId = '{}'".format(userid)
                rows = cursor.execute(sql)
                for i in range(rows):
                    futureResult.append(cursor.fetchone())
                sql = "select * from `swap` where userId = '{}'".format(userid)
                rows = cursor.execute(sql)
                for i in range(rows):
                    swapResult.append(cursor.fetchone())
        finally:
            jsonRes = json.dumps(res)
            return Response(jsonRes, mimetype='application/json')
        
@app.route("/getfutureinfo")
def getFutureInfo():
    currentTime = datetime.now()
    result = []
    try:
        with sqlCli.cursor() as cursor:
            sql = "select settleDate, productCode from `info`"
            rows = cursor.execute(sql)
            for i in range(rows):
                record = cursor.fetchone()
                settleDate = record['settleDate']
                delta = settleDate - currentTime
                if(delta.days > 0):
                    result.append(record['productCode'])
    finally:
        return jsonify(info = result)
                    
@app.route("/userpage")
def userPage():
    userid = request.cookies.get('userid')
    if(userid != None and userid != ''):
        return render_template("UserPage.html")
    else:
        return redirect(url_for('login'))
    
@app.route("/loginO", methods=["POST"])
def userLogin():
    userid = request.form['userid']
    password = request.form['password']
    result = None
    try:
        with sqlCli.cursor() as cursor: 
            sql = "select * from `user` where id = '{}' and password = '{}' and type = 0".format(userid, password)
            cursor.execute(sql)
            result = cursor.fetchone()
    finally:
        if(result == None):
            return jsonify(err = 'invalid', redirect = '')
        else:
            response = make_response(jsonify(err = '', redirect = 'userpage'))
            response.set_cookie('userid', userid)
            return response
    return jsonify(err = 'invalid', redirect = '')
@app.route("/loginA", methods=["POST"])
def adminLogin():
    userid = request.form['userid']
    password = request.form['password']
    result = None
    try:
        with sqlCli.cursor() as cursor:
            sql = "select * from `user` where id = '{}' and password = '{}' and type = 1".format(userid, password)
            cursor.execute(sql)
            result = cursor.fetchone()
    finally:
        if(result == None):
            return jsonify(err = 'invalid', redirect = '')
        else:
            return jsonify(err = '', redirect = 'userpage')
    return jsonify(err = 'invalid', redirect = '')
            
@app.route("/register/validation", methods=["POST"])
def registerValid():
    data = request.get_json()
    result = None
    field = data['field']
    if(field == "email"):
        try:
            with sqlCli.cursor() as cursor:
                sql = "select * from `user` where eaddress = '{}'".format(data['data'])
                cursor.execute(sql)
                result = cursor.fetchone()
        finally:
            if(result != None):
                 return 'EMAIL_ALREADY_EXIST'
            else:
                return ''
    elif(field == "userid"):
        try:
            with sqlCli.cursor() as cursor:
                sql = "select * from `user` where id = '{}'".format(data['data'])
                cursor.execute(sql)
                result = cursor.fetchone()
        finally:
            if(result != None):
                return "USERNAME_ALREADY_EXIST"
            else:
                return ''
    else:
        return ''
@app.route("/register", methods=['GET','POST'])
def register():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        userid = request.form['userid']
        eaddress = request.form['eaddress']
        password = request.form['password']
        try:
            with sqlCli.cursor() as cursor:
                sql = "insert into `user` (`id`, `firstname`, `lastname`, `eaddress`, `type`, `password`)\
                       values ('{}', '{}', '{}', '{}', {}, '{}')".format(userid, firstname, lastname, eaddress, 0, password)
                cursor.execute(sql)
            sqlCli.commit()
        finally:
            return jsonify(err = '', redirect = 'login')
    else:
        return render_template("Register.html")

@app.route("/riskEvaluation")
def riskEvaluation():
    return render_template("RiskEvaluation.html")



if __name__ == "__main__":
    app.run(debug=True)
