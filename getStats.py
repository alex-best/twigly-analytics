import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey
    )
from sqlalchemy.orm.exc import NoResultFound
import datetime
from os import path
from json import dumps, loads
from mailchimp import Mailchimp
from re import sub
from urllib.parse import unquote

from fb import *

import tornado.ioloop
import tornado.web

import argparse

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

settings = {
    "cookie_secret": "twiglyr0x",
    "login_url": "/"
}
statsBase = declarative_base()
statsengine_url = 'mysql+pymysql://twigly:***REMOVED***@***REMOVED***/twigly_prod?charset=utf8'
#statsengine_url = 'mysql+pymysql://root@localhost:3306/twigly_dev?charset=utf8'
mailchimpkey = "***REMOVED***"

#relevantStates = [3,10,11,12,16]
deliveredStates = [3]
deliveredFreeStates = [10,11,12,16]
inProgress = [1,2,9,15]
returnedStates = [4]

class order(statsBase):
	__tablename__ = "orders"
	order_id = Column('order_id', Integer, primary_key=True)
	user_id = Column("user_id", Integer)
	delivery_zone_id = Column("delivery_zone_id", Integer)
	delivery_address = Column("delivery_address", String)
	coupon_id = Column("coupon_id", Integer)
	mobile_number = Column("mobile_number", String)
	cost = Column("cost", Float)
	service_tax = Column("service_tax", Float)
	vat = Column("vat", Float)
	sub_total = Column("sub_total", Float)
	delivery_charges = Column("delivery_charges", Float)
	total = Column("total", Float)
	wallet_transaction_id = Column("wallet_transaction_id", Integer)
	order_status = Column("order_status", Integer)
	payment_option = Column("payment_option", Integer)
	payment_status = Column("payment_status", Integer)
	date_add = Column("date_add", DateTime)
	date_upd = Column("date_upd", DateTime)
	source = Column("source", Integer)
	store_id = Column("store_id", Integer)

class orderdetail(statsBase):
	__tablename__ = "order_details"
	order_detail_id = Column("order_detail_id", Integer, primary_key=True)
	order_id = Column("order_id", Integer)
	menu_item_id = Column("menu_item_id", Integer)
	quantity = Column("quantity", Integer)
	price = Column("price", Float)
	discount = Column("discount", Float)
	discount_type = Column("discount_type", Integer)
	item_cost = Column("item_cost", Float)
	packaging_cost = Column("packaging_cost", Float)
	date_add = Column("date_add", DateTime)
	date_upd = Column("date_upd", DateTime)

class orderdetailoption(statsBase):
	__tablename__ = "order_detail_options"
	order_detail_id = Column("order_detail_option_id", Integer, primary_key=True)
	order_id = Column("order_detail_id", Integer, ForeignKey("order_details.order_detail_id"))
	menu_item_id = Column("ingredient_option_id", Integer)
	price = Column("price", Float)


class tag(statsBase):
	__tablename__ = "tags"
	tag_id = Column("tag_id", Integer, primary_key=True)
	name = Column("name", String)
	priority = Column("priority", Integer)
	is_visible = Column("is_visible", Integer)
	mandatory_for_order = Column("mandatory_for_order", Integer)

class menu_item_tag(statsBase):
	__tablename__ = "menu_item_tags"
	menu_item_id = Column("menu_item_id", Integer)
	tag_id = Column("tag_id", Integer)
	__mapper_args__ = {
		'primary_key':[menu_item_id, tag_id]
    }

class feedback(statsBase):
	__tablename__ = "feedbacks"
	feedback_id = Column("feedback_id", Integer, primary_key=True)
	food_rating = Column("food_rating", Integer)
	delivery_rating = Column("delivery_rating", Integer)
	order_id = Column("order_id", Integer)
	comment = Column("comment", String)

class menuitem(statsBase):
	__tablename__ = "menu_items"
	menu_item_id = Column("menu_item_id", Integer, primary_key=True)
	name = Column("name", String)
	img_url = Column("img_url", String)
	description = Column("description", String)
	calories = Column("calories", Integer)
	is_active = Column("is_active", Integer)
	category = Column("category", Integer)
	is_combo = Column("is_combo", Integer)
	cooking_station = Column("cooking_station", Integer)
	

	def getJson(self):
		return {
			"menu_item_id": self.menu_item_id,
			"name": self.name
		}

class user(statsBase):
	__tablename__ = "users"
	user_id = Column("user_id", Integer, primary_key=True)
	name = Column("name", String)

def getRedirect(username):
	if (username in ["chef", "chef03", "headchef"]):
		return "storeitems"
	else:
		return "stats"

def authenticate(thisusername, thispassword):
	if (thisusername == "admin" and thispassword == "tw1gl7h1") or (thisusername == "review" and thispassword == "rvwdash") or (thisusername == "chef" and thispassword == "twigly123") or (thisusername == "chef03" and thispassword == "twiglychef03") or (thisusername == "headchef" and thispassword == "rahulonly"):
		return {"result": True}
	else:
		return {"result": False}

class BaseHandler(tornado.web.RequestHandler):
	def get_current_user(self):
		return self.get_secure_cookie("user")

class LoginHandler(BaseHandler):
	def get(self):
		self.render("templates/logintemplate.html")

	def post(self):
		thisuser = self.get_argument('username')
		thispassword = self.get_argument('password')
		authresult = authenticate(thisuser, thispassword)
		if (authresult["result"]):
			self.set_secure_cookie("user", thisuser)

		authresult["redirect"] = getRedirect(thisuser)
		self.write(authresult)

def getTotalCount(parsedstartdate, parsedenddate, daterange, statssession, store_list):
	dailyorderscountquery = statssession.query(order.date_add, sqlalchemy.func.count(order.order_id)).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress)).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add), order.store_id.in_(store_list))

	thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): int(thisresult[1]) for thisresult in dailyorderscountquery}
	totalcount = []
	for thisdate in daterange:
		if thisdate in thiscountdetails:
			totalcount.append(thiscountdetails[thisdate])
		else:
			totalcount.append(0)

	return totalcount

def getOrderCounts(parsedstartdate, parsedenddate, dailyordersquery, daterange, statssession):
	firstorderquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress)).order_by(order.date_add).group_by(order.mobile_number)

	firstordersmap = {}
	for thisorder in firstorderquery:
		firstordersmap[thisorder.mobile_number] = thisorder.date_add.strftime("%c")

	ordercounts = {thisdate: {"new": 0, "old": 0} for thisdate in daterange}
	ordertotals = {thisdate: {"new": 0.0, "old": 0.0} for thisdate in daterange}

	platformcounts = {thisdate: {"Android": 0, "Web": 0, "iOS": 0, "Zomato": 0, "Swiggy": 0, "Call":0} for thisdate in daterange}

	freeordercounts = {thisdate: {"FoodTrial": 0, "FreeDelivery": 0, "Returned": 0} for thisdate in daterange}
	freeordersums = {thisdate: {"FoodTrial": 0.0, "FreeDelivery": 0.0, "Returned": 0.0} for thisdate in daterange}

	active_stores = statssession.query(store).filter(store.is_active == True).all()
	active_stores_list = [x.store_id for x in active_stores]

	newusercountsbystore = {x.store_id: {thisdate:0 for thisdate in daterange} for x in active_stores}
	newusertotalsbystore = {x.store_id: {thisdate:0.0 for thisdate in daterange} for x in active_stores}

	for thisorder in dailyordersquery:
		if thisorder.order_status not in returnedStates:
			if thisorder.mobile_number in firstordersmap:
				if (thisorder.date_add.strftime("%c") == firstordersmap[thisorder.mobile_number]):
					ordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["new"] += 1
					ordertotals[thisorder.date_add.strftime("%a %b %d, %Y")]["new"] += float(thisorder.total)
					newusercountsbystore[thisorder.store_id][thisorder.date_add.strftime("%a %b %d, %Y")] += 1
					newusertotalsbystore[thisorder.store_id][thisorder.date_add.strftime("%a %b %d, %Y")] += float(thisorder.total)
				else:
					ordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["old"] += 1
					ordertotals[thisorder.date_add.strftime("%a %b %d, %Y")]["old"] += float(thisorder.total)

			if thisorder.order_status == 12: #food trials
				freeordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["FoodTrial"] += 1
				freeordersums[thisorder.date_add.strftime("%a %b %d, %Y")]["FoodTrial"] += float(thisorder.total)
			elif thisorder.order_status in [10,11]: #free on delivery
				freeordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["FreeDelivery"] += 1
				freeordersums[thisorder.date_add.strftime("%a %b %d, %Y")]["FreeDelivery"] += float(thisorder.total)

			if thisorder.coupon_id == 58: #coupon RKK
				freeordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["FoodTrial"] += 1
				freeordersums[thisorder.date_add.strftime("%a %b %d, %Y")]["FoodTrial"] += float(thisorder.sub_total)*1.13
			elif thisorder.coupon_id == 29: #free on delivery and coupon matata
				freeordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["FreeDelivery"] += 1
				freeordersums[thisorder.date_add.strftime("%a %b %d, %Y")]["FreeDelivery"] += float(thisorder.sub_total)*1.13

			
			if (thisorder.source == 0):
				platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["Android"] += 1
			elif (thisorder.source == 1):
				platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["Web"] += 1
			elif (thisorder.source ==2):
				platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["iOS"] += 1
			elif (thisorder.source ==6):
				platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["Zomato"] += 1
			elif (thisorder.source ==7):
				platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["Swiggy"] += 1
			elif (thisorder.source ==8):
				platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["Call"] += 1
		elif thisorder.order_status in returnedStates: #refunds
			freeordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["Returned"] += 1
			freeordersums[thisorder.date_add.strftime("%a %b %d, %Y")]["Returned"] += float(thisorder.total)
		

	neworders = []
	for thisdate in daterange:
		neworders.append(ordercounts[thisdate]["new"])

	totalneworders = sum(neworders)

	repeatorders = []
	for thisdate in daterange:
		repeatorders.append(ordercounts[thisdate]["old"])

	totalrepeatorders = sum(repeatorders)

	newsums = []
	for thisdate in daterange:
		newsums.append(ordertotals[thisdate]["new"])

	repeatsums = []
	for thisdate in daterange:
		repeatsums.append(ordertotals[thisdate]["old"])


	newusersbystore = {}
	for store_id in active_stores_list:
		templist = []
		for thisdate in daterange:
			templist.append(newusercountsbystore[store_id][thisdate])
		newusersbystore[store_id] = templist

	newusersumsbystore = {}
	for store_id in active_stores_list:
		templist = []
		for thisdate in daterange:
			templist.append(newusertotalsbystore[store_id][thisdate])
		newusersumsbystore[store_id] = templist

	androidorders = []
	weborders = []
	iosorders = []
	zomatoorders = []
	swiggyorders = []
	oncallorders = []

	for thisdate in daterange:
		androidorders.append(platformcounts[thisdate]["Android"])
		weborders.append(platformcounts[thisdate]["Web"])
		iosorders.append(platformcounts[thisdate]["iOS"])
		zomatoorders.append(platformcounts[thisdate]["Zomato"])
		swiggyorders.append(platformcounts[thisdate]["Swiggy"])
		oncallorders.append(platformcounts[thisdate]["Call"])

	foodtrialscount = []
	freedeliverycount = []
	returncount = []
	foodtrialstotal = []
	freedeliverytotal = []
	returntotal = []

	for thisdate in daterange:
		foodtrialscount.append(freeordercounts[thisdate]["FoodTrial"])
		freedeliverycount.append(freeordercounts[thisdate]["FreeDelivery"])
		returncount.append(freeordercounts[thisdate]["Returned"])
		foodtrialstotal.append(freeordersums[thisdate]["FoodTrial"])
		freedeliverytotal.append(freeordersums[thisdate]["FreeDelivery"])
		returntotal.append(freeordersums[thisdate]["Returned"])

	result = {"neworders": neworders, "repeatorders": repeatorders, "totalneworders": totalneworders, "totalrepeatorders": totalrepeatorders, "newsums": newsums, "repeatsums": repeatsums, "androidorders": androidorders, "weborders": weborders, "iosorders": iosorders, "zomatoorders": zomatoorders, "swiggyorders": swiggyorders,"oncallorders":oncallorders, "foodtrialscount": foodtrialscount, "freedeliverycount": freedeliverycount, "returncount": returncount, "foodtrialstotal": foodtrialstotal, "freedeliverytotal": freedeliverytotal, "returntotal":returntotal, "newusersbystore":newusersbystore,"newusersumsbystore":newusersumsbystore}
	return (result)

class StatsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):

		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 7
			else:
				horizon = int(horizon)

			parsedenddate = datetime.date.today() +  datetime.timedelta(days=1)
			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
			daterange = [parsedstartdate.strftime("%a %b %d, %Y")]
			for c in range(horizon-1):
				daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%a %b %d, %Y"))

		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date()
			parsedenddate = parsedenddate + datetime.timedelta(days=1)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%a %b %d, %Y"))

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		current_store = self.get_argument("store", "All")

		active_stores = statssession.query(store).filter(store.is_active == True).all()
		active_stores_list = [x.store_id for x in active_stores]

		if current_store == "All":
			store_list = active_stores_list
		else:
			store_list = [int(current_store)]
		
		current_store_name = "All"
		for thisstore in active_stores:
			if [thisstore.store_id] == current_store:
				current_store_name = thisstore.name
				break

		dailysalesquery = statssession.query(order.date_add, sqlalchemy.func.sum(order.total), sqlalchemy.func.sum(order.vat)).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.order_status.in_(deliveredStates + inProgress), order.store_id.in_(store_list)).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))

		totalsales = []

		thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[1]) for thisresult in dailysalesquery}
		for thisdate in daterange:
			if thisdate in thiscountdetails:
				totalsales.append(thiscountdetails[thisdate])
			else:
				totalsales.append(0)

		totalsalesvalue = sum(totalsales)

		totalcount = getTotalCount(parsedstartdate, parsedenddate, daterange, statssession,store_list)

		dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress + returnedStates), order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.store_id.in_(store_list)).all()

		detailedordercounts = getOrderCounts(parsedstartdate, parsedenddate, dailyordersquery, daterange, statssession)

		dailyorderids = [thisorder.order_id for thisorder in dailyordersquery if (thisorder.order_status not in returnedStates)]


		#### Now looking at actual sales

		grosssalesquery = statssession.query(orderdetail.date_add,orderdetail.quantity,orderdetail.price,orderdetailoption.price,orderdetail.menu_item_id).outerjoin(orderdetailoption).filter(orderdetail.order_id.in_(dailyorderids))
			
		grosssaleslookup = {}
		for grossdetail in grosssalesquery:
			if grossdetail[0].strftime("%a %b %d, %Y") in grosssaleslookup:
				grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] += (grossdetail[1]*grossdetail[2])	 	
			else:
			 	grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] = (grossdetail[1]*grossdetail[2])
			if grossdetail[3]:
				grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] += (grossdetail[1]*grossdetail[3])

		vatlookup = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[2]) for thisresult in dailysalesquery}

		grosssales = []
		netsalespretax = []

		for c in range(0, len(daterange)):
			try:
				grosssales.append(float(grosssaleslookup[daterange[c]]))
			except KeyError:
				grosssales.append(0.0)
			try:
				netsalespretax.append(float(totalsales[c]) - float(vatlookup[daterange[c]]))
			except KeyError:
				netsalespretax.append(0.0)

		dailyapc = []

		for c in range(len(daterange)):
			try: 
				dailyapc.append(grosssales[c]/totalcount[c])
			except ZeroDivisionError:
				dailyapc.append(0)

		totalgrosssales = sum(grosssales)
		totalnetsalespretax = sum(netsalespretax)

		feedbackonorders = statssession.query(feedback).filter(feedback.order_id.in_(dailyorderids), sqlalchemy.or_(feedback.food_rating > 0, feedback.delivery_rating > 0)).all()

		totalorders = len(dailyorderids)

		try:
			averageapc = totalgrosssales/totalorders
		except ZeroDivisionError:
			averageapc = 0

		orders_with_feedback = len(feedbackonorders)

		feedback_chart_data = [{"name": "Orders with Feedback", "y": orders_with_feedback}, {"name": "Orders without Feedback", "y": (totalorders - orders_with_feedback)}]

		food_rating_counts = [{"name": "5 stars", "y": 0, "sliced": "true", "selected": "true"}, {"name": "4 stars", "y": 0}, {"name": "3 stars", "y": 0}, {"name": "2 stars", "y": 0}, {"name": "1 star", "y": 0}]
		total_food_ratings = 0
		delivery_rating_counts = [{"name": "5 stars", "y": 0, "sliced": "true", "selected": "true"}, {"name": "4 stars", "y": 0}, {"name": "3 stars", "y": 0}, {"name": "2 stars", "y": 0}, {"name": "1 star", "y": 0}]
		total_delivery_ratings = 0

		for thisfeedback in feedbackonorders:
			if (thisfeedback.food_rating > 0):
				food_rating_counts[5-thisfeedback.food_rating]["y"] += 1
				total_food_ratings += 1
			if (thisfeedback.delivery_rating > 0):
				delivery_rating_counts[5-thisfeedback.delivery_rating]["y"] += 1
				total_delivery_ratings += 1

		newusersbystore = []
		for thisstore in active_stores:
			newusersbystore.append({"store_id": thisstore.store_id, "name": thisstore.name, "usercounts":detailedordercounts["newusersbystore"][thisstore.store_id], "usertotals":detailedordercounts["newusersumsbystore"][thisstore.store_id]})


		

		# predefs = {"Combos": [41,42,47,48], "Minute Maid": [25], "Pasta": [10,11,13,14,18,19,26,37,45], "Sandwich": [5,7,8,9,12,15,22,32,35,36], "Cheese Cake": [30], "Carrot Cake": [31], "Pita (/3)": [28,29], "Apple Strudel": [46], "Blueberry Brainfreezer": [49]}

		# predefitems = [cat for cat in predefs]

		# inputsmap = []

		# for cat in predefitems:
		# 	salecountquery = statssession.query(orderdetail.date_add, sqlalchemy.func.sum(orderdetail.quantity)).filter(orderdetail.date_add <= parsedenddate, orderdetail.date_add >= parsedstartdate, orderdetail.order_id.in_(dailyorderids), orderdetail.menu_item_id.in_(predefs[cat])).group_by(sqlalchemy.func.year(orderdetail.date_add), sqlalchemy.func.month(orderdetail.date_add), sqlalchemy.func.day(orderdetail.date_add))
			
		# 	thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): int(thisresult[1]) for thisresult in salecountquery}
		# 	thisinputslist = []
		# 	for thisdate in daterange:
		# 		if thisdate in thiscountdetails:
		# 			thisinputslist.append(thiscountdetails[thisdate])
		# 		else:
		# 			thisinputslist.append(0)

		# 	inputsmap.append({"name": cat, "data":thisinputslist})		

		current_user = self.get_current_user().decode()

		statssession.remove()
		self.render("templates/statstemplate.html", daterange=daterange, totalsales=totalsales, totalcount=totalcount, neworders=detailedordercounts["neworders"], repeatorders=detailedordercounts["repeatorders"], newsums=detailedordercounts["newsums"], repeatsums=detailedordercounts["repeatsums"], dailyapc=dailyapc, feedback_chart_data=feedback_chart_data, food_rating_counts=food_rating_counts, delivery_rating_counts=delivery_rating_counts, totalsalesvalue=totalsalesvalue, totalorders=totalorders, totalneworders=detailedordercounts["totalneworders"], totalrepeatorders=detailedordercounts["totalrepeatorders"], averageapc=averageapc, androidorders=detailedordercounts["androidorders"], weborders=detailedordercounts["weborders"], iosorders=detailedordercounts["iosorders"], zomatoorders=detailedordercounts["zomatoorders"], swiggyorders=detailedordercounts["swiggyorders"], oncallorders=detailedordercounts["oncallorders"],foodtrialstotal=detailedordercounts["foodtrialstotal"], freedeliverytotal=detailedordercounts["freedeliverytotal"], returntotal=detailedordercounts["returntotal"], foodtrialscount=detailedordercounts["foodtrialscount"], freedeliverycount=detailedordercounts["freedeliverycount"], returncount=detailedordercounts["returncount"], grosssales = grosssales, totalgrosssales = totalgrosssales, netsalespretax = netsalespretax, totalnetsalespretax = totalnetsalespretax, user=current_user, active_stores=active_stores, current_store=current_store, current_store_name=current_store_name, newusersbystore=newusersbystore)

class CustomerStatsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("admin", "review"):
			self.redirect('/stats')
		else:
			horizon = self.get_argument("horizon", None)
			startdate = self.get_argument("startmonth", None)
			enddate = self.get_argument("endmonth", None)
			if startdate is None:
				if horizon is None:
					horizon = 3
				else:
					horizon = int(horizon)
				parsedenddate = datetime.datetime.strptime(datetime.date.today().strftime("%Y-%m"),"%Y-%m").date()
				m, y = (parsedenddate.month-horizon) % 12, parsedenddate.year + ((parsedenddate.month)-horizon-1) // 12
				if not m: m = 12
				parsedstartdate = datetime.datetime(y, m, 1)
			else:
				parsedstartdate = datetime.datetime.strptime(startdate, "%Y-%m").date()
				parsedenddate = datetime.datetime.strptime(enddate, "%Y-%m").date()
				m, y = (parsedenddate.month+1) % 12, parsedenddate.year + ((parsedenddate.month)+1-1) // 12
				if not m: m = 12
				parsedenddate = datetime.datetime(y, m, 1)

			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))

			current_store = self.get_argument("store", "All")

			active_stores = statssession.query(store).filter(store.is_active == True).all()
			active_stores_list = [x.store_id for x in active_stores]

			if current_store == "All":
				store_list = active_stores_list
			else:
				store_list = [int(current_store)]
			
			current_store_name = "All"
			for thisstore in active_stores:
				if [thisstore.store_id] == current_store:
					current_store_name = thisstore.name
					break

			orders = statssession.query(order.order_id, order.user_id, order.date_add, order.total).filter(order.date_add < parsedenddate, order.date_add >= parsedstartdate, order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress)).all()

			firstorderquery = statssession.query(order.user_id,order.date_add).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress)).order_by(order.date_add).group_by(order.user_id)


			firstOrderLookup = {} #customer: first month
			for thisorder in firstorderquery:
				firstOrderLookup[thisorder.user_id] = thisorder.date_add.strftime("%Y-%m")


			customerLookup = {} #customers:order dates
			customerOrderLookup = {} #customers:order ids
			monthAllCustomerLookup = {} #month:all customers
			customers = set() #all customers
			months = [] #all months
			for thisorder in orders:
				thiscustomer = thisorder.user_id
				customers.add(thiscustomer)
				thisdate = thisorder.date_add
				thismonth = thisdate.strftime("%Y-%m")
				if (thismonth not in months):
					months.append(thismonth)
				
				if thiscustomer in customerLookup: 
					customerLookup[thiscustomer].append(thisdate)
					customerOrderLookup[thiscustomer].append(thisorder.order_id)
					if (thismonth in monthAllCustomerLookup):
						monthAllCustomerLookup[thismonth].add(thiscustomer)
					else:
						monthAllCustomerLookup[thismonth] = set([thiscustomer])
				else: 
					customerLookup[thiscustomer] = [thisdate]
					customerOrderLookup[thiscustomer] = [thisorder.order_id]

					if (thismonth in monthAllCustomerLookup):
						monthAllCustomerLookup[thismonth].add(thiscustomer)
					else:
						monthAllCustomerLookup[thismonth] = set([thiscustomer])

			monthRepeatOrderLookup = {} #month: all repeat orders
			monthNewOrderLookup = {} #month: new customer orders
			for thisorder in orders:
				thisdate = thisorder.date_add
				thismonth = thisdate.strftime("%Y-%m")
				if firstOrderLookup[thisorder.user_id] == thismonth:
					if thismonth in monthNewOrderLookup:
						monthNewOrderLookup[thismonth].add(thisorder)
					else:
						monthNewOrderLookup[thismonth] = set([thisorder])
				else:
					if thismonth in monthRepeatOrderLookup:
						monthRepeatOrderLookup[thismonth].add(thisorder)
					else:
						monthRepeatOrderLookup[thismonth] = set([thisorder])

			outputtable = "<table class='table table-striped table-hover tablesorter' style='width: 100%;'><thead><tr><th>Month</th><th>Active Users</th>"
			for m in months:
				outputtable += "<th>"+m+"</th>"
			outputtable += "<th>% Active in last 1 month</th><th>% Active in last 2 month</th><th>Dropped</th><th>% Dropped</th></thead></tr>"

			monthNewCustomerLookup = {} #month: new customers
			for month in range(len(months)):
				outputtable += "<tr><td>"+months[month]+"</td>"
				outputtable += "<td>"+str(len(monthAllCustomerLookup[months[month]]))+"</td>"
				followmonths = months[month+1:]
				lasttwomonths = months[-2:]
				returnedinlasttwomonths = set()
				followmonthsdata = {fm: 0 for fm in followmonths} #month m+i: no. of new customers who returned in month m+i
				totalreturned = set() #all new customers who returned in m+i months 
				newcustomers = set() #new customers in month m
				for tm in range(month):
					outputtable += "<td>-</td>"
				for customer in monthAllCustomerLookup[months[month]]: #all customers for month m
					if (firstOrderLookup[customer] == months[month]):
						newcustomers.add(customer)
				outputtable += "<td>"+str(len(newcustomers))+"</td>"
				monthNewCustomerLookup[months[month]] = newcustomers

				for nextmonth in followmonths:
					for customer in newcustomers:
						if customer in monthAllCustomerLookup[nextmonth]:
							followmonthsdata[nextmonth] += 1
							totalreturned.add(customer)
		
				for activemonth in lasttwomonths:
					for customer in newcustomers:
						if customer in monthAllCustomerLookup[activemonth]:
							returnedinlasttwomonths.add(customer)

				for fm in followmonths:
					outputtable += "<td>"+str(followmonthsdata[fm])+"</td>"
				
				if len(followmonths)>0:
					outputtable += "<td>"+"{:10.2f}".format((followmonthsdata[followmonths[len(followmonths)-1]])/len(newcustomers)*100)+"% </td>"
				else: #last row
						outputtable += "<td>100%</td>"

				outputtable += "<td>"+"{:10.2f}".format(len(returnedinlasttwomonths)/len(newcustomers)*100)+"% </td>"
				
				outputtable += "<td>"+str(len(newcustomers) - len(totalreturned))+"</td><td>"+"{:10.2f}".format((len(newcustomers) - len(totalreturned))/len(newcustomers)*100)+"% </td></tr>"
		
			outputtable += "</table>"

			allcustomersbymonth = [len(monthAllCustomerLookup[month]) for month in months]
			newcustomersbymonth = [len(monthNewCustomerLookup[month]) for month in months]
			repeatcustomersbymonth = [(len(monthAllCustomerLookup[month]) - len(monthNewCustomerLookup[month])) for month in months]
			newordersbymonth = [len(monthNewOrderLookup[month]) if month in monthNewOrderLookup else 0 for month in months]
			repeatordersbymonth = [len(monthRepeatOrderLookup[month])  if month in monthRepeatOrderLookup else 0 for month in months]


			#### Now looking at actual sales

			thisstoreorders = [thisorder.order_id for thisorder in orders]
			grosssalesquery = statssession.query(orderdetail.order_id,orderdetail.quantity,orderdetail.price,orderdetailoption.price).outerjoin(orderdetailoption).filter(orderdetail.order_id.in_(thisstoreorders))
			
			grosssaleslookup = {}
			for grossdetail in grosssalesquery:
				if grossdetail[0] in grosssaleslookup:  
					 grosssaleslookup[grossdetail[0]]+=float(grossdetail[1]*grossdetail[2])
				else:
					 grosssaleslookup[grossdetail[0]]=float(grossdetail[1]*grossdetail[2])
				if grossdetail[3]:
					grosssaleslookup[grossdetail[0]] += float(grossdetail[1]*grossdetail[3])
			
			alltotalsbymonth = [0.0 for m in range(len(months))]
			newtotalsbymonth = [0.0 for m in range(len(months))]
			repeattotalsbymonth = [0.0 for m in range(len(months))]
			
			for month in range(len(months)):
				if months[month] in monthNewOrderLookup: 
					for o in monthNewOrderLookup[months[month]]:
						if o.order_id in grosssaleslookup:
							newtotalsbymonth[month] += float (grosssaleslookup[o.order_id])
							alltotalsbymonth[month] += float (grosssaleslookup[o.order_id])
				if months[month] in monthRepeatOrderLookup: 
					for o in monthRepeatOrderLookup[months[month]]:
						if o.order_id in grosssaleslookup:
							repeattotalsbymonth[month] += float (grosssaleslookup[o.order_id])
							alltotalsbymonth[month] += float (grosssaleslookup[o.order_id])

			allAPC = [alltotalsbymonth[m]/(newordersbymonth[m]+repeatordersbymonth[m]) if (newordersbymonth[m]+repeatordersbymonth[m]) > 0 else 0.0 for m in range(len(months))]
			newAPC = [newtotalsbymonth[m]/newordersbymonth[m] if newordersbymonth[m] > 0 else 0.0 for m in range(len(months))]
			repeatAPC = [repeattotalsbymonth[m]/repeatordersbymonth[m] if repeatordersbymonth[m]>0 else 0.0 for m in range(len(months))]


			outputtableorders = "<table class='table cdxdc  table-striped table-hover tablesorter' style='width: 100%;'><thead><tr><th>Month</th><th>Cohort Members</th>"
			for m in months:
				outputtableorders += "<th>"+m+"</th>"
			outputtableorders += "</thead></tr>"
			for month in range(len(months)):
				outputtableorders += "<tr><td>"+months[month]+"</td>"
				outputtableorders += "<td>"+str(len(monthNewCustomerLookup[months[month]]))+"</td>"
				followmonths = months[month:]#+1
				followmonthsdata = {fm: 0 for fm in followmonths} 
				for tm in range(month):
					outputtableorders += "<td>-</td>"
				newcustomers = monthNewCustomerLookup[months[month]]
				for customer in newcustomers:
					myorderdates = customerLookup[customer]
					for orderdate in myorderdates:
						followmonthsdata[orderdate.strftime("%Y-%m")] += 1
				for fm in followmonths:
					outputtableorders += "<td>"+str(followmonthsdata[fm])+"</td>"
			outputtableorders += "</table>"


			outputtablevalues = "<table class='table cdxdc  table-striped table-hover tablesorter' style='width: 100%;'><thead><tr><th>Month</th><th>Cohort Members</th>"
			for m in months:
				outputtablevalues += "<th>"+m+"</th>"
			outputtablevalues += "</thead></tr>"
			for month in range(len(months)):
				outputtablevalues += "<tr><td>"+months[month]+"</td>"
				outputtablevalues += "<td>"+str(len(monthNewCustomerLookup[months[month]]))+"</td>"
				followmonths = months[month:]#+1
				followmonthsdata = {fm: 0 for fm in followmonths} 
				for tm in range(month):
					outputtablevalues += "<td>-</td>"
				newcustomers = monthNewCustomerLookup[months[month]]
				for customer in newcustomers:
					myorderdates = customerLookup[customer]
					myorders = customerOrderLookup[customer]
					for i in range(len(myorderdates)):
						#some order_ids are not in the gross lookup - 1,2,3,4,41307
						if myorders[i] in grosssaleslookup: 
							followmonthsdata[myorderdates[i].strftime("%Y-%m")] += grosssaleslookup[myorders[i]]
				for fm in followmonths:
					outputtablevalues += "<td>"+str(followmonthsdata[fm])+"</td>"
			outputtablevalues += "</table>"



			current_user = self.get_current_user().decode()

			statssession.remove()
			self.render("templates/customerstatstemplate.html", user=current_user, outputtable=outputtable, months=months, allcustomers=allcustomersbymonth, newcustomers=newcustomersbymonth, repeatcustomers=repeatcustomersbymonth, neworders=newordersbymonth,repeatorders=repeatordersbymonth, alltotals=alltotalsbymonth, newtotals=newtotalsbymonth,repeattotals=repeattotalsbymonth,allAPC=allAPC, newAPC=newAPC,repeatAPC=repeatAPC, outputtableorders=outputtableorders, outputtablevalues=outputtablevalues)


class OrderStatsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):

		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 7
			else:
				horizon = int(horizon)

			parsedenddate = datetime.date.today() +  datetime.timedelta(days=1)

			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
			daterange = [parsedstartdate.strftime("%a %b %d, %Y")]
			for c in range(horizon-1):
				daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%a %b %d, %Y"))
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date()
			parsedenddate = parsedenddate + datetime.timedelta(days=1)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%a %b %d, %Y"))

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		current_store = self.get_argument("store", "All")

		active_stores = statssession.query(store).filter(store.is_active == True).all()
		active_stores_list = [x.store_id for x in active_stores]

		if current_store == "All":
			store_list = active_stores_list
		else:
			store_list = [int(current_store)]
		
		current_store_name = "All"
		for thisstore in active_stores:
			if [thisstore.store_id] == current_store:
				current_store_name = thisstore.name
				break

		dailysalesquery = statssession.query(order.date_add).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.order_status.in_(deliveredStates + inProgress), order.store_id.in_(store_list))

		orderstatsresult = {thisdate: {hour:0 for hour in range(0,24)} for thisdate in daterange}
		for thisorder in dailysalesquery:
			orderstatsresult[thisorder.date_add.strftime("%a %b %d, %Y")][thisorder.date_add.hour] += 1

		hourrange = range(0,24)
		showresultinterim = {thisdate: {"name": thisdate, "data": []} for thisdate in daterange}
		for thisdate in daterange:
			for thishour in hourrange:
				showresultinterim[thisdate]["data"].append(orderstatsresult[thisdate][thishour])

		showresult = []
		for thisdate in daterange:
			showresult.append(showresultinterim[thisdate])

		current_user = self.get_current_user().decode()

		statssession.remove()

		self.render("templates/orderstatstemplate.html", daterange=daterange, hourrange=hourrange, showresult=showresult, user=current_user, active_stores=active_stores, current_store=current_store, current_store_name=current_store_name)

class ItemStatsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ["admin", "headchef", "chef", "chef03"]:
			self.redirect('/stats')
		else:
			horizon = self.get_argument("horizon", None)
			startdate = self.get_argument("startdate", None)
			enddate = self.get_argument("enddate", None)

			if startdate is None:
				if horizon is None:
					horizon = 7
				else:
					horizon = int(horizon)

				parsedenddate = datetime.date.today() +  datetime.timedelta(days=1)

				parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
				daterange = [parsedstartdate.strftime("%a %b %d, %Y")]
				for c in range(horizon-1):
					daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%a %b %d, %Y"))
			
			else:
				parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date()
				parsedenddate = parsedenddate + datetime.timedelta(days=1)
				parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
				daterange = []
				for c in range((parsedenddate - parsedstartdate).days):
					daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%a %b %d, %Y"))

			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))

			current_store = self.get_argument("store", "All")

			active_stores = statssession.query(store).filter(store.is_active == True).all()
			active_stores_list = [x.store_id for x in active_stores]

			if current_store == "All":
				store_list = active_stores_list
			else:
				store_list = [int(current_store)]
			
			current_store_name = "All"
			for thisstore in active_stores:
				if [thisstore.store_id] == current_store:
					current_store_name = thisstore.name
					break


			dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.store_id.in_(store_list))

			dailyorderids = [thisorder.order_id for thisorder in dailyordersquery]
			dailyordersdatelookup = {thisorder.order_id: thisorder.date_add.strftime("%a %b %d, %Y") for thisorder in dailyordersquery}

			cookingstations = [{'id':1,'name':'Sandwich'}, {'id':2,'name':'HotStation'},{'id':8,'name':'Dessert'},{'id':16,'name':'Pizza'},{'id':32,'name':'Grilled'}]


			csmap = []

			for thiscs in cookingstations:
				relevantmenuitems = statssession.query(menuitem.menu_item_id).filter(menuitem.cooking_station == thiscs['id'])
				thiscountquery = statssession.query(orderdetail.date_add, sqlalchemy.func.sum(orderdetail.quantity), orderdetail.order_id).filter(orderdetail.order_id.in_(dailyorderids), orderdetail.menu_item_id.in_(relevantmenuitems)).group_by(sqlalchemy.func.year(orderdetail.date_add), sqlalchemy.func.month(orderdetail.date_add), sqlalchemy.func.day(orderdetail.date_add))
				thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): int(thisresult[1]) for thisresult in thiscountquery}
				thiscslist = []
				for thisdate in daterange:
					if thisdate in thiscountdetails:
						thiscslist.append(thiscountdetails[thisdate])
					else:
						thiscslist.append(0)

				csmap.append({"name": thiscs['name'], "data":thiscslist})

			allcsidtoname = {0:'None',1:'Sandwich', 2:'Hot Station',4:'Salad Station',8:'Dessert',16:'Pizza',32:'Grilled',64:'Soup',3:'Combo',5:'Combo',10:'Combo',11:'Combo',12:'Combo',13:'Combo'}

			menuitems = {thismenuitem.menu_item_id: {"name": thismenuitem.name, "cooking_station":allcsidtoname[thismenuitem.cooking_station], "total": 0, "datelookup": {thisdate: 0 for thisdate in daterange}} for thismenuitem in statssession.query(menuitem)}

			for suborder in statssession.query(orderdetail).filter(orderdetail.order_id.in_(dailyorderids)):
				menuitems[suborder.menu_item_id]["datelookup"][dailyordersdatelookup[suborder.order_id]] += suborder.quantity
				menuitems[suborder.menu_item_id]["total"] += suborder.quantity

			active_stores = statssession.query(store).filter(store.is_active == True).all()

			current_store_name = "All"
			for thisstore in active_stores:
				if [thisstore.store_id] == current_store:
					current_store_name = thisstore.name
					break

			itemhtml = "<table class='table table-striped table-hover tablesorter' style='width: 100%;'><thead><tr><th>Dish</th><th>Cooking Station</th><th>Total</th>"
			for thisdate in daterange:
				itemhtml += "<th>" + thisdate + "</th>"

			itemhtml += "</tr><tbody>"
			for thismenuitem in menuitems:
				if menuitems[thismenuitem]["total"] == 0:
					continue
				itemhtml += "<tr><td style='font-weight: bold;'>" + menuitems[thismenuitem]["name"] + "</td>"
				itemhtml += "<td style='font-weight: bold;'>" + str(menuitems[thismenuitem]["cooking_station"]) + "</td>"
				itemhtml += "<td style='font-weight: bold;'>" + str(menuitems[thismenuitem]["total"]) + "</td>"
				for thisdate in daterange:
					if menuitems[thismenuitem]["datelookup"][thisdate] == 0:
						itemhtml += "<td>-</td>"
					else:
						itemhtml += "<td>" + str(menuitems[thismenuitem]["datelookup"][thisdate]) + "</td>"
				itemhtml += "</tr>"
			itemhtml += "</tbody></table>"

			statssession.remove()
			self.render("templates/itemstatstemplate.html", daterange=daterange, csmap=csmap, itemhtml=itemhtml, active_stores=active_stores, current_store=current_store, current_store_name=current_store_name, user=current_user)

class UserStatsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			horizon = self.get_argument("horizon", None)
			startdate = self.get_argument("startdate", None)
			enddate = self.get_argument("enddate", None)
			if startdate is None:
				if horizon is None:
					horizon = 7
				else:
					horizon = int(horizon)

				parsedenddate = datetime.date.today() +  datetime.timedelta(days=1)

				parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
				daterange = [parsedstartdate.strftime("%a %b %d, %Y")]
				for c in range(horizon-1):
					daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%a %b %d, %Y"))
			
			else:
				parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date()
				parsedenddate = parsedenddate + datetime.timedelta(days=1)
				parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
				daterange = []
				for c in range((parsedenddate - parsedstartdate).days):
					daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%a %b %d, %Y"))

			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))

			dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate)
			dailyorderids = [thisorder.order_id for thisorder in dailyordersquery]
			orderdetailsquery = statssession.query(orderdetail).filter(orderdetail.order_id.in_(dailyorderids))
			orderdetailslookup = {thisorder.order_id: [] for thisorder in dailyordersquery}
			for thisorderdetail in orderdetailsquery:
				orderdetailslookup[thisorderdetail.order_id].append(thisorderdetail)

			resultlookup = {}
			countlookup = {}

			for thisorder in dailyordersquery:
				if thisorder.user_id not in resultlookup:
					resultlookup[thisorder.user_id] = 0
					countlookup[thisorder.user_id] = 0
				countlookup[thisorder.user_id] += 1
				revenue = thisorder.total
				cost = thisorder.cost
				#cost = 0
				delivery = 60
				#for thisorderitem in orderdetailslookup[thisorder.order_id]:
				#	cost += thisorderitem.item_cost + thisorderitem.packaging_cost
				profit = revenue - cost - delivery
				if (thisorder.user_id == 116):
					print (thisorder.user_id, profit, thisorder.order_id)
				resultlookup[thisorder.user_id] += profit

			users = len([x for x in resultlookup])

			lossthreshold = 0
			med1threshold = 100
			med2threshold = 500
			highthreshold = 1000
			lossmakers = 0
			med1makers = 0
			med2makers = 0
			med3makers = 0
			highmakers = 0

			order1threshold = 1
			order2threshold = 2
			order3threshold = 5
			order4threshold = 7
			order5threshold = 10
			counter1 = 0
			counter2 = 0
			counter3 = 0
			counter4 = 0
			counter5 = 0

			lossmakerids = []

			for user in resultlookup:
				if resultlookup[user] < lossthreshold:
					lossmakers += 1
					lossmakerids.append(user)
				elif resultlookup[user] >= lossthreshold and resultlookup[user] < med1threshold:
					med1makers += 1
				elif resultlookup[user] >= med1threshold and resultlookup[user] < med2threshold:
					med2makers += 1
				elif resultlookup[user] >= med2threshold and resultlookup[user] < highthreshold:
					med3makers += 1
				elif resultlookup[user] > highthreshold:
					highmakers += 1

			for user in countlookup:
				if countlookup[user] >= order1threshold and countlookup[user] < order2threshold:
					counter1 += 1 
				elif countlookup[user] >= order2threshold and countlookup[user] < order3threshold:
					counter2 += 1 
				elif countlookup[user] >= order3threshold and countlookup[user] < order4threshold:
					counter3 += 1 
				elif countlookup[user] >= order4threshold and countlookup[user] < order5threshold:
					counter4 += 1 
				elif countlookup[user] >= order5threshold:
					counter5 += 1 

			lossmakerstring = ""
			for lossmakerid in lossmakerids:
				lossmakerstring += str(lossmakerid) + ", "

			statssession.remove()
			self.render("templates/userstemplate.html", daterange=daterange, lossmakers=lossmakers, med1makers=med1makers, med2makers=med2makers, med3makers=med3makers, highmakers=highmakers, counter1=counter1, counter2=counter2, counter3=counter3, counter4=counter4, counter5=counter5, users=users, lossmakerids=lossmakerids, user=current_user)

class storemenuitem(statsBase):
	__tablename__ = "store_menu_items"
	store_menu_item_id = Column("store_menu_item_id", Integer, primary_key=True)
	store_id = Column("store_id", String)
	menu_item_id = Column("menu_item_id", String)
	avl_quantity = Column("avl_quantity", String)
	selling_price = Column("selling_price", Integer)
	cost_price = Column("cost_price", Integer)
	discount = Column("discount", Integer)
	discount_type = Column("discount_type", Integer)
	discount_quantity = Column("discount_quantity", Integer)
	packaging_cost = Column("packaging_cost", Integer)
	is_active = Column("is_active", Integer)
	priority = Column("priority", Integer)

	def getJson(self):
		return {
			"store_menu_item_id": self.store_menu_item_id,
			"store_id": self.store_id,
			"menu_item_id": self.menu_item_id
		}

class store(statsBase):
	__tablename__ = "stores"
	store_id = Column("store_id", Integer, primary_key=True)
	name = Column("name", String)
	is_active = Column("is_active", Boolean)
	
def getDishType():
	statsengine = sqlalchemy.create_engine(statsengine_url)
	statssession = scoped_session(sessionmaker(bind=statsengine))

	tags = statssession.query(tag).all()
	menu_item_tags = statssession.query(menu_item_tag).all()
	vegtagid = None
	nonvegtagid = None
	eggtagid = None
	for thistag in tags:
		if thistag.name == "#VEG":
			vegtagid = thistag.tag_id
		if thistag.name == "#NONVEG":
			nonvegtagid = thistag.tag_id
		if thistag.name == "#EGG":
			eggtagid = thistag.tag_id

	vegitems = [mit.menu_item_id for mit in menu_item_tags if mit.tag_id == vegtagid]
	nonvegitems = [mit.menu_item_id for mit in menu_item_tags if mit.tag_id == nonvegtagid]
	eggitems = [mit.menu_item_id for mit in menu_item_tags if mit.tag_id == eggtagid]

	statssession.remove()
	return (vegitems, nonvegitems, eggitems)

def getStoreItems(current_store):
	statsengine = sqlalchemy.create_engine(statsengine_url)
	statssession = scoped_session(sessionmaker(bind=statsengine))

	store_items = statssession.query(storemenuitem).filter(storemenuitem.store_id == current_store).all()
	menu_items = statssession.query(menuitem).all()

	menu_item_mapping = {thismenuitem.menu_item_id: thismenuitem for thismenuitem in menu_items}
	store_items.sort(key=lambda x: (-int(format(x.is_active, '08b')[-1]), -x.priority))
	activelist = [{"name": menu_item_mapping[x.menu_item_id].name, "menu_item_id": x.menu_item_id, "store_menu_item_id": x.store_menu_item_id, "quantity": x.avl_quantity, "is_active": isActiveItem(x), "priority": x.priority, "price": x.selling_price, "discount": x.discount, "image": menu_item_mapping[x.menu_item_id].img_url, "description": menu_item_mapping[x.menu_item_id].description} for x in store_items if isActiveItem(x)]
	inactivelist = [{"name": menu_item_mapping[x.menu_item_id].name, "menu_item_id": x.menu_item_id, "store_menu_item_id": x.store_menu_item_id, "quantity": x.avl_quantity, "is_active": isActiveItem(x), "priority": x.priority, "price": x.selling_price, "discount": x.discount, "image": menu_item_mapping[x.menu_item_id].img_url, "description": menu_item_mapping[x.menu_item_id].description} for x in store_items if not isActiveItem(x)]
	# for i in store_items:
	# 	print (menu_item_mapping[i.menu_item_id].name, format(i.is_active, '08b'), bool(int(format(i.is_active, '08b')[-1])))
	
	active_stores = statssession.query(store).filter(store.is_active == True).all()

	current_store_name = ""
	for thisstore in active_stores:
		if thisstore.store_id == current_store:
			current_store_name = thisstore.name
			break

	statssession.remove()

	return (activelist, inactivelist, active_stores, current_store_name)

def isActiveItem(store_item):
	return bool(int(format(store_item.is_active, '08b')[-1]))

class StoreItemsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("headchef", "chef", "chef03", "admin"):
			self.redirect('/stats')
		else:
			current_store = self.get_argument("store", 2)
			if current_user == "chef03":
				current_store = 3
			if current_user == "chef":
				current_store = 2

			current_store = int(current_store)

			storeitems = getStoreItems(current_store)
			self.render("templates/storeitems.html", activelist = storeitems[0], inactivelist = storeitems[1], activeitems = len(storeitems[0]), active_stores=storeitems[2], current_store=current_store, current_store_name=storeitems[3], user=current_user)

class TodayMenuHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "chef":
			self.redirect('/stats')
		else:
			current_store = 2
			storeitems = getStoreItems(current_store)
			self.render("templates/todaysmenu.html", activelist = storeitems[0], activeitems = len(storeitems[0]), user=current_user)

def flip(input, status):
	inputb = format(input, "08b")
	output = ""
	if status == "true":
		output = inputb[0:-1] + "1"
	else:
		output = inputb[0:-1] + "0"
	return int(output,2)

class UpdateItemsActiveHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		store_menu_item_id = int(self.get_argument("store_menu_item_id"))
		status = self.get_argument("checked")

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		store_items = statssession.query(storemenuitem).all()
		store_items.sort(key=lambda x: (-int(format(x.is_active, '08b')[-1]), -x.priority))
		active_store_items = []
		inactive_store_items = []
		selected_menu_item = None
		for store_item in store_items:
			if (store_item.store_menu_item_id == store_menu_item_id):
				selected_menu_item = store_item
			elif isActiveItem(store_item):
				active_store_items.append(store_item)
			else:
				inactive_store_items.append(store_item)

		selected_menu_item.is_active = flip(selected_menu_item.is_active, status)
		if status == "true":
			selected_menu_item.priority = 1000*(len(active_store_items)+1)
		else:
			selected_menu_item.priority = 1000*(len(inactive_store_items)+1)
		
		for i in range(0, len(active_store_items)):
			active_store_items[i].priority = 1000*(len(active_store_items) - i)
		for i in range(0, len(inactive_store_items)):
			inactive_store_items[i].priority = 1000*(len(inactive_store_items) - i)

		statssession.commit()
		self.write({"action": True})
		statssession.remove()

class MoveItemsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		store_menu_item_id = int(self.get_argument("store_menu_item_id"))
		index = int(self.get_argument("index"))
		
		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		store_items = statssession.query(storemenuitem).all()
		store_items = [x for x in store_items if isActiveItem(x)]
		store_items.sort(key=lambda x: (-x.priority))
		finallist = [x for x in store_items if x.store_menu_item_id != store_menu_item_id]
		thisitem = [x for x in store_items if x.store_menu_item_id == store_menu_item_id][0]
		finallist.insert(index, thisitem)
		
		for i in range(0, len(finallist)):
			finallist[i].priority = 1000*(len(finallist) - i)

		statssession.commit()
		self.write({"action": True})
		statssession.remove()

class UpdateQuantityHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		store_menu_item_id = int(self.get_argument("store_menu_item_id"))
		quantity = int(self.get_argument("quantity"))

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		store_item = statssession.query(storemenuitem).filter(storemenuitem.store_menu_item_id == store_menu_item_id).one()
		store_item.avl_quantity = quantity

		statssession.commit()
		self.write({"action": True})
		statssession.remove()

def get_service(api_name, api_version, scope, key_file_location, service_account_email):
	"""Get a service that communicates to a Google API.

	Args:
	api_name: The name of the api to connect to.
	api_version: The api version to connect to.
	scope: A list auth scopes to authorize for the application.
	key_file_location: The path to a valid service account p12 key file.
	service_account_email: The service account email address.

	Returns:
	A service that is connected to the specified API.
	"""

	credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file_location, scopes=scope)

	http = credentials.authorize(httplib2.Http())

	# Build the service object.
	service = build(api_name, api_version, http=http)

	return service

def get_first_profile_id(service):
	# Use the Analytics service object to get the first profile id.

	# Get a list of all Google Analytics accounts for this user
	accounts = service.management().accounts().list().execute()

	if accounts.get('items'):
		# Get the first Google Analytics account.
		account = accounts.get('items')[0].get('id')

	# Get a list of all the properties for the first account.
	properties = service.management().webproperties().list(accountId=account).execute()

	if properties.get('items'):
		# Get the first property id.
		property = properties.get('items')[0].get('id')

		# Get a list of all views (profiles) for the first property.
		profiles = service.management().profiles().list(accountId=account, webPropertyId=property).execute()

		if profiles.get('items'):
			# return the first view (profile) id.
			return profiles.get('items')[0].get('id')

	return None

def get_results(service, profile_id):
	# Use the Analytics Service Object to query the Core Reporting API
	# for the number of sessions within the past seven days.
	return service.data().ga().get(
		ids='ga:' + profile_id,
		start_date='7daysAgo',
		end_date='today',
		metrics='ga:sessions').execute()

def print_results(results):
	# Print data nicely for the user.
	if results:
		print('View (Profile): %s' % results.get('profileInfo').get('profileName'))
		print('Total Sessions: %s' % results.get('rows')[0][0])

	else:
		print('No results found')

def getAnalyticsData(start_date, end_date, metrics, dimensions, sort=None):
	# Define the auth scopes to request.
	scope = ['https://www.googleapis.com/auth/analytics.readonly']

	# Use the developer console and replace the values with your
	# service account email and relative location of your key file.
	service_account_email = 'twigly-analytics@global-terrain-***REMOVED***.iam.gserviceaccount.com'
	key_file_location = 'analytics.json'

	# Authenticate and construct service.
	service = get_service('analytics', 'v3', scope, key_file_location, service_account_email)
	profile = get_first_profile_id(service)
	if (sort == None):
		api_query = service.data().ga().get(
		    ids="ga:" + profile,
		    start_date=start_date,
		    end_date=end_date,
		    metrics=metrics,
		    dimensions=dimensions)
	else:
		api_query = service.data().ga().get(
		    ids="ga:" + profile,
		    start_date=start_date,
		    end_date=end_date,
		    metrics=metrics,
		    dimensions=dimensions,
		    sort=sort)
	results = api_query.execute()
	return results.get('rows')

def getPlatform(input):
	if (input == "Wap" or input == "Web"):
		return "Web"
	elif (input.count(".") == 2):
		return "Android"
	elif (input.count(".") < 2):
		return "iOS"
	else:
		return input

class AnalyticsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("admin", "review"):
			self.redirect('/stats')
		else:
			horizon = self.get_argument("horizon", None)
			startdate = self.get_argument("startdate", None)
			enddate = self.get_argument("enddate", None)
			if startdate is None:
				if horizon is None:
					horizon = 7
				else:
					horizon = int(horizon)

				parsedenddate = datetime.date.today() +  datetime.timedelta(days=1)

				parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
				gastartdate = parsedstartdate.strftime("%Y-%m-%d")
				gaenddate = (parsedenddate - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
				daterange = [parsedstartdate.strftime("%a %b %d, %Y")]
				resultdatelookup = {parsedstartdate.strftime("%Y%m%d"): parsedstartdate.strftime("%a %b %d, %Y")}
				for c in range(horizon-1):
					resultdatelookup[(parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%Y%m%d")] = (parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%a %b %d, %Y")
					daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%a %b %d, %Y"))
			else:
				parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date()
				parsedenddate = parsedenddate + datetime.timedelta(days=1)
				parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
				gastartdate = parsedstartdate.strftime("%Y-%m-%d")
				gaenddate = (parsedenddate - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
				daterange = []
				resultdatelookup = {parsedstartdate.strftime("%Y%m%d"): parsedstartdate.strftime("%a %b %d, %Y")}
				for c in range((parsedenddate - parsedstartdate).days):
					resultdatelookup[(parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%Y%m%d")] = (parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%a %b %d, %Y")
					daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%a %b %d, %Y"))

			userresults = getAnalyticsData(gastartdate, gaenddate, 'ga:users, ga:newUsers', 'ga:date')

			userresultslookup = {thisdate: {"users": 0, "newusers": 0} for thisdate in daterange}
			for result in userresults:
				userresultslookup[resultdatelookup[result[0]]]["users"] = int(result[1])
				userresultslookup[resultdatelookup[result[0]]]["newusers"] = int(result[2])

			userslist = [userresultslookup[thisdate]["users"] for thisdate in daterange]
			newuserslist = [userresultslookup[thisdate]["newusers"] for thisdate in daterange]

			totalusers = sum(userslist)
			totalnewusers = sum(newuserslist)

			current_store = self.get_argument("store", "All")

			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))

			active_stores = statssession.query(store).filter(store.is_active == True).all()
			active_stores_list = [x.store_id for x in active_stores]

			if current_store == "All":
				store_list = active_stores_list
			else:
				store_list = [int(current_store)]

			current_store_name = "All"
			for thisstore in active_stores:
				if [thisstore.store_id] == current_store:
					current_store_name = thisstore.name
					break

			totalcount = getTotalCount(parsedstartdate, parsedenddate, daterange, statssession, store_list)

			dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate).all()

			detailedordercounts = getOrderCounts(parsedstartdate, parsedenddate, dailyordersquery, daterange, statssession)

			dailyconversion = []
			for d in range(0, len(daterange)):
				dailyconversion.append(totalcount[d]/userslist[d])

			newconversion = []
			for d in range(0, len(daterange)):
				newconversion.append(detailedordercounts["neworders"][d]/newuserslist[d])

			overallconversion = sum(totalcount)/totalusers
			overallnewconversion = detailedordercounts["totalneworders"]/totalnewusers

			trafficsourcedata = getAnalyticsData(gastartdate, gaenddate, 'ga:users', 'ga:date, ga:source', '-ga:users, ga:source')
			trafficresults = {}
			trafficsources = []
			for result in trafficsourcedata:
				if result[1] not in trafficsources:
					try:
						trafficsources.append(result[1])
					except UnicodeDecodeError:
						trafficsources.append(result[1].decode())
				if resultdatelookup[result[0]] in trafficresults:
					try:
						trafficresults[resultdatelookup[result[0]]][result[1]] = int(result[2])
					except UnicodeDecodeError:
						trafficresults[resultdatelookup[result[0]]][result[1].decode()] = int(result[2])
				else:
					try:
						trafficresults[resultdatelookup[result[0]]] = {result[1]: int(result[2])}
					except UnicodeDecodeError:
						trafficresults[resultdatelookup[result[0]]] = {result[1].decode(): int(result[2])}
			
			trafficintermediate = {}
			for thisdate in daterange:
				for source in trafficsources:
					if source in trafficresults[thisdate]:
						if source in trafficintermediate:
							trafficintermediate[source].append(trafficresults[thisdate][source])
						else:
							trafficintermediate[source] = [trafficresults[thisdate][source]]
					else:
						if source in trafficintermediate:
							trafficintermediate[source].append(0)
						else:
							trafficintermediate[source] = [0]

			trafficdatatodisplay = []
			for source in trafficintermediate:
				trafficdatatodisplay.append({"name": source, "data": trafficintermediate[source]})

			platformdata = getAnalyticsData(gastartdate, gaenddate, 'ga:users', 'ga:date, ga:appVersion')

			platformresults = {}
			platforms = []
			for result in platformdata:
				thisplatform = getPlatform(result[1])
				if thisplatform not in platforms:
					platforms.append(thisplatform)
				if resultdatelookup[result[0]] in platformresults:
					if thisplatform in platformresults[resultdatelookup[result[0]]]:
						platformresults[resultdatelookup[result[0]]][thisplatform] += int(result[2])
					else:
						platformresults[resultdatelookup[result[0]]][thisplatform] = int(result[2])
				else:
					platformresults[resultdatelookup[result[0]]] = {thisplatform: int(result[2])}

			platformintermediate = {}
			for thisdate in daterange:
				for platform in platformresults[thisdate]:
					if platform in platformintermediate:
						platformintermediate[platform].append(platformresults[thisdate][platform])
					else:
						platformintermediate[platform] = [platformresults[thisdate][platform]]

			platformdatatoshow = []
			for platform in platformintermediate:
				platformdatatoshow.append({"name": platform, "data": platformintermediate[platform]})

			androidconversionseries = []
			webconversionseries = []
			iosconversionseries = []

			for d in range(0, len(daterange)):
				androidconversionseries.append(detailedordercounts["androidorders"][d]/platformintermediate["Android"][d])
				webconversionseries.append(detailedordercounts["weborders"][d]/platformintermediate["Web"][d])
				iosconversionseries.append(detailedordercounts["iosorders"][d]/platformintermediate["iOS"][d])

			androidconversion = sum(detailedordercounts["androidorders"])/sum(platformintermediate["Android"])
			webconversion = sum(detailedordercounts["weborders"])/sum(platformintermediate["Web"])
			iosconversion = sum(detailedordercounts["iosorders"])/sum(platformintermediate["iOS"])

			newusersbystore = []
			for thisstore in active_stores:
				newusersbystore.append({"store_id": thisstore.store_id, "name": thisstore.name, "usercounts":detailedordercounts["newusersbystore"][thisstore.store_id], "usertotals":detailedordercounts["newusersumsbystore"][thisstore.store_id]})

			statssession.remove()

			self.render("templates/userstatstemplate.html", daterange=daterange, userslist=userslist, newuserslist=newuserslist, totalusers=totalusers, totalnewusers=totalnewusers, dailyconversion=dailyconversion, newconversion=newconversion, overallconversion=overallconversion, overallnewconversion=overallnewconversion, trafficdatatodisplay=dumps(trafficdatatodisplay), platformdatatoshow=dumps(platformdatatoshow), androidconversionseries=androidconversionseries, webconversionseries=webconversionseries, iosconversionseries=iosconversionseries, androidconversion=androidconversion, webconversion=webconversion, iosconversion=iosconversion, user=current_user, newusersbystore=newusersbystore)

class SendMailHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			current_store = 2
			current_store_item_details = getStoreItems(current_store)
			activelist = current_store_item_details[0]
			inactivelist = current_store_item_details[1]
			vegitems, nonvegitems, eggitems = getDishType()

			for activeitem in activelist:
				if activeitem["menu_item_id"] in vegitems:
					activeitem["type"] = "v"
				elif activeitem["menu_item_id"] in nonvegitems:
					activeitem["type"] = "n"
				elif activeitem["menu_item_id"] in eggitems:
					activeitem["type"] = "e"
				else:
					activeitem["type"] = ""

			for inactiveitem in inactivelist:
				if inactiveitem["menu_item_id"] in vegitems:
					inactiveitem["type"] = "v"
				elif inactiveitem["menu_item_id"] in nonvegitems:
					inactiveitem["type"] = "n"
				elif inactiveitem["menu_item_id"] in eggitems:
					inactiveitem["type"] = "e"
				else:
					inactiveitem["type"] = ""
			self.render("templates/sendmailtemplate.html", activelist = activelist, inactivelist = inactivelist, user=current_user)

def createMail(itemlist):
	current_store = 2
	current_store_item_details = getStoreItems(current_store)
	activelist = current_store_item_details[0]
	inactivelist = current_store_item_details[1]

	vegitems, nonvegitems, eggitems = getDishType()

	for activeitem in activelist:
		if activeitem["menu_item_id"] in vegitems:
			activeitem["type"] = "v"
		elif activeitem["menu_item_id"] in nonvegitems:
			activeitem["type"] = "n"
		elif activeitem["menu_item_id"] in eggitems:
			activeitem["type"] = "e"
		else:
			activeitem["type"] = ""

	for inactiveitem in inactivelist:
		if inactiveitem["menu_item_id"] in vegitems:
			inactiveitem["type"] = "v"
		elif inactiveitem["menu_item_id"] in nonvegitems:
			inactiveitem["type"] = "n"
		elif inactiveitem["menu_item_id"] in eggitems:
			inactiveitem["type"] = "e"
		else:
			inactiveitem["type"] = ""

	itemlookup = {item["store_menu_item_id"]: item for item in activelist}
	inactiveitemlookup = {item["store_menu_item_id"]: item for item in inactivelist}
	itemlookup.update(inactiveitemlookup)
	finallist = [itemlookup[int(x)] for x in itemlist.split(",")]
	return finallist

def getMailTemplate(template):
	if (template == 2):
		return ("templates/mailtemplate2.html", "")
	elif (template == 3):
		return ("templates/mailtemplate3.html", "")
	elif (template == 4):
		return ("templates/mailtemplate4.html", "")
	elif (template == 5):
		return ("templates/mailtemplate4.html", "red")
	elif (template == 6):
		return ("templates/mailtemplate4.html", "green")
	elif (template == 7):
		return ("templates/mailtemplate4.html", "purple")
	else:
		return ("templates/mailtemplate.html", "")

class MailPreviewHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			subject = unquote(self.get_argument("subject"))
			header = unquote(self.get_argument("header"))
			length = int(self.get_argument("items"))
			itemlist = self.get_argument("itemlist")
			finallist = createMail(itemlist)
			sod = int(self.get_argument("sod", "-1"))
			dod = int(self.get_argument("dod", "-1"))
			template = int(self.get_argument("template", "1"))
			mailtemplate = getMailTemplate(template)
			self.render(template_name = mailtemplate[0], activeitems = finallist, header = header, length = length, sod=sod, dod=dod, color=mailtemplate[1])

class MailchimpHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			current_store = 2
			activelist = getStoreItems(current_store)[0]
			subject = unquote(self.get_argument("subject"))
			header = unquote(self.get_argument("header"))
			length = int(self.get_argument("items"))
			itemlist = self.get_argument("itemlist")
			finallist = createMail(itemlist)
			sod = int(self.get_argument("sod", "-1"))
			dod = int(self.get_argument("dod", "-1"))
			template = int(self.get_argument("template", "1"))
			mailtemplate = getMailTemplate(template)
			
			content = self.render_string(template_name = mailtemplate[0], activeitems = finallist, header = header, length = length, sod=sod, dod=dod, color=mailtemplate[1])

			#Change this variable to change the list
			list_id = "ea0d1e3356"
			# ea0d1e3356 is the main Twigly list
			# list_id = "d2a7019f47"
			# d2a7019f47 is the test list

			mailerror = False
			try:
				mailchimp = Mailchimp(mailchimpkey)
				newCampaign = mailchimp.campaigns.create(type="regular", options={"list_id": list_id, "subject": subject, "from_email": "@testmail.com", "from_name": "Twigly", "to_name": "*|FNAME|*", "title": subject, "authenticate": True, "generate_text": True}, content={"html": content})
				mailchimp.campaigns.send(newCampaign["id"])
			except:
				mailerror = True
				print ("Unexpected error:" + sys.exc_info()[0])

			if (mailerror):
				self.write({"result": False})
			else:
				self.write({"result": True})


class MailchimpUpdateHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			startdate = self.get_argument("startdate", None)
			if startdate is None:
				parsedstartdate = datetime.date.today()
			else:
				parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()

			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))

			thissql1 = "select email, name from users where email is not null and date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00';" 
			result1 = statsengine.execute(thissql1)

			userids = []
			for item in result1:
				userids.append({"email":str(item[0]).lower(), "name":str(item[1]).title()})
		
			statssession.remove()

			#Change this variable to change the list
			list_id = "ea0d1e3356"
			# ea0d1e3356 is the main Twigly list
			# list_id = "d2a7019f47"
			# d2a7019f47 is the test list

			mailerror = False
			batch_list = []
			for item in userids:
				batch_list.append({'email':{'email':item['email']}, 'email_type':'html', 'merge_vars':{'FNAME':item['name']}})
			try:
				m = Mailchimp(mailchimpkey)
				mailchimpresponse = m.lists.batch_subscribe(list_id, batch_list, double_optin=False)
			except Exception as e:
				print ("Unexpected error:",e)

			if (mailchimpresponse['error_count']>0):
				self.write({"result": False})
				msg = MIMEMultipart()
				fromaddr = '@testmail.com'
				toaddr = '***REMOVED***'				
				msg['From'] = fromaddr
				msg['To'] = toaddr
				msg['Subject'] = str(mailchimpresponse['error_count'])+" error(s) in mailchimp List for "+parsedstartdate.strftime("%Y-%m-%d")
				body = str(mailchimpresponse)
				msg.attach(MIMEText(body, 'plain'))
				host = 'email-smtp.us-east-1.amazonaws.com'
				port = 587
				user = "***REMOVED***"
				password = "***REMOVED***"
				server = smtplib.SMTP(host, port)
				server.starttls()
				server.login(user, password)
				server.sendmail(fromaddr, toaddr, msg.as_string())
				server.quit()
			else:
				self.write({"result": True})

class MailchimpLazySignupHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			parsedstartdate = datetime.date.today() - datetime.timedelta(days=2)

			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))

			thissql1 = "select u.email from users u where u.email is not null and u.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and u.date_add<='" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select o.user_id from orders o where order_status in (3,10,11) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00');" 
			result1 = statsengine.execute(thissql1)

			userids = []
			for item in result1:
				userids.append({"email":str(item[0]).lower()})
			
			statssession.remove()

			#Change this variable to change the list
			list_id = "ea0d1e3356"
			# ea0d1e3356 is the main Twigly list
			# list_id = "d2a7019f47"
			# d2a7019f47 is the test list

			template_id = 139741 # int

			static_segment_id = 60393 # int..  main list
			# static_segment_id = 60389 # int.. for test list
			
			batch_list = []
			for item in userids:
				batch_list.append({'email':item['email']})

			# batch_list.append({'email':'***REMOVED***'})


			try:
				m = Mailchimp(mailchimpkey)
				#Create a segment for lazy signups
				# mcresponse = m.lists.static_segment_add(list_id,"Lazy Signups")
				# print(mcresponse)

				mcresponse = m.lists.static_segment_reset(list_id,static_segment_id)
				mcresponse = m.lists.static_segment_members_add(list_id,static_segment_id,batch_list)
				subject = "Great food is just 3 clicks away"
				mcresponse = m.campaigns.create(type="regular", options={"list_id": list_id, "subject": subject, "from_email": "@testmail.com", "from_name": "Twigly", "to_name": "*|FNAME|*", "title": subject, "authenticate": True, "generate_text": True, "template_id":template_id}, content={"sections": {}}, segment_opts={"saved_segment_id":static_segment_id})
				mre2 = m.campaigns.send(mcresponse["id"])

			except Exception as e:
				print ("Unexpected error:",e)

			if ('complete' in mre2 and mre2['complete']==True):
				self.write({"result": True})
				msg = MIMEMultipart()
				fromaddr = '@testmail.com'
				toaddr = '***REMOVED***'				
				msg['From'] = fromaddr
				msg['To'] = toaddr
				msg['Subject'] =  str(len(batch_list))+" recepients of Lazy campaign for "+parsedstartdate.strftime("%Y-%m-%d")
				body = "Email sent successfully to " + str(batch_list)
				msg.attach(MIMEText(body, 'plain'))
				host = 'email-smtp.us-east-1.amazonaws.com'
				port = 587
				user = "***REMOVED***"
				password = "***REMOVED***"
				server = smtplib.SMTP(host, port)
				server.starttls()
				server.login(user, password)
				server.sendmail(fromaddr, toaddr, msg.as_string())
				server.quit()
			else:
				self.write({"result": False})
				msg = MIMEMultipart()
				fromaddr = '@testmail.com'
				toaddr = '***REMOVED***'				
				msg['From'] = fromaddr
				msg['To'] = toaddr
				msg['Subject'] =  "Some error in the Lazy mailchimp campaign for "+parsedstartdate.strftime("%Y-%m-%d")
				body = str(mre2)
				msg.attach(MIMEText(body, 'plain'))
				host = 'email-smtp.us-east-1.amazonaws.com'
				port = 587
				user = "***REMOVED***"
				password = "***REMOVED***"
				server = smtplib.SMTP(host, port)
				server.starttls()
				server.login(user, password)
				server.sendmail(fromaddr, toaddr, msg.as_string())
				server.quit()


class FeedbackHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("admin", "headchef"):
			self.redirect('/stats')
		
		page = int(self.get_argument('p', 0))
		pagesize = 30

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		feedbacks = statssession.query(feedback).order_by(feedback.feedback_id.desc()).slice(page*pagesize, (page+1)*pagesize)
		relevantorders = [thisfeedback.order_id for thisfeedback in feedbacks]

		thisorders = statssession.query(order).filter(order.order_id.in_(relevantorders))
		orderslookup = {thisorder.order_id: thisorder for thisorder in thisorders}
		thisorderdetails = statssession.query(orderdetail).filter(orderdetail.order_id.in_(relevantorders))
		orderdetailslookup = {thisorder.order_id: [thisorderdetail for thisorderdetail in thisorderdetails if thisorderdetail.order_id == thisorder.order_id] for thisorder in thisorders}
		relevantmenuitems = [thisorderdetail.menu_item_id for thisorderdetail in thisorderdetails]
		menuitemdetails = statssession.query(menuitem).filter(menuitem.menu_item_id.in_(relevantmenuitems))
		menuitemlookup = {thismenuitem.menu_item_id: thismenuitem.name for thismenuitem in menuitemdetails}
		relevantusers = [thisorder.user_id for thisorder in thisorders]
		users = statssession.query(user).filter(user.user_id.in_(relevantusers))
		userlookup = {thisuser.user_id: thisuser for thisuser in users}

		results = [{"feedback": thisfeedback, "order": orderslookup[thisfeedback.order_id], "orderdetails": orderdetailslookup[thisfeedback.order_id]} for thisfeedback in feedbacks]

		statssession.remove()

		self.render("templates/feedbacktemplate.html", results=results, menuitems=menuitemlookup, userlookup=userlookup, page=page, user=current_user)

class datewise_store_menu_item(statsBase):
	__tablename__ = "datewise_store_menu"
	datewise_store_menu_item_id = Column("datewise_store_menu_item_id", Integer, primary_key=True)
	store_menu_item_id = Column("store_menu_item_id", Integer)
	date_effective = Column("date_effective", DateTime)
	priority = Column("priority", Integer)
	avl_quantity = Column("avl_quantity", Integer)
	is_active = Column("is_active", Boolean)


class store_ingredient_inventory(statsBase):
    __tablename__ = 'store_ingredient_inventory'
    inventory_id = Column('inventory_id', Integer, primary_key=True)
    store_id = Column('store_id', Integer)
    batch_id = Column('batch_id', Integer, ForeignKey("ingredient_batches.batch_id"))
    date_effective = Column('date_effective', DateTime)
    daywise_batch_number = Column('daywise_batch_number', Integer)
    actual_units = Column('actual_units', Float)
    role = Column('role', Integer)

class ingredient_batches(statsBase):
    __tablename__ = "ingredient_batches"
    batch_id = Column('batch_id', Integer, primary_key=True)
    ingredient_id = Column('ingredient_id', Integer, ForeignKey("ingredients.ingredient_id"))

class ingredients(statsBase):
    __tablename__ = "ingredients"
    ingredient_id = Column('ingredient_id', Integer, primary_key=True)
    pack_size = Column('pack_size', Integer)
    cost = Column('cost', Float)


class WastageHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("admin", "headchef"):
			self.redirect('/stats')

		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 7
			else:
				horizon = int(horizon)

			parsedenddate = datetime.date.today() +  datetime.timedelta(days=1)

			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
			daterange = [parsedstartdate.strftime("%a %b %d, %Y")]
			for c in range(horizon-1):
				daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%a %b %d, %Y"))
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date()
			parsedenddate = parsedenddate + datetime.timedelta(days=1)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%a %b %d, %Y"))

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		active_stores = statssession.query(store).filter(store.is_active == True).all()

		dwactivestates = [1,3,5,7,9]
		dwstoreitemsquery = statssession.query(datewise_store_menu_item).filter(datewise_store_menu_item.date_effective < parsedenddate, datewise_store_menu_item.date_effective >= parsedstartdate, datewise_store_menu_item.is_active.in_(dwactivestates))
		
		storeitemsquery = statssession.query(storemenuitem).all()
		storeitemslookup = {x.store_menu_item_id: x for x in storeitemsquery}
		menuitemsquery = statssession.query(menuitem).all()
		menuitemlookup = {x.menu_item_id: x for x in menuitemsquery}

		dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate).all()

		#dailyorderids = [thisorder.order_id for thisorder in dailyordersquery]

		storeingredientinventoryquery = statssession.query(store_ingredient_inventory,ingredient_batches,ingredients).join(ingredient_batches).join(ingredients).filter(store_ingredient_inventory.date_effective < parsedenddate,store_ingredient_inventory.date_effective >= parsedstartdate, store_ingredient_inventory.role.in_([3,14]),store_ingredient_inventory.actual_units>0).all()
		grosssales = []
		predictedsales = []
		wastage = []
		storewastage=[]
		wastagepc = []
		stores = []

		for thisstore in active_stores:
			#### First looking at production
			peritemwastage = {dr: {} for dr in daterange}
			thisdwsmis = [dwsmi for dwsmi in dwstoreitemsquery if storeitemslookup[dwsmi.store_menu_item_id].store_id == thisstore.store_id and storeitemslookup[dwsmi.store_menu_item_id].selling_price > 0]
			dwsmilookup = {}
			for dwsmi in thisdwsmis:
				if dwsmi.date_effective.strftime("%a %b %d, %Y") in dwsmilookup:
					dwsmilookup[dwsmi.date_effective.strftime("%a %b %d, %Y")] += (dwsmi.avl_quantity*storeitemslookup[dwsmi.store_menu_item_id].selling_price)
				else:
					dwsmilookup[dwsmi.date_effective.strftime("%a %b %d, %Y")] = (dwsmi.avl_quantity*storeitemslookup[dwsmi.store_menu_item_id].selling_price)

				if storeitemslookup[dwsmi.store_menu_item_id].menu_item_id in peritemwastage[dwsmi.date_effective.strftime("%a %b %d, %Y")]:
					peritemwastage[dwsmi.date_effective.strftime("%a %b %d, %Y")][storeitemslookup[dwsmi.store_menu_item_id].menu_item_id] += dwsmi.avl_quantity
				else:
					peritemwastage[dwsmi.date_effective.strftime("%a %b %d, %Y")][storeitemslookup[dwsmi.store_menu_item_id].menu_item_id] = dwsmi.avl_quantity

			#### Now looking at actual sales

			thisstoreorders = [thisorder.order_id for thisorder in dailyordersquery if thisorder.store_id == thisstore.store_id]
			
			grosssalesquery = statssession.query(orderdetail.date_add,orderdetail.quantity,orderdetail.price,orderdetailoption.price,orderdetail.menu_item_id).outerjoin(orderdetailoption).filter(orderdetail.order_id.in_(thisstoreorders))
				
			grosssaleslookup = {}
			for grossdetail in grosssalesquery:
				if grossdetail[0].strftime("%a %b %d, %Y") in grosssaleslookup:
					grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] += (grossdetail[1]*grossdetail[2])	 	
				else:
				 	grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] = (grossdetail[1]*grossdetail[2])
				if grossdetail[3]:
					grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] += (grossdetail[1]*grossdetail[3])

				if grossdetail[0].strftime("%a %b %d, %Y") in peritemwastage:
					if grossdetail[4] in peritemwastage[grossdetail[0].strftime("%a %b %d, %Y")]:
						peritemwastage[grossdetail[0].strftime("%a %b %d, %Y")][grossdetail[4]] -= grossdetail[1]
				else:
					peritemwastage[grossdetail[0].strftime("%a %b %d, %Y")] = {}
					peritemwastage[grossdetail[0].strftime("%a %b %d, %Y")][grossdetail[4]] = -grossdetail[1]

			wastagelookup = {dr: 0 for dr in daterange}
			midlookup = {smi.menu_item_id: smi for smi in storeitemsquery if smi.store_id == thisstore.store_id}
			for dr in peritemwastage:
				for menuitemid in peritemwastage[dr]:
					if peritemwastage[dr][menuitemid] > 0:
						wastagelookup[dr] += (peritemwastage[dr][menuitemid]*midlookup[menuitemid].cost_price)

			storewastagelookup = {dr: 0 for dr in daterange}
			storewastageitems = [(thisinventory,thisbatch,thisingredient) for (thisinventory,thisbatch,thisingredient) in storeingredientinventoryquery if thisinventory.store_id == thisstore.store_id]
			
			for (inv,bat,ing) in storewastageitems:
				if inv.date_effective.strftime("%a %b %d, %Y") in storewastagelookup:
					storewastagelookup[inv.date_effective.strftime("%a %b %d, %Y")] += (inv.actual_units*ing.cost/ing.pack_size)
				else:
					storewastagelookup[inv.date_effective.strftime("%a %b %d, %Y")] = inv.actual_units*ing.cost/ing.pack_size

			thisgrosssales = []
			thispredictedsales = []
			thiswastage = []
			thisstorewastage = []
			thiswastagepc = []

			for c in range(0, len(daterange)):
				try:
					thispredictedsales.append(float(dwsmilookup[daterange[c]]))
				except KeyError:
					thispredictedsales.append(0.0)

				try:
					thisgrosssales.append(float(grosssaleslookup[daterange[c]]))
				except KeyError:
					thisgrosssales.append(0.0)

				try:
					thiswastage.append(float(wastagelookup[daterange[c]]))
				except KeyError:
					thiswastage.append(0.0)	

				try:
					thisstorewastage.append(float(storewastagelookup[daterange[c]]))
				except KeyError:
					thiswastage.append(0.0)	

				try:
					thiswastagepc.append(float(storewastagelookup[daterange[c]])/float(grosssaleslookup[daterange[c]])*100.0)
				except KeyError:
					thiswastagepc.append(0.0)	


			grosssales.append(thisgrosssales)
			predictedsales.append(thispredictedsales)
			wastage.append(thiswastage)
			storewastage.append(thisstorewastage)
			wastagepc.append(thiswastagepc)
			stores.append({"store_id": thisstore.store_id, "name": thisstore.name, "grosssales": sum(thisgrosssales), "predictedsales": sum(thispredictedsales), "wastage": sum(thiswastage), "storewastage":sum(thisstorewastage),"wastagepc": sum(thisstorewastage)/sum(thisgrosssales)*100})

		totalgrosssales = 0
		totalpredictedsales = 0
		totalwastage = 0
		totalstorewastage = 0
		companygrosssales = [0 for dr in daterange]
		companypredictedsales = [0 for dr in daterange]
		companywastage = [0 for dr in daterange]
		companystorewastage = [0 for dr in daterange]
		companywastagepc = [0 for dr in daterange]
		for i in range(len(stores)):
			totalgrosssales += stores[i]["grosssales"]
			totalpredictedsales += stores[i]["predictedsales"]
			totalwastage += stores[i]["wastage"]
			totalstorewastage += stores[i]["storewastage"]

			for j in range(len(daterange)):
				companygrosssales[j] += grosssales[i][j]
				companypredictedsales[j] += predictedsales[i][j]
				companywastage[j] += wastage[i][j]
				companystorewastage[j] += storewastage[i][j]
		
		for k in range(len(daterange)):
			try:
				companywastagepc[k] = float(companystorewastage[k]/companygrosssales[k]*100.0)
			except:
				pass

		stores.insert(0, {"store_id": 0, "name": "Twigly", "grosssales": totalgrosssales, "predictedsales": totalpredictedsales, "wastage": totalwastage, "storewastage":totalstorewastage,"wastagepc": totalstorewastage/totalgrosssales*100.0})
		grosssales.insert(0, companygrosssales)
		predictedsales.insert(0, companypredictedsales)
		wastage.insert(0, companywastage)
		storewastage.insert(0, companystorewastage)
		wastagepc.insert(0, companywastagepc)
		statssession.remove()

		self.render("templates/wastagetemplate.html", daterange=daterange, grosssales=grosssales, predictedsales=predictedsales, wastage=wastage, storewastage=storewastage, wastagepc=wastagepc, stores=stores, numstores=len(stores), user=current_user)

class GetStoreItemsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		storeitems = statssession.query(storemenuitem).all()
		menuitems = statssession.query(menuitem).all()

		response = {"storeitems": [x.getJson() for x in storeitems], "menuitems": [y.getJson() for y in menuitems]}

		active_stores = statssession.query(store).filter(store.is_active == True).all()
		active_stores_list = [x.store_id for x in active_stores]

		enddate = self.get_argument("date", None)
		parsedenddate = datetime.datetime.strptime(enddate, "%Y-%m-%d").date()
		parsedenddate = parsedenddate - datetime.timedelta(days=6)
		parsedstartdate = parsedenddate - datetime.timedelta(days=1)
		daterange = [parsedstartdate.strftime("%a %b %d, %Y")]

		totalcount = getTotalCount(parsedstartdate, parsedenddate, daterange, statssession, active_stores_list)
		response["last_week"] = totalcount[0]

		statssession.remove()

		self.write(response)

class SetDateWiseMenuHandler(BaseHandler):
	@tornado.web.authenticated
	def post(self):
		thisdate = datetime.datetime.strptime(self.get_argument("date"), "%Y-%m-%d").date()
		thisdata = loads(self.get_argument("data"))
		
		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		storeitems = statssession.query(storemenuitem).all()
		storeitemslookup = {x.store_menu_item_id: x for x in storeitems}

		currentdwitems = statssession.query(datewise_store_menu_item).filter(datewise_store_menu_item.date_effective == thisdate).delete(synchronize_session=False)

		statssession.commit()

		storedata = {}
		for storeitem in storeitems:
			if storeitem.store_id in storedata:
				pass
			else:
				storedata[storeitem.store_id] = []

		for item in thisdata:
			thisdatewiseitem = datewise_store_menu_item()
			thisdatewiseitem.date_effective = thisdate
			thisdatewiseitem.store_menu_item_id = item["store_menu_item_id"]
			thisdatewiseitem.avl_quantity = item["avl_quantity"]
			thisdatewiseitem.is_active = True
			thisstoreid = storeitemslookup[item["store_menu_item_id"]].store_id
			storedata[thisstoreid].append(thisdatewiseitem)
			statssession.add(thisdatewiseitem)

		for store in storedata:
			thisstoreitems = len(storedata[store])
			for i in range(0, thisstoreitems):
				storedata[store][i].priority = 100000*store + (thisstoreitems - i)*100

		statssession.commit()
		statssession.remove()


# class delivery(statsBase):
# 	__tablename__ = "deliveries"
# 	delivery_id = Column("delivery_id", Integer, primary_key=True)
# 	order_id = Column("order_id", Integer)
# 	delivery_boy_id = Column("delivery_boy_id", Integer)

# class ordertime(statsBase):
# 	__tablename__ = "order_status_time"
# 	delivery_id = Column("order_status_time_id", Integer, primary_key=True)
# 	order_id = Column("order_id", Integer)
# 	delivery_boy_id = Column("order_status", Integer)
# 	time_add = Column("time_add", DateTime)

class DeliveryHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("admin"):
			self.redirect('/stats')

		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 7
			else:
				horizon = int(horizon)

			parsedenddate = datetime.date.today() +  datetime.timedelta(days=1)

			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
			daterange = [parsedstartdate.strftime("%a %b %d, %Y")]
			for c in range(horizon-1):
				daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%a %b %d, %Y"))
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date()
			parsedenddate = parsedenddate + datetime.timedelta(days=1)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%a %b %d, %Y"))

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))


		#delivery boy rating query 1
		from sqlalchemy import text
		thissql1 = text("select a.delivery_boy_id,d.name,count(*),sum(case when c.falls_under_gurantee = 1 then 1 else 0 end) as count_priority,sum(case when c.falls_under_gurantee = 0 then 1 else 0 end) as count_np,sum(case when g.delivery_rating>0 then 1 else 0 end) as total_rated,sum(case when g.delivery_rating>0 then delivery_rating else 0 end)/sum(case when g.delivery_rating>0 then 1 else 0 end) as avg_rated,sum(case when g.delivery_rating=1 then 1 else 0 end) as rated_1,sum(case when g.delivery_rating=2 then 1 else 0 end) as rated_2, sum(case when b.order_status = 10 then 1 else 0 end) as free_orders from orders b left join deliveries a on a.order_id=b.order_id left join delivery_zones c on b.delivery_zone_id=c.delivery_zone_id left join delivery_boys d on d.delivery_boy_id=a.delivery_boy_id left join feedbacks g on g.order_id = b.order_id where b.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and b.order_status in (3,10,11) group by 1,2;")

		result1 = statsengine.execute(thissql1)

		resultlookup = {x[0]: x[1:] for x in result1}

		#delivery boy rating query 2
		thissql2 = text("select a.delivery_boy_id, d.name, count(*), sum(case when c.falls_under_gurantee = 1 then timestampdiff(minute,e.time_add,f.time_add) else 0 end)/sum(case when c.falls_under_gurantee = 1 then 1 else 0 end) as time_p, sum(case when c.falls_under_gurantee = 0 then timestampdiff(minute,e.time_add,f.time_add) else 0 end)/sum(case when c.falls_under_gurantee = 0 then 1 else 0 end) as time_np from orders b left join deliveries a on a.order_id=b.order_id left join delivery_zones c on b.delivery_zone_id=c.delivery_zone_id left join delivery_boys d on d.delivery_boy_id=a.delivery_boy_id left join order_status_times e on b.order_id=e.order_id left join order_status_times f on b.order_id=f.order_id left join feedbacks g on g.order_id = a.order_id where b.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and b.order_status in (3,10,11) and e.order_status=2 and f.order_status =15 group by 1,2;")

		result2 = statsengine.execute(thissql2)
		# for row in result2:
		# 	if row[0] in resultlookup:
		# 		resultlookup[row[0]] += row[2:]
		# 	else:
		# 		resultlookup[row[0]] = [row[0],row[1],"-","-","-","-","-","-","-"] + list(row[2:])

		for row in result2:
			resultlookup[row[0]] += row[2:]

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>DB ID</th><th>Name</th><th>Total Orders</th><th>Priority Orders</th><th>Non Priority Orders</th><th>Total Ratings</th><th>Average Rating</th><th>Orders Rated 1</th><th>Orders Rated 2</th><th>Free Orders</th><th class='part2'>Count with Rating</th><th class='part2'>Time for Priority Orders</th><th class='part2'>Time for Non-Priority Orders</th></thead>"
		
		for db in resultlookup:
			if len(resultlookup[db]) == 12:
				outputtable += "<tr><td>" + str(db) + "</td><td>" + resultlookup[db][0] + "</td><td>" + str(resultlookup[db][1]) + "</td><td>" + str(resultlookup[db][2]) + "</td><td>" + str(resultlookup[db][3]) + "</td><td>" + str(resultlookup[db][4]) + "</td><td>" + str(resultlookup[db][5]) + "</td><td>" + str(resultlookup[db][6]) + "</td><td>" + str(resultlookup[db][7]) + "</td><td>" + str(resultlookup[db][8]) + "</td><td class='part2'>" + str(resultlookup[db][9]) + "</td><td class='part2'>" + str(resultlookup[db][10]) + "</td><td class='part2'>" + str(resultlookup[db][11]) + "</td></tr>"
			else:
				outputtable += "<tr><td>" + str(db) + "</td><td>" + resultlookup[db][0] + "</td><td>" + str(resultlookup[db][1]) + "</td><td>" + str(resultlookup[db][2]) + "</td><td>" + str(resultlookup[db][3]) + "</td><td>" + str(resultlookup[db][4]) + "</td><td>" + str(resultlookup[db][5]) + "</td><td>" + str(resultlookup[db][6]) + "</td><td>" + str(resultlookup[db][7]) + "</td><td>" + str(resultlookup[db][8]) + "</td><td class='part2'>-</td><td class='part2'>-</td><td class='part2'>-</td></tr>"
		
		outputtable += "</table>"



		#delivery boy comments
		thissql3 = text("select c.delivery_boy_id, d.name, b.date_add, a.order_id, a.delivery_rating, a.comment from feedbacks a left join orders b on a.order_id=b.order_id left join deliveries c on b.order_id=c.order_id left join delivery_boys d on c.delivery_boy_id=d.delivery_boy_id where b.order_status in (3,10,11) and a.delivery_rating in (1,2) and b.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add <'" +parsedenddate.strftime("%Y-%m-%d") + " 00:00:00';")

		result3 = statsengine.execute(thissql3)
		deliveryfeedback = {}
		
		outputtable2 = "<table class='table tablesorter table-striped table-hover'><thead><th>DB ID</th><th>Name</th><th>Order Date</th><th>Order ID</th><th>Delivery Rating</th><th>Comment</th></thead>"
		
		for item in result3:
			outputtable2 += "<tr><td>" + str(item[0]) + "</td><td>" + str(item[1]) + "</td><td>" + str(item[2]) + "</td><td><a href='http://twigly.in/admin/orders?f="+str(item[3])+"'>" + str(item[3]) + "</a></td><td>" + str(item[4]) + "</td><td style='text-align:left;'>" + str(item[5]) + "</td><tr>"

		outputtable2 += "</table>"


		# All Free deliveries
		thissql4 = text("select date(o.date_add), o.order_id, timediff(b.time_add,a.time_add), c.delivery_boy_id, d.name from orders o left join order_status_times as a on a.order_id=o.order_id left join order_status_times as b on b.order_id=o.order_id left join deliveries c on c.order_id=o.order_id left join delivery_boys d on d.delivery_boy_id=c.delivery_boy_id where o.order_status in (10) and a.order_status=0 and b.order_status=3 and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <'" +parsedenddate.strftime("%Y-%m-%d") + " 00:00:00';")

		result4 = statsengine.execute(thissql4)
		deliveryfeedback = {}
		
		outputtable3 = "<table class='table tablesorter table-striped table-hover'><thead><th>Order Date</th><th>Order ID</th><th>Received to Delivery Time</th><th>Delivery Boy ID</th><th>Delivery Boy Name</th></thead>"
		
		for item in result4:
			outputtable3 += "<tr><td>" + str(item[0]) + "</td><td><a href='http://twigly.in/admin/orders?f="+str(item[1])+"'>" + str(item[1]) + "</a></td><td>" + str(item[2]) + "</td><td>" + str(item[3]) + "</td><td>" + str(item[4]) + "</td><tr>"

		outputtable3 += "</table>"



		statssession.remove()
		self.render("templates/deliveriestemplate.html", outputtable=outputtable, outputtable2=outputtable2, outputtable3=outputtable3, user=current_user)


class DeliveryStatsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("admin"):
			self.redirect('/stats')

		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 7
			else:
				horizon = int(horizon)

			parsedenddate = datetime.date.today() +  datetime.timedelta(days=1)

			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
			daterange = [parsedstartdate.strftime("%a %b %d, %Y")]
			for c in range(horizon-1):
				daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%a %b %d, %Y"))
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date()
			parsedenddate = parsedenddate + datetime.timedelta(days=1)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%a %b %d, %Y"))

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))


		# average delivery rating by store
		active_stores = statssession.query(store).filter(store.is_active == True).all()
		active_stores_list = [x.store_id for x in active_stores]

		thissql3 = "select b.store_id, date(b.date_add), sum(case when g.delivery_rating>0 then delivery_rating else 0 end), sum(case when g.delivery_rating>0 then 1 else 0 end), sum(case when g.delivery_rating>0 then delivery_rating else 0 end)/sum(case when g.delivery_rating>0 then 1 else 0 end), sum(case when b.order_id>0 then 1 else 0 end) from orders b left join feedbacks g on g.order_id = b.order_id where b.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and b.order_status in (3,10,11) group by 1,2;" 
		result3 = statsengine.execute(thissql3)

		avgdeliverytimebystore = {x.store_id: {thisdate:0.0 for thisdate in daterange} for x in active_stores}
		totalordersbystore = {x.store_id: {thisdate:0 for thisdate in daterange} for x in active_stores}
		feedbacksreceivedsbystore = {x.store_id: {thisdate:0 for thisdate in daterange} for x in active_stores}
		for item in result3:
			if item[0] in active_stores_list:
				if item[1].strftime("%a %b %d, %Y") in daterange:
					if item[4]: avgdeliverytimebystore[item[0]][item[1].strftime("%a %b %d, %Y")] = item[4]
					if item[5]: totalordersbystore[item[0]][item[1].strftime("%a %b %d, %Y")] = item[5]
					if item[3]: feedbacksreceivedsbystore[item[0]][item[1].strftime("%a %b %d, %Y")] = item[3]
		
		avgdeliveryscorebystore = []
		for thisstore in active_stores:
			templist = []
			templist2 = []
			templist3 = []
			for thisdate in daterange:
				templist.append(float(avgdeliverytimebystore[thisstore.store_id][thisdate]))
				templist2.append(int(totalordersbystore[thisstore.store_id][thisdate]))
				templist3.append(int(feedbacksreceivedsbystore[thisstore.store_id][thisdate]))
			avgdeliveryscorebystore.append({"store_id": thisstore.store_id, "name": thisstore.name, "avgdeliveryscore":templist, "totalorders":templist2, "feedbacksreceived":templist3})

		# dispatch to reach time by store

		thissql4 = "select o.store_id, date(o.date_add), sum(case when timediff(b.time_add,a.time_add) <= '00:10:00' then 1 else 0 end) as count_0_10, sum(case when timediff(b.time_add,a.time_add) >'00:10:00' and timediff(b.time_add,a.time_add) <='00:20:00' then 1 else 0 end) as count_10_20, sum(case when timediff(b.time_add,a.time_add) >'00:20:00' and timediff(b.time_add,a.time_add) <='00:30:00' then 1 else 0 end) as count_20_30, sum(case when timediff(b.time_add,a.time_add) > '00:30:00' then 1 else 0 end) as count_30_plus from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id=b.order_id where a.order_status=2 and b.order_status=15 and o.order_status in (3,10,11) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"

		result4 = statsengine.execute(thissql4)
		deliverytimeresultsbystore = {x.store_id: { thisdate:[] for thisdate in daterange} for x in active_stores}
		for item in result4:
			if item[0] in active_stores_list:
				if item[1].strftime("%a %b %d, %Y") in daterange:
					deliverytimeresultsbystore[item[0]][item[1].strftime("%a %b %d, %Y")] = item[2:]

		deliverytimestack = []
		for thisstore in active_stores:
			list0_10 = []
			list10_20 = []
			list20_30 = []
			list30_plus = []
			for thisdate in daterange:
				list0_10.append(int(deliverytimeresultsbystore[thisstore.store_id][thisdate][0]))
				list10_20.append(int(deliverytimeresultsbystore[thisstore.store_id][thisdate][1]))
				list20_30.append(int(deliverytimeresultsbystore[thisstore.store_id][thisdate][2]))
				list30_plus.append(int(deliverytimeresultsbystore[thisstore.store_id][thisdate][3]))
			deliverytimestack.append({"store_id": thisstore.store_id, "name": thisstore.name, "deliverytime010":list0_10,"deliverytime1020":list10_20,"deliverytime2030":list20_30,"deliverytime30plus":list30_plus,})


		# priority vs non priority orders by store

		thissql5 = "select o.store_id, date(o.date_add),sum(case when c.falls_under_gurantee = 1 then 1 else 0 end) as count_priority, sum(case when c.falls_under_gurantee = 0 then 1 else 0 end) as count_np from orders o left join delivery_zones c on o.delivery_zone_id=c.delivery_zone_id where o.order_status in (3,10,11) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"

		result5 = statsengine.execute(thissql5)
		priorityorderresultsbystore = {x.store_id: { thisdate:[] for thisdate in daterange} for x in active_stores}
		for item in result5:
			if item[0] in active_stores_list:
				if item[1].strftime("%a %b %d, %Y") in daterange:
					priorityorderresultsbystore[item[0]][item[1].strftime("%a %b %d, %Y")] = item[2:]

		priorityorderstack = []
		for thisstore in active_stores:
			listpriority = []
			for thisdate in daterange:
				listpriority.append(float(100*priorityorderresultsbystore[thisstore.store_id][thisdate][1]/(priorityorderresultsbystore[thisstore.store_id][thisdate][0]+priorityorderresultsbystore[thisstore.store_id][thisdate][1]))) # non-priority order %age
			priorityorderstack.append({"store_id": thisstore.store_id, "name": thisstore.name,"prioritypc":listpriority})


		# Average cooking to dispatch time by store

		thissql6 = "select o.store_id, date(o.date_add), count(*), sum(time_to_sec(timediff(b.time_add,a.time_add))) as sumtime_cooking  from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id=b.order_id where a.order_status=1 and b.order_status=2 and o.order_status in (3,10,11) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"

		result6 = statsengine.execute(thissql6)
		cookingtodispatcklookup = {x.store_id: { thisdate:[] for thisdate in daterange} for x in active_stores}
		for item in result6:
			if item[0] in active_stores_list:
				if item[1].strftime("%a %b %d, %Y") in daterange:
					cookingtodispatcklookup[item[0]][item[1].strftime("%a %b %d, %Y")] = item[2:]


		# Average dispatch to reached dest time by store

		thissql7 = "select o.store_id, date(o.date_add), count(*), sum(time_to_sec(timediff(b.time_add,a.time_add))) as sumtime_dispatching  from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id=b.order_id where a.order_status=2 and b.order_status=15 and o.order_status in (3,10,11) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"
		result7 = statsengine.execute(thissql7)
		dispatchtoreachlookup = {x.store_id: { thisdate:[] for thisdate in daterange} for x in active_stores}
		for item in result7:
			if item[0] in active_stores_list:
				if item[1].strftime("%a %b %d, %Y") in daterange:
					dispatchtoreachlookup[item[0]][item[1].strftime("%a %b %d, %Y")] = item[2:]

		# Average reached to delivere dest time by store
		thissql8 = "select o.store_id, date(o.date_add), count(*), sum(time_to_sec(timediff(b.time_add,a.time_add))) as sumtime_delivering  from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id=b.order_id where a.order_status=15 and b.order_status=3 and o.order_status in (3,10,11) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"
		result8 = statsengine.execute(thissql8)
		reachtodeliverlookup = {x.store_id: { thisdate:[] for thisdate in daterange} for x in active_stores}
		for item in result8:
			if item[0] in active_stores_list:
				if item[1].strftime("%a %b %d, %Y") in daterange:
					reachtodeliverlookup[item[0]][item[1].strftime("%a %b %d, %Y")] = item[2:]

		cookingtimes = []
		for thisstore in active_stores:
			list1 = []
			list2 = []
			list3 = []
			for thisdate in daterange:
				list1.append(float(cookingtodispatcklookup[thisstore.store_id][thisdate][1]/cookingtodispatcklookup[thisstore.store_id][thisdate][0]/60)) # avg time in minutes
				list2.append(float(dispatchtoreachlookup[thisstore.store_id][thisdate][1]/dispatchtoreachlookup[thisstore.store_id][thisdate][0]/60)) # avg time in minutes
				list3.append(float(reachtodeliverlookup[thisstore.store_id][thisdate][1]/reachtodeliverlookup[thisstore.store_id][thisdate][0]/60)) # avg time in minutes
			cookingtimes.append({"store_id": thisstore.store_id, "name": thisstore.name,"cookingtime":list1,"dispatchtime":list2,"deliverytime":list3})

		statssession.remove()
		self.render("templates/deliverystatstemplate.html", daterange=daterange,avgdeliveryscorebystore=avgdeliveryscorebystore, deliverytimestack=deliverytimestack, priorityorderstack=priorityorderstack, cookingtimes=cookingtimes, user=current_user)

class PaymentStatsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("admin"):
			self.redirect('/stats')

		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 1
			else:
				horizon = int(horizon)

			parsedenddate = datetime.date.today() +  datetime.timedelta(days=1)

			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
			daterange = [parsedstartdate.strftime("%Y-%m-%d")]
			for c in range(horizon-1):
				daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%Y-%m-%d"))
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date()
			parsedenddate = parsedenddate + datetime.timedelta(days=1)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%Y-%m-%d"))

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))



		# users who had failure at PG
		thissql1 = "select date(date_add), count(distinct user_id) from orders where order_status in (13,14) and date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and date_add <'" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and payment_status not in (26) group by 1;"
		result1 = statsengine.execute(thissql1)

		userswhohadpgfailurelookup = {thisdate:0 for thisdate in daterange}
		for item in result1:
			if item[0].strftime("%Y-%m-%d") in daterange:
				userswhohadpgfailurelookup[item[0].strftime("%Y-%m-%d")] = item[1]
		userswhohadpgfailure = []
		for thisdate in daterange:
			userswhohadpgfailure.append(int(userswhohadpgfailurelookup[thisdate])) 
			
		# Those who ended up ordering
		thissql2 = "select date(a.date_add),count(distinct b.user_id) from orders a left join orders b on a.user_id=b.user_id where a.order_status in (13,14) and b.order_status in (3,10,11) and date(a.date_add) = date(b.date_add) and a.date_add > '" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and a.date_add < '" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add > '" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add < '" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and a.payment_status not in (26) group by 1;"

		result2 = statsengine.execute(thissql2)

		userswhoendeduporderinglookup = {thisdate:0 for thisdate in daterange}
		for item in result2:
			if item[0].strftime("%Y-%m-%d") in daterange:
				userswhoendeduporderinglookup[item[0].strftime("%Y-%m-%d")] = item[1]
		userswhoendedupordering = []
		for thisdate in daterange:
			userswhoendedupordering.append(int(userswhoendeduporderinglookup[thisdate])) 


		userswhodidnotreturn = []
		for i in range(len(daterange)):
			userswhodidnotreturn.append(userswhohadpgfailure[i]-userswhoendedupordering[i])



		# User who cancelled
		thissql3 = "select date(date_add),count(distinct user_id) from orders where order_status in (13,14) and date_add > '" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and date_add < '" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and payment_status in (26) group by 1;"

		result3 = statsengine.execute(thissql3)

		userswhocancelledlookup = {thisdate:0 for thisdate in daterange}
		for item in result3:
			if item[0].strftime("%Y-%m-%d") in daterange:
				userswhocancelledlookup[item[0].strftime("%Y-%m-%d")] = item[1]
		userswhocancelled = []
		for thisdate in daterange:
			userswhocancelled.append(int(userswhocancelledlookup[thisdate])) 




		# Users who did not return
		thissql4 = "select date(date_add), user_id from orders where order_status in (13,14) and date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and date_add <'" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and payment_status not in (26);"
		result4 = statsengine.execute(thissql4)

		useridswhohadpgfailurelookup = {thisdate:set() for thisdate in daterange}
		for item in result4:
			if item[0].strftime("%Y-%m-%d") in daterange:
				useridswhohadpgfailurelookup[item[0].strftime("%Y-%m-%d")].add(item[1])
		
		# Those who ended up ordering
		thissql5 = "select date(a.date_add), b.user_id from orders a left join orders b on a.user_id=b.user_id where a.order_status in (13,14) and b.order_status in (3,10,11) and date(a.date_add) = date(b.date_add) and a.date_add > '" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and a.date_add < '" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add > '" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add < '" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and a.payment_status not in (26);"

		result5 = statsengine.execute(thissql5)
		useridswhoreturnedlookup = {thisdate:set() for thisdate in daterange}
		for item in result5:
			if item[0].strftime("%Y-%m-%d") in daterange:
				useridswhoreturnedlookup[item[0].strftime("%Y-%m-%d")].add(item[1])


		useridsthatdidnotreturn = {thisdate:[] for thisdate in daterange}
		allusers = set()
		for thisdate in daterange:
			currentlist = useridswhohadpgfailurelookup[thisdate]
			for thisuser in currentlist:
				if thisuser not in useridswhoreturnedlookup[thisdate]:
					useridsthatdidnotreturn[thisdate].append(thisuser)
					allusers.add(thisuser)


		# Those who ended up ordering
		thissql6 = "select user_id, name, mobile_number, date_add from users where user_id in ("+str(allusers).strip('{}')+");"
		result6 = statsengine.execute(thissql6)
		useridswhoreturnedlookup = {thisdate:set() for thisdate in daterange}
		userlookup = {}
		for item in result6:
			userlookup.update({item[0]:item[1:]})

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>Date</th><th>User Id</th><th>User Name</th><th>User Mobile Number</th><th>Registered On</th><th>View Orders</th></thead>"
		
		for thisdate in daterange:
			currentlist = useridsthatdidnotreturn[thisdate]
			for thisuser in currentlist:
				outputtable += "<tr><td>" + str(thisdate) + "</td><td>" + str(thisuser) + "</td><td>" + str(userlookup[thisuser][0]) + "</td><td>" + str(userlookup[thisuser][1]) + "</td><td>" + str(userlookup[thisuser][2]) + "</td><td><a href='http://twigly.in/admin/orders?s=id&f="+str(userlookup[thisuser][1])+"'>View Orders</a></td></tr>"
				#http://twigly.in/admin/orders?s=id&f=9810178333

		outputtable += "</table>"

		statssession.remove()
		self.render("templates/paymentstemplate.html", daterange=daterange, userswhohadpgfailure=userswhohadpgfailure,userswhodidnotreturn=userswhodidnotreturn, userswhocancelled=userswhocancelled, outputtable=outputtable, user=current_user)


current_path = path.dirname(path.abspath(__file__))
static_path = path.join(current_path, "static")

application = tornado.web.Application([
	(r"/", LoginHandler),
	(r"/stats", StatsHandler),
	(r"/itemstats", ItemStatsHandler),
	#(r"/userstats", UserStatsHandler),
	(r"/storeitems", StoreItemsHandler),
	(r"/todaysmenu", TodayMenuHandler),
	(r"/updateActive", UpdateItemsActiveHandler),
	(r"/moveActive", MoveItemsHandler),
	(r"/updateQuantity", UpdateQuantityHandler),
	(r"/userstats", AnalyticsHandler),
	(r"/sendmail", SendMailHandler),
	(r"/getpreview", MailPreviewHandler),
	(r"/sendtomailchimp", MailchimpHandler),
	(r"/updatemailchimp", MailchimpUpdateHandler),
	(r"/sendtolazysignups", MailchimpLazySignupHandler),
	(r"/feedbacks", FeedbackHandler),
	(r"/wastage", WastageHandler),
	(r"/getstoreitems", GetStoreItemsHandler),
	(r"/setdatewisestoremenu", SetDateWiseMenuHandler),
	(r"/deliveries", DeliveryHandler),
	(r"/deliverystats", DeliveryStatsHandler),
	(r"/payments", PaymentStatsHandler),
	(r"/orderstats", OrderStatsHandler),
	(r"/customerstats", CustomerStatsHandler),
	(r"/vanvaas", VanvaasHandler),
	(r"/vanvaas/update/", UpdateVanvaasHandler),
	(r"/vanvaas/(.*)", VanvaasViewHandler),
	(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': static_path})
], **settings)

if __name__ == "__main__":
	application.listen(8080)
	print ("Listening on port 8080")
	tornado.ioloop.IOLoop.instance().start()

