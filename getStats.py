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
import sys

from fb import *

import tornado.ioloop
import tornado.web
import urllib.request

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

# import redis

settings = {
    "cookie_secret": "***REMOVED***",
    "login_url": "/"
}
statsBase = declarative_base()
statsengine_url = 'mysql+pymysql://twigly:***REMOVED***@***REMOVED***/twigly_prod?charset=utf8'
#statsengine_url = 'mysql+pymysql://root@localhost:3306/twigly_dev?charset=utf8'
mailchimpkey = "***REMOVED***"

environment_production=True #True for prod, False for dev

#relevantStates = [3,10,11,12,16]
deliveredStates = [3]
deliveredFreeStates = [10,11,12,16]
inProgress = [1,2,9,15]
returnedStates = [4]
outlet_types = [0,5]
ck_type = [1,5]

# POOL = redis.ConnectionPool(host='52.74.45.76', port=5317, db=0, password='***REMOVED***')

# # Redis keys
# redis_key_morningusers = 'mc::morning_users'
# redis_key_morningusers_cc = 'mc::morning_users::cc'
# redis_key_morningusers_46 = 'mc::morning_users::46'
# redis_key_morningusers_kkj = 'mc::morning_users::kkj'
# redis_key_eveningusers = 'mc::evening_users'
# redis_key_eveningusers_cc = 'mc::evening_users::cc'
# redis_key_eveningusers_46 = 'mc::evening_users::46'
# redis_key_eveningusers_kkj = 'mc::evening_users::kkj'

# def getRedisVariable(variable_name):
#     my_server = redis.Redis(connection_pool=POOL)
#     response = my_server.get(variable_name)
#     return response

# def setRedisVariable(variable_name, variable_value):
#     my_server = redis.Redis(connection_pool=POOL)
#     my_server.set(variable_name, variable_value)



class order(statsBase):
	__tablename__ = "orders"
	order_id = Column('order_id', Integer, primary_key=True)
	user_id = Column("user_id", Integer)
	# delivery_zone_id = Column("delivery_zone_id", Integer)
	#delivery_address = Column("delivery_address", String)
	coupon_id = Column("coupon_id", Integer)
	mobile_number = Column("mobile_number", String)
	cost = Column("cost", Float)
	service_tax = Column("service_tax", Float)
	vat = Column("vat", Float)
	sub_total = Column("sub_total", Float)
	delivery_charges = Column("delivery_charges", Float)
	wallet_amount = Column("wallet_amount", Float)
	subscription_amount = Column("subscription_amount", Float)
	coupon_discount = Column("coupon_discount", Float)
	total = Column("total", Float)
	wallet_transaction_id = Column("wallet_transaction_id", Integer)
	order_status = Column("order_status", Integer)
	payment_option = Column("payment_option", Integer)
	payment_status = Column("payment_status", Integer)
	date_add = Column("date_add", DateTime)
	date_upd = Column("date_upd", DateTime)
	source = Column("source", Integer)
	store_id = Column("store_id", Integer)
	is_for_later = Column("is_for_later", Integer)

class orderstatustimes(statsBase):
	__tablename__ = "order_status_times"
	order_status_time_id = Column('order_status_time_id', Integer, primary_key=True)
	order_id = Column('order_id', Integer,ForeignKey("orders.order_id"))
	order_status = Column("order_status", Integer)
	time_add = Column("time_add", DateTime)
	

class orderdetail(statsBase):
	__tablename__ = "order_details"
	order_detail_id = Column("order_detail_id", Integer, primary_key=True)
	order_id = Column('order_id', Integer,ForeignKey("orders.order_id"))
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
	order_detail_option_id = Column("order_detail_option_id", Integer, primary_key=True)
	order_detail_id = Column("order_detail_id", Integer, ForeignKey("order_details.order_detail_id"))
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
	email = Column("email", String)


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
	store_type = Column("store_type", Integer)
	
	

def getRedirect(username):
	if (username in ["chef", "chef03", "headchef"]):
		return "storeitems"
	elif (username in ["twiglyservice"]):
		return "dormantregulars"
	elif (username in ["@testmail.com","@testmail.com","@testmail.com","@testmail.com"]):
		return "itemstats"
	else:
		return "stats"

def authenticate(thisusername, thispassword):
	allusers={***REMOVED***}

	if thisusername in allusers:
		if allusers[thisusername] == thispassword:
			return {"result": True}

	return {"result": False}

def getFirstName(name):
	if(name==None):
		return "Customer"
	arr = name.split(' ')
	if(arr == None or len(arr)==0):
		return "Customer"
	if(arr[0]==None):
		return "Customer";
	fname = arr[0]
	if(len(fname) < 3 or fname.lower() == "swiggy"):
		return "Customer"
	if(fname[1] == '.'):
		return "Customer"
	if(fname[0] in '0123456789'):
		return "Customer"
	if(len(fname) >= 3):
	    if(fname[0:3].lower() in ("dr.", "dr ", "mr.","mr ") or fname[0:4].lower() in ("mrs.","mrs ")):
	        return "Customer"
	return fname[0:1].upper() + fname[1:].lower();


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
	dailyorderscountquery = statssession.query(order.date_add, sqlalchemy.func.count(order.order_id)).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.store_id.in_(store_list), order.is_for_later.op('&')(256)!=256).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))

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

	platformcounts = {thisdate: {"Android": 0, "Web": 0, "iOS": 0, "Zomato": 0, "Swiggy": 0, "Call":0,"FP": 0, "UberEats":0} for thisdate in daterange}
	newusercountsbysource = {thisdate: {"Android": 0, "Web": 0, "iOS": 0, "Zomato": 0, "Swiggy": 0, "Call":0,"FP": 0,"UberEats":0} for thisdate in daterange}
	
	freeordercounts = {thisdate: {"FoodTrial": 0, "FreeDelivery": 0, "Returned": 0} for thisdate in daterange}
	freeordersums = {thisdate: {"FoodTrial": 0.0, "FreeDelivery": 0.0, "Returned": 0.0} for thisdate in daterange}

	active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()
	active_stores_list = [x.store_id for x in active_stores]

	newusercountsbystore = {x.store_id: {thisdate:0 for thisdate in daterange} for x in active_stores}
	orderforlaterbystoredata = {x.store_id: {thisdate:0 for thisdate in daterange} for x in active_stores}
	deliverychargesumbystoredata = {x.store_id: {thisdate:0 for thisdate in daterange} for x in active_stores}
	newusertotalsbystore = {x.store_id: {thisdate:0.0 for thisdate in daterange} for x in active_stores}


	for thisorder in dailyordersquery:
		if thisorder.is_for_later&256!=256:
			if thisorder.order_status not in returnedStates:
				if thisorder.mobile_number in firstordersmap:
					if (thisorder.date_add.strftime("%c") == firstordersmap[thisorder.mobile_number]):
						ordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["new"] += 1
						ordertotals[thisorder.date_add.strftime("%a %b %d, %Y")]["new"] += float(thisorder.total + thisorder.subscription_amount)
						if (thisorder.store_id in active_stores_list):
							newusercountsbystore[thisorder.store_id][thisorder.date_add.strftime("%a %b %d, %Y")] += 1
							newusertotalsbystore[thisorder.store_id][thisorder.date_add.strftime("%a %b %d, %Y")] += float(thisorder.total)
						if (thisorder.source == 0):
							newusercountsbysource[thisorder.date_add.strftime("%a %b %d, %Y")]["Android"] += 1
						elif (thisorder.source == 1):
							newusercountsbysource[thisorder.date_add.strftime("%a %b %d, %Y")]["Web"] += 1
						elif (thisorder.source ==2):
							newusercountsbysource[thisorder.date_add.strftime("%a %b %d, %Y")]["iOS"] += 1
						elif (thisorder.source ==6):
							newusercountsbysource[thisorder.date_add.strftime("%a %b %d, %Y")]["Zomato"] += 1
						elif (thisorder.source ==7):
							newusercountsbysource[thisorder.date_add.strftime("%a %b %d, %Y")]["Swiggy"] += 1
						elif (thisorder.source ==8):
							newusercountsbysource[thisorder.date_add.strftime("%a %b %d, %Y")]["Call"] += 1
						elif (thisorder.source ==9):
							newusercountsbysource[thisorder.date_add.strftime("%a %b %d, %Y")]["FP"] += 1
						elif (thisorder.source ==10):
							newusercountsbysource[thisorder.date_add.strftime("%a %b %d, %Y")]["UberEats"] += 1
					else:
						ordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["old"] += 1
						ordertotals[thisorder.date_add.strftime("%a %b %d, %Y")]["old"] += float(thisorder.total + thisorder.subscription_amount)

				if thisorder.order_status == 12: #food trials
					freeordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["FoodTrial"] += 1
					# freeordersums[thisorder.date_add.strftime("%a %b %d, %Y")]["FoodTrial"] += float(thisorder.total)
				elif thisorder.order_status in [10,11]: #free on delivery
					freeordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["FreeDelivery"] += 1
					# freeordersums[thisorder.date_add.strftime("%a %b %d, %Y")]["FreeDelivery"] += float(thisorder.total)

				if thisorder.coupon_id == 58 and thisorder.order_status != 12: #coupon RKK
					freeordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["FoodTrial"] += 1
					freeordersums[thisorder.date_add.strftime("%a %b %d, %Y")]["FoodTrial"] += float(thisorder.sub_total)
				elif thisorder.coupon_id == 29 and thisorder.order_status not in [10,11]: #free on delivery and coupon matata
					freeordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["FreeDelivery"] += 1
					freeordersums[thisorder.date_add.strftime("%a %b %d, %Y")]["FreeDelivery"] += float(thisorder.sub_total)

				
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
				elif (thisorder.source ==9):
					platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["FP"] += 1
				elif (thisorder.source ==10):
					platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["UberEats"] += 1

				if (thisorder.is_for_later&0x1 == 0x1):
					orderforlaterbystoredata[thisorder.store_id][thisorder.date_add.strftime("%a %b %d, %Y")] += 1

				deliverychargesumbystoredata[thisorder.store_id][thisorder.date_add.strftime("%a %b %d, %Y")] += float(thisorder.delivery_charges)

			elif thisorder.order_status in returnedStates: #refunds
				freeordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["Returned"] += 1
				# freeordersums[thisorder.date_add.strftime("%a %b %d, %Y")]["Returned"] += float(thisorder.total)
		

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

	deliverychargesumbystore = {}
	for store_id in active_stores_list:
		templist = []
		for thisdate in daterange:
			templist.append(deliverychargesumbystoredata[store_id][thisdate])
		deliverychargesumbystore[store_id] = templist


	orderforlaterbystore = {}
	for store_id in active_stores_list:
		templist = []
		for thisdate in daterange:
			templist.append(orderforlaterbystoredata[store_id][thisdate])
		orderforlaterbystore[store_id] = templist


	androidorders = []
	weborders = []
	iosorders = []
	zomatoorders = []
	swiggyorders = []
	oncallorders = []
	fporders = []
	uberorders = []

	for thisdate in daterange:
		androidorders.append(platformcounts[thisdate]["Android"])
		weborders.append(platformcounts[thisdate]["Web"])
		iosorders.append(platformcounts[thisdate]["iOS"])
		zomatoorders.append(platformcounts[thisdate]["Zomato"])
		swiggyorders.append(platformcounts[thisdate]["Swiggy"])
		oncallorders.append(platformcounts[thisdate]["Call"])
		fporders.append(platformcounts[thisdate]["FP"])
		uberorders.append(platformcounts[thisdate]["UberEats"])

	newandroidorders = []
	newweborders = []
	newiosorders = []
	newzomatoorders = []
	newswiggyorders = []
	newoncallorders = []
	newfporders = []
	newuberorders = []

	for thisdate in daterange:
		newandroidorders.append(newusercountsbysource[thisdate]["Android"])
		newweborders.append(newusercountsbysource[thisdate]["Web"])
		newiosorders.append(newusercountsbysource[thisdate]["iOS"])
		newzomatoorders.append(newusercountsbysource[thisdate]["Zomato"])
		newswiggyorders.append(newusercountsbysource[thisdate]["Swiggy"])
		newoncallorders.append(newusercountsbysource[thisdate]["Call"])
		newfporders.append(newusercountsbysource[thisdate]["FP"])
		newuberorders.append(newusercountsbysource[thisdate]["UberEats"])

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

	result = {"neworders": neworders, "repeatorders": repeatorders, "totalneworders": totalneworders, "totalrepeatorders": totalrepeatorders, "newsums": newsums, "repeatsums": repeatsums, "androidorders": androidorders, "weborders": weborders, "iosorders": iosorders, "zomatoorders": zomatoorders, "swiggyorders": swiggyorders,"oncallorders":oncallorders,"fporders": fporders,"uberorders": uberorders, "newandroidorders": newandroidorders, "newweborders": newweborders, "newiosorders": newiosorders, "newzomatoorders": newzomatoorders, "newswiggyorders": newswiggyorders,"newoncallorders":newoncallorders,"newfporders": newfporders,"newuberorders": newuberorders, "foodtrialscount": foodtrialscount, "freedeliverycount": freedeliverycount, "returncount": returncount, "foodtrialstotal": foodtrialstotal, "freedeliverytotal": freedeliverytotal, "returntotal":returntotal, "newusersbystore":newusersbystore,"newusersumsbystore":newusersumsbystore,"orderforlaterbystore": orderforlaterbystore, "deliverychargesumbystore": deliverychargesumbystore}
	return (result)

class StatsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):

		current_user = self.get_current_user().decode()
		if current_user not in ("admin","review","headchef","teahaltge"):
			self.redirect('/')

		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 8
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
		if current_user in ("teahaltge"):
			current_store="3"

		active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()
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

		dailysalesquery = statssession.query(order.date_add, sqlalchemy.func.sum(order.total), sqlalchemy.func.sum(order.vat), sqlalchemy.func.sum(order.delivery_charges), sqlalchemy.func.sum(order.wallet_amount), sqlalchemy.func.sum(order.coupon_discount),sqlalchemy.func.sum(order.service_tax),sqlalchemy.func.sum(order.subscription_amount) ).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.order_status.in_(deliveredStates + inProgress), order.store_id.in_(store_list), order.is_for_later.op('&')(256)!=256).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))

		totalsales = []
		deliverycharges=[]
		wallettotal = []
		coupontotal = []
		subscriptiontotal = []


		thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[1]) for thisresult in dailysalesquery}
		thisdeliverydetails = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[3]) for thisresult in dailysalesquery}
		wallettransactionlookup = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[4]) for thisresult in dailysalesquery}
		couponlookup = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[5]) for thisresult in dailysalesquery}
		subscriptionsalelookup =  {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[7]) for thisresult in dailysalesquery}

		for thisdate in daterange:
			if thisdate in thiscountdetails:
				totalsales.append(thiscountdetails[thisdate])
			else:
				totalsales.append(0)

			if thisdate in thisdeliverydetails:
				deliverycharges.append(thisdeliverydetails[thisdate])
			else:
				deliverycharges.append(0)
			
			if thisdate in wallettransactionlookup:
				wallettotal.append(float(wallettransactionlookup[thisdate])) 
			else:
				wallettotal.append(0)
			
			if thisdate in couponlookup:
				coupontotal.append(float(couponlookup[thisdate])) 
			else:
				coupontotal.append(0) 

			if thisdate in subscriptionsalelookup:
				subscriptiontotal.append(float(subscriptionsalelookup[thisdate])) 
			else:
				subscriptiontotal.append(0) 

		totalsalesadj=[]
		for i in range(0, len(daterange)):
			totalsalesadj.append(totalsales[i]+subscriptiontotal[i])

		totalsales = totalsalesadj

		totalsalesvalue = sum(totalsales)

		totalcount = getTotalCount(parsedstartdate, parsedenddate, daterange, statssession,store_list)

		dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress + returnedStates), order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.store_id.in_(store_list)).all()

		detailedordercounts = getOrderCounts(parsedstartdate, parsedenddate, dailyordersquery, daterange, statssession)

		dailyorderids = [thisorder.order_id for thisorder in dailyordersquery if (thisorder.order_status not in returnedStates)]
		
		freeorderids = [thisorder.order_id for thisorder in dailyordersquery if (thisorder.order_status in [10,11])]
		foodtrialids = [thisorder.order_id for thisorder in dailyordersquery if (thisorder.order_status in [12])]
		returnedorderids = [thisorder.order_id for thisorder in dailyordersquery if (thisorder.order_status in returnedStates)]
		subscriptionorderids = [thisorder.order_id for thisorder in dailyordersquery if (thisorder.is_for_later&256==256)]

		#### Now looking at actual sales
		grosssalesquery = statssession.query(sqlalchemy.func.date(order.date_add),sqlalchemy.func.sum(orderdetail.quantity*orderdetail.price),sqlalchemy.func.sum(orderdetail.quantity*orderdetail.discount)).outerjoin(orderdetail).filter(order.order_id.in_(dailyorderids), order.order_id.notin_(subscriptionorderids)).group_by(sqlalchemy.func.date(order.date_add))
			
		grosssaleslookup = {}
		itemdisclookup = {}

		for grossdetail in grosssalesquery:
			if grossdetail[0].strftime("%a %b %d, %Y") in grosssaleslookup:
				grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] += (grossdetail[1])
			else:
			 	grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] = (grossdetail[1])

			if grossdetail[0].strftime("%a %b %d, %Y") in itemdisclookup:
				itemdisclookup[grossdetail[0].strftime("%a %b %d, %Y")] += grossdetail[2]
			else:
				itemdisclookup[grossdetail[0].strftime("%a %b %d, %Y")] = grossdetail[2]

		grosssalesodoquery = statssession.query(sqlalchemy.func.date(order.date_add),sqlalchemy.func.sum(orderdetail.quantity*orderdetailoption.price)).outerjoin(orderdetail).outerjoin(orderdetailoption).filter(order.order_id.in_(dailyorderids)).group_by(sqlalchemy.func.date(order.date_add))

		for grossdetail in grosssalesodoquery:
			if grossdetail[0].strftime("%a %b %d, %Y") in grosssaleslookup:
				grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] += (grossdetail[1])
			else:
			 	grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] = (grossdetail[1])

		vatlookup = {thisresult[0].strftime("%a %b %d, %Y"): (float(thisresult[2])+float(thisresult[6])) for thisresult in dailysalesquery}

		grosssales = []
		netsalespretax = []
		itemdiscounttotal = []

		for c in range(0, len(daterange)):
			try:
				# grosssales.append(float(grosssaleslookup[daterange[c]]))
				grosssales.append(float(grosssaleslookup[daterange[c]])+float(deliverycharges[c]))
			except KeyError:
				grosssales.append(0.0)
			try:
				netsalespretax.append(float(totalsales[c]) - float(vatlookup[daterange[c]]))
			except KeyError:
				netsalespretax.append(0.0)

			if (daterange[c] in itemdisclookup):
				itemdiscounttotal.append(float(itemdisclookup[daterange[c]])) 
			else:
				itemdiscounttotal.append(0) 

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

		if current_user in ("teahaltge"):
			statssession.remove()
			self.render("templates/statstemplate.html", daterange=daterange, totalsales=totalsales, totalcount=totalcount,totalsalesvalue=totalsalesvalue, totalorders=totalorders,grosssales = grosssales, totalgrosssales = totalgrosssales, netsalespretax = netsalespretax, totalnetsalespretax = totalnetsalespretax, user=current_user, active_stores=active_stores, current_store=current_store, current_store_name=current_store_name)
			return


		try:
			averageapc = totalgrosssales/totalorders
		except ZeroDivisionError:
			averageapc = 0

		allfreeids=freeorderids+foodtrialids+returnedorderids

		freeordersquery1 = statssession.query(order.date_add,orderdetail.quantity,orderdetail.price,orderdetailoption.price,order.order_id).join(orderdetail).outerjoin(orderdetailoption).filter(order.order_id.in_(allfreeids))

		freeorderslookup = {}
		foodtriallookup = {}
		returnedorderslookup = {}
		for itemdetail in freeordersquery1:
			if itemdetail[4] in freeorderids:
				if itemdetail[0].strftime("%a %b %d, %Y") in freeorderslookup:
					freeorderslookup[itemdetail[0].strftime("%a %b %d, %Y")] += (itemdetail[1]*itemdetail[2])	 	
				else:
				 	freeorderslookup[itemdetail[0].strftime("%a %b %d, %Y")] = (itemdetail[1]*itemdetail[2])
				if itemdetail[3]:
					freeorderslookup[itemdetail[0].strftime("%a %b %d, %Y")] += (itemdetail[1]*itemdetail[3])
			elif itemdetail[4] in foodtrialids:
				if itemdetail[0].strftime("%a %b %d, %Y") in foodtriallookup:
					foodtriallookup[itemdetail[0].strftime("%a %b %d, %Y")] += (itemdetail[1]*itemdetail[2])	 	
				else:
				 	foodtriallookup[itemdetail[0].strftime("%a %b %d, %Y")] = (itemdetail[1]*itemdetail[2])
				if itemdetail[3]:
					foodtriallookup[itemdetail[0].strftime("%a %b %d, %Y")] += (itemdetail[1]*itemdetail[3])
			elif itemdetail[4] in returnedorderids:
				if itemdetail[0].strftime("%a %b %d, %Y") in returnedorderslookup:
					returnedorderslookup[itemdetail[0].strftime("%a %b %d, %Y")] += (itemdetail[1]*itemdetail[2])	 	
				else:
				 	returnedorderslookup[itemdetail[0].strftime("%a %b %d, %Y")] = (itemdetail[1]*itemdetail[2])
				if itemdetail[3]:
					returnedorderslookup[itemdetail[0].strftime("%a %b %d, %Y")] += (itemdetail[1]*itemdetail[3])

		freegross = []
		ftgross = []
		retgross = []
		for c in range(0, len(daterange)):
			if (daterange[c] in freeorderslookup):
				freegross.append(float(freeorderslookup[daterange[c]])+float(detailedordercounts["freedeliverytotal"][c]))
			else:
				freegross.append(0.0+float(detailedordercounts["freedeliverytotal"][c]))
			
			if (daterange[c] in foodtriallookup):
				ftgross.append(float(foodtriallookup[daterange[c]])+float(detailedordercounts["foodtrialstotal"][c]))
			else:
				ftgross.append(0.0+float(detailedordercounts["foodtrialstotal"][c]))
				
			if (daterange[c] in returnedorderslookup):
				retgross.append(float(returnedorderslookup[daterange[c]]))
			else:
				retgross.append(0.0)

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

		orderlaterbystore = []
		for thisstore in active_stores:
			orderlaterbystore.append({"store_id": thisstore.store_id, "name": thisstore.name, "orderforlater":detailedordercounts["orderforlaterbystore"][thisstore.store_id]})

		deliverychargesumbystore = []
		for thisstore in active_stores:
			deliverychargesumbystore.append({"store_id": thisstore.store_id, "name": thisstore.name, "deliverychargesum":detailedordercounts["deliverychargesumbystore"][thisstore.store_id]})


		store_list_str = ",".join(map(str,store_list))

		consumptionsql_1 = "select date(so.expected_delivery), sum(sod.received_quantity*ing.cost/ing.pack_size) from ingredients ing left join store_order_details sod on ing.ingredient_id=sod.ingredient_id left join store_orders so on sod.store_order_id=so.store_order_id where so.type in (2) and so.res_store_id in ("+store_list_str+") and ing.production in (1,2,3,4,5,6,7,8,10) and so.status=3 and date(so.expected_delivery)>='" + parsedstartdate.strftime("%Y-%m-%d") + "' and date(so.expected_delivery)<='" + parsedenddate.strftime("%Y-%m-%d") + "' group by 1;"
		result1 = statsengine.execute(consumptionsql_1)
		# print (consumptionsql_1)
		consumptionlookup={}
		# print(daterange)
		for row in result1:
			# print(row)
			if row[0].strftime("%a %b %d, %Y") in daterange:
				consumptionlookup[row[0].strftime("%a %b %d, %Y")] = row[1]

		# print(consumptionlookup)
		foodcost = []
		foodcostpc = []
		for c in range(0, len(daterange)):
			try:
				foodcost.append(float(consumptionlookup[daterange[c]]))
				foodcostpc.append(float(consumptionlookup[daterange[c]])/(grosssales[c]-deliverycharges[c])*100)
			except KeyError:
				foodcost.append(0.0)
				foodcostpc.append(0.0)

		# print(foodcost)
		# print(foodcostpc)


		# diff = []
		# diff2 = []
		# for c in range(0, len(daterange)):
		# 	diff.append(grosssales[c]-netsalespretax[c]-wallettotal[c]-coupontotal[c]-itemdiscounttotal[c]-deliverycharges[c])
		# 	diff2.append(freegross[c]+ftgross[c]+retgross[c])

		# print(diff)
		# print(diff2)

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
		self.render("templates/statstemplate.html", daterange=daterange, totalsales=totalsales, totalcount=totalcount, neworders=detailedordercounts["neworders"], repeatorders=detailedordercounts["repeatorders"], newsums=detailedordercounts["newsums"], repeatsums=detailedordercounts["repeatsums"], dailyapc=dailyapc, feedback_chart_data=feedback_chart_data, food_rating_counts=food_rating_counts, delivery_rating_counts=delivery_rating_counts, totalsalesvalue=totalsalesvalue, totalorders=totalorders, totalneworders=detailedordercounts["totalneworders"], totalrepeatorders=detailedordercounts["totalrepeatorders"], averageapc=averageapc, androidorders=detailedordercounts["androidorders"], weborders=detailedordercounts["weborders"], iosorders=detailedordercounts["iosorders"], zomatoorders=detailedordercounts["zomatoorders"], swiggyorders=detailedordercounts["swiggyorders"], oncallorders=detailedordercounts["oncallorders"],fporders=detailedordercounts["fporders"],uberorders=detailedordercounts["uberorders"], newandroidorders=detailedordercounts["newandroidorders"], newweborders=detailedordercounts["newweborders"], newiosorders=detailedordercounts["newiosorders"], newzomatoorders=detailedordercounts["newzomatoorders"], newswiggyorders=detailedordercounts["newswiggyorders"], newoncallorders=detailedordercounts["newoncallorders"],newfporders=detailedordercounts["newfporders"],newuberorders=detailedordercounts["newuberorders"], foodtrialstotal=ftgross, freedeliverytotal=freegross, returntotal=retgross, foodtrialscount=detailedordercounts["foodtrialscount"], freedeliverycount=detailedordercounts["freedeliverycount"], returncount=detailedordercounts["returncount"], grosssales = grosssales, totalgrosssales = totalgrosssales, netsalespretax = netsalespretax, totalnetsalespretax = totalnetsalespretax, user=current_user, active_stores=active_stores, current_store=current_store, current_store_name=current_store_name, newusersbystore=newusersbystore, itemdiscounttotal=itemdiscounttotal,wallettotal=wallettotal,coupontotal=coupontotal,orderlaterbystore=orderlaterbystore,deliverychargesumbystore=deliverychargesumbystore,foodcost=foodcost, foodcostpc=foodcostpc)

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

			active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()
			active_stores_list = [x.store_id for x in active_stores]
			

			if current_store == "All":
				store_list = active_stores_list
			else:
				store_list = [int(current_store)]

			current_store_name = "All"
			for thisstore in active_stores:
				if (str(thisstore.store_id) == current_store):
					current_store_name = thisstore.name
					break

			orders = statssession.query(order.order_id, order.user_id, order.date_add, order.total).filter(order.date_add < parsedenddate, order.date_add >= parsedstartdate, order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.store_id.in_(store_list)).all()

			firstorderquery = statssession.query(order.user_id,order.date_add).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.store_id.in_(store_list)).order_by(order.date_add).group_by(order.user_id)


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
			#TODO

			grosssalesquery = statssession.query(order.order_id,sqlalchemy.func.sum(orderdetail.quantity*orderdetail.price),order.delivery_charges).outerjoin(orderdetail).filter(order.order_id.in_(thisstoreorders),order.is_for_later.op('&')(256)!=256).group_by(order.order_id)
				
			grosssaleslookup = {}

			for grossdetail in grosssalesquery:
				if grossdetail[0] in grosssaleslookup:
					grosssaleslookup[grossdetail[0]] += (grossdetail[1])
				else:
				 	grosssaleslookup[grossdetail[0]] = (grossdetail[1])
				grosssaleslookup[grossdetail[0]]+=grossdetail[2]

			grosssalesodoquery = statssession.query(order.order_id,sqlalchemy.func.sum(orderdetail.quantity*orderdetailoption.price)).outerjoin(orderdetail).outerjoin(orderdetailoption).filter(order.order_id.in_(thisstoreorders),order.is_for_later.op('&')(256)!=256).group_by(order.order_id)
			
			for grossdetail in grosssalesodoquery:
				if grossdetail[1]:
					if grossdetail[0] in grosssaleslookup:
						grosssaleslookup[grossdetail[0]] += (grossdetail[1])
					else:
					 	grosssaleslookup[grossdetail[0]] = (grossdetail[1])
			
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
			self.render("templates/customerstatstemplate.html", user=current_user, active_stores=active_stores, current_store=current_store, current_store_name=current_store_name,outputtable=outputtable, months=months, allcustomers=allcustomersbymonth, newcustomers=newcustomersbymonth, repeatcustomers=repeatcustomersbymonth, neworders=newordersbymonth,repeatorders=repeatordersbymonth, alltotals=alltotalsbymonth, newtotals=newtotalsbymonth,repeattotals=repeattotalsbymonth,allAPC=allAPC, newAPC=newAPC,repeatAPC=repeatAPC, outputtableorders=outputtableorders, outputtablevalues=outputtablevalues)


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

		active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()
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
		if current_user not in ["admin", "headchef", "chef", "chef03","review","@testmail.com","@testmail.com","@testmail.com","@testmail.com", "twiglyservice"]:
			self.redirect('/stats')
		else:
			horizon = self.get_argument("horizon", None)
			startdate = self.get_argument("startdate", None)
			enddate = self.get_argument("enddate", None)
			current_day = self.get_argument("d", "All")
			time_of_day = self.get_argument("t", "All")

			alldays = [{"id":0,"name":"Mon"},{"id":1,"name":"Tue"},{"id":2,"name":"Wed"},{"id":3,"name":"Thu"},{"id":4,"name":"Fri"},{"id":5,"name":"Sat"},{"id":6,"name":"Sun"}]

			include_days = []
			if current_day=="All":
				include_days = [x["id"] for x in alldays]
			else:
				include_days = [int(current_day)]

			alltime = [{"id":0,"name":"After 4pm"},{"id":1,"name":"Before 4pm"}]

			if startdate is None:
				if horizon is None:
					horizon = 7
				else:
					horizon = int(horizon)

				parsedenddate = datetime.date.today() +  datetime.timedelta(days=1)

				parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
				daterange = []#parsedstartdate.strftime("%a %b %d, %Y")]
				for c in range(horizon):
					tempdate = parsedstartdate + datetime.timedelta(days=(c))
					if tempdate.weekday() in include_days:
						daterange.append((tempdate).strftime("%a %b %d, %Y"))
			
			else:
				parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date()
				parsedenddate = parsedenddate + datetime.timedelta(days=1)
				parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
				daterange = []
				for c in range((parsedenddate - parsedstartdate).days):
					tempdate = parsedstartdate + datetime.timedelta(days=c)
					if tempdate.weekday() in include_days:
						daterange.append((tempdate).strftime("%a %b %d, %Y"))

			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))

			current_store = self.get_argument("store", "All")

			if current_user == "@testmail.com":
				current_store="2"
			elif current_user == "@testmail.com":
				current_store="3"
			elif current_user == "@testmail.com":
				current_store="5"
			elif current_user == "@testmail.com":
				current_store="12"

			active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()
			active_stores_list = [x.store_id for x in active_stores]

			if current_store == "All":
				store_list = active_stores_list
			else:
				store_list = [int(current_store)]
			
			current_store_name = "All"
			for thisstore in active_stores:
				if str(thisstore.store_id) == current_store:
					current_store_name = thisstore.name
					break

			# dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), sqlalchemy.func.weekday(order.date_add).in_(include_days), order.store_id.in_(store_list))

			dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.store_id.in_(store_list),sqlalchemy.func.weekday(order.date_add).in_(include_days))

			#, sqlalchemy.func.weekday(order.date_add).in_(include_days)

			if time_of_day=='0':
				dailyordersquery = statssession.query(order).join(orderstatustimes).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.store_id.in_(store_list),sqlalchemy.func.weekday(order.date_add).in_(include_days), orderstatustimes.order_status==1, sqlalchemy.func.time(orderstatustimes.time_add)>='16:00:00')

			elif time_of_day=='1':
				dailyordersquery = statssession.query(order).join(orderstatustimes).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.store_id.in_(store_list),sqlalchemy.func.weekday(order.date_add).in_(include_days), orderstatustimes.order_status==1, sqlalchemy.func.time(orderstatustimes.time_add)<'16:00:00')

			dailyorderids = [thisorder.order_id for thisorder in dailyordersquery]

			dailyordersdatelookup = {thisorder.order_id: thisorder.date_add.strftime("%a %b %d, %Y") for thisorder in dailyordersquery}

			cookingstations = [{'id':1,'name':'Sandwich'}, {'id':2,'name':'HotStation'},{'id':8,'name':'Dessert'},{'id':16,'name':'Pizza'},{'id':32,'name':'Grilled'}]


			csmap = []

			for thiscs in cookingstations:
				relevantmenuitems = statssession.query(menuitem.menu_item_id).filter(menuitem.cooking_station == thiscs['id'])
				thiscountquery = statssession.query(order.date_add, sqlalchemy.func.sum(orderdetail.quantity), orderdetail.order_id).outerjoin(orderdetail).filter(order.order_id.in_(dailyorderids), orderdetail.menu_item_id.in_(relevantmenuitems)).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))
				thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): int(thisresult[1]) for thisresult in thiscountquery}
				thiscslist = []
				for thisdate in daterange:
					if thisdate in thiscountdetails:
						thiscslist.append(thiscountdetails[thisdate])
					else:
						thiscslist.append(0)

				csmap.append({"name": thiscs['name'], "data":thiscslist})

			# allcsidtoname = {0:'None',1:'Sandwich', 2:'Hot Station',4:'Salad Station',8:'Dessert',16:'Pizza',32:'Grilled',64:'Soup',3:'Combo',5:'Combo',10:'Combo',11:'Combo',12:'Combo',13:'Combo',9:'Combo',34:'Combo'}
            
			allcsidtoname = {0:'None',1:'Sandwich', 2:'Hot Station',4:'Salad Station',8:'Dessert',16:'Pizza',32:'Grilled',64:'Soup'}

			allmenuitems = statssession.query(menuitem)
			for thismenuitem in allmenuitems:
				if thismenuitem.cooking_station not in allcsidtoname:
					# print('adding CS',thismenuitem.cooking_station)
					allcsidtoname[thismenuitem.cooking_station]='Combo'		

			menuitems = {thismenuitem.menu_item_id: {"name": thismenuitem.name, "cooking_station":allcsidtoname[thismenuitem.cooking_station], "total": 0, "soldout": {thisdate: [] for thisdate in daterange}, "datelookup": {thisdate: 0 for thisdate in daterange}} for thismenuitem in allmenuitems}

			for suborder in statssession.query(orderdetail).filter(orderdetail.order_id.in_(dailyorderids)):
				if (dailyordersdatelookup[suborder.order_id] in daterange):
					menuitems[suborder.menu_item_id]["datelookup"][dailyordersdatelookup[suborder.order_id]] += suborder.quantity
					menuitems[suborder.menu_item_id]["total"] += suborder.quantity


			smis_all = statssession.query(storemenuitem).filter(storemenuitem.store_id.in_(store_list), storemenuitem.menu_item_id.in_(menuitems.keys())).all()

			smi_lookup = {x.store_menu_item_id:{"menu_item_id":x.menu_item_id, "store_id":x.store_id} for x in smis_all}

			dwactivestates = [1,3,5,7,9]
			soldout_items = statssession.query(datewise_store_menu_item).filter(datewise_store_menu_item.is_active.in_(dwactivestates),datewise_store_menu_item.eod_quantity==0,datewise_store_menu_item.avl_quantity>0,datewise_store_menu_item.date_effective < parsedenddate, datewise_store_menu_item.date_effective >= parsedstartdate, sqlalchemy.func.weekday(datewise_store_menu_item.date_effective).in_(include_days), datewise_store_menu_item.store_menu_item_id.in_(smi_lookup.keys())).all()
			
			for item in soldout_items:
				menu_item_id = smi_lookup[item.store_menu_item_id]["menu_item_id"]
				store_id = smi_lookup[item.store_menu_item_id]["store_id"] 
				date_effective = item.date_effective
				menuitems[menu_item_id]["soldout"][date_effective.strftime("%a %b %d, %Y")].append(store_id)
				
			active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()

			today = datetime.date.today().strftime("%a %b %d, %Y")

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
						if len(menuitems[thismenuitem]["soldout"][thisdate])>0 and thisdate!=today:
							itemhtml += "<td style='color:red;' title='"+str(menuitems[thismenuitem]["soldout"][thisdate])+"'>"
						else:
							itemhtml += "<td>"
						itemhtml += str(menuitems[thismenuitem]["datelookup"][thisdate]) + "</td>"
				itemhtml += "</tr>"
			itemhtml += "</tbody></table>"

			statssession.remove()
			self.render("templates/itemstatstemplate.html", daterange=daterange, csmap=csmap, itemhtml=itemhtml, active_stores=active_stores, current_store=current_store, current_store_name=current_store_name, user=current_user, current_day=current_day, alldays=alldays, time_of_day=time_of_day, alltime=alltime)

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
	
	active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()

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

class DiscountAnalysisHandler(BaseHandler):
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

			current_store = self.get_argument("store", "All")

			active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()
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

			dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress + returnedStates), order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.store_id.in_(store_list),order.is_for_later.op('&')(256)!=256).all()

			dailyorderids = [thisorder.order_id for thisorder in dailyordersquery if (thisorder.order_status not in returnedStates)]

			grosssalesquery = statssession.query(sqlalchemy.func.date(order.date_add),sqlalchemy.func.sum(orderdetail.quantity*orderdetail.price)).outerjoin(orderdetail).filter(order.order_id.in_(dailyorderids)).group_by(sqlalchemy.func.date(order.date_add))
				
			grosssaleslookup = {}

			for grossdetail in grosssalesquery:
				if grossdetail[0].strftime("%a %b %d, %Y") in grosssaleslookup:
					grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] += (grossdetail[1])
				else:
				 	grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] = (grossdetail[1])

			grosssalesodoquery = statssession.query(sqlalchemy.func.date(order.date_add),sqlalchemy.func.sum(orderdetail.quantity*orderdetailoption.price)).outerjoin(orderdetail).outerjoin(orderdetailoption).filter(order.order_id.in_(dailyorderids)).group_by(sqlalchemy.func.date(order.date_add))
			
			for grossdetail in grosssalesodoquery:
				if grossdetail[0].strftime("%a %b %d, %Y") in grosssaleslookup:
					grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] += (grossdetail[1])
				else:
				 	grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] = (grossdetail[1])				

			totalsales = []

			dailysalesquery = statssession.query(order.date_add, sqlalchemy.func.sum(order.wallet_amount), sqlalchemy.func.sum(order.coupon_discount), sqlalchemy.func.sum(order.delivery_charges)).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.order_status.in_(deliveredStates + inProgress), order.store_id.in_(store_list)).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))

			wallettotal = []
			coupontotal = []
			deliverycharges = []

			wallettransactionlookup = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[1]) for thisresult in dailysalesquery}
			couponlookup = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[2]) for thisresult in dailysalesquery}
			thisdeliverydetails = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[3]) for thisresult in dailysalesquery}

			for thisdate in daterange:
				if thisdate in wallettransactionlookup:
					wallettotal.append(float(wallettransactionlookup[thisdate])) 
				else:
					wallettotal.append(0)
				
				if thisdate in couponlookup:
					coupontotal.append(float(couponlookup[thisdate])) 
				else:
					coupontotal.append(0)

				if thisdate in thisdeliverydetails:
					deliverycharges.append(thisdeliverydetails[thisdate])
				else:
					deliverycharges.append(0) 

			for c in range(0, len(daterange)):
				try:
					# grosssales.append(float(grosssaleslookup[daterange[c]]))
					totalsales.append(float(grosssaleslookup[daterange[c]])+float(deliverycharges[c]))
				except KeyError:
					totalsales.append(0.0)

			resulthtml = "<table style='border-collapse: separate; border-spacing: 4px;'><thead><tr><th>&nbsp;</th>"
			for thisdate in daterange:
				resulthtml += ("<th>" + thisdate + "</th>")
			resulthtml += "</tr></thead><tbody>"

			resulthtml += "<tr><td style='font-weight: bold; text-align: left;'>Gross Sales<br>" + str(round(sum(totalsales),2)) + "</td>"
			for x in totalsales:
				resulthtml += ("<td style='text-align: right;'>" + str(x) + "</td>")
			resulthtml += "</tr>"


			itemdiscountsql = "select date(date_add), sum(quantity*discount) from order_details where discount > 0 and order_id in (select order_id from orders where order_status in (3,10,11,12,16) and date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and is_for_later&256!=256) group by 1;"
			itemdiscountresult = statsengine.execute(itemdiscountsql)
			itemdiscountlookup = {fd[0].strftime("%a %b %d, %Y"): fd[1] for fd in itemdiscountresult}
			itemdiscountlist = []
			for thisdate in daterange:
				if thisdate in itemdiscountlookup:
					itemdiscountlist.append(float(itemdiscountlookup[thisdate]))
				else:
					itemdiscountlist.append(0)

			totaldiscounts = []
			for index, x in enumerate(itemdiscountlist):
				totaldiscounts.append(x + wallettotal[index] + coupontotal[index])
			resulthtml += "<tr><td style='font-weight: bold; text-align: left;'>Total Discounts<br>" + str(round(sum(totaldiscounts),2)) + "<br>" + str(round(sum(totaldiscounts)*100/sum(totalsales),2)) + "%</td>"
			for index, x  in enumerate(totaldiscounts):
				try:
					resulthtml += ("<td style='text-align: right;'>" + str(round(x,2)) + "<br>" + str(round(x/totalsales[index]*100,2))+ "%</td>")
				except ZeroDivisionError:
					resulthtml += "<td style='text-align: right;'>-</td>"
			resulthtml += "</tr>"


			resulthtml += "<tr style='border-top: 1px solid #000;'><td style='font-weight: bold; text-align: left;'>Item Discounts<br>" + str(round(sum(itemdiscountlist),2)) + "<br>" + str(round(sum(itemdiscountlist)*100/sum(totalsales),2)) + "%</td>"
			for index, x  in enumerate(itemdiscountlist):
				try:
					resulthtml += ("<td style='text-align: right;'>" + str(round(x,2)) + "<br>" + str(round(x/totaldiscounts[index]*100,2))+ "%</td>")
				except ZeroDivisionError:
					resulthtml += "<td  style='text-align: right;'>-</td>"
			resulthtml += "</tr>"

			freedessertssql = "select date(date_add), sum(a.quantity*a.discount) from order_details as a join menu_items as b on a.menu_item_id = b.menu_item_id where a.price-a.discount = 0 and a.order_id in (select order_id from orders where order_status = 3 and date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59') and b.cooking_station =8 group by 1;"
			freedessertresult = statsengine.execute(freedessertssql)
			freedessertlookup = {fd[0].strftime("%a %b %d, %Y"): fd[1] for fd in freedessertresult}
			freedessertlist = []
			for thisdate in daterange:
				if thisdate in freedessertlookup:
					freedessertlist.append(float(freedessertlookup[thisdate]))
				else:
					freedessertlist.append(0)

			resulthtml += "<tr style='background: #ccc; text-align: right;'><td>Free Desserts<br>" + str(round(sum(freedessertlist),2)) + "<br>" + str(round(sum(freedessertlist)*100/sum(itemdiscountlist),2)) + "%</td>"
			for index, x  in enumerate(freedessertlist):
				try:
					resulthtml += ("<td>" + str(round(x,2)) + "<br>" + str(round(x/itemdiscountlist[index]*100,2))+ "%</td>")
				except ZeroDivisionError:
					resulthtml += "<td>-</td>"
			resulthtml += "</tr>"

			sotdsql = "select date(date_add), sum(a.quantity*a.discount) from order_details as a join menu_items as b on a.menu_item_id = b.menu_item_id where ((a.price-a.discount = 140) or (a.price-a.discount = 160)) and a.order_id in (select order_id from orders where order_status = 3 and date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59') and b.cooking_station = 1 group by 1;"
			sotdresult = statsengine.execute(sotdsql)
			sotdlookup = {fd[0].strftime("%a %b %d, %Y"): fd[1] for fd in sotdresult}
			sotdlist = []
			for thisdate in daterange:
				if thisdate in sotdlookup:
					sotdlist.append(float(sotdlookup[thisdate]))
				else:
					sotdlist.append(0)

			resulthtml += "<tr style='background: #ccc; text-align: right;'><td>Sandwich of the Day<br>" + str(round(sum(sotdlist),2)) + "<br>" + str(round(sum(sotdlist)*100/sum(itemdiscountlist),2)) + "%</td>"
			for index, x  in enumerate(sotdlist):
				try:
					resulthtml += ("<td>" + str(round(x,2)) + "<br>" + str(round(x/itemdiscountlist[index]*100,2))+ "%</td>")
				except ZeroDivisionError:
					resulthtml += "<td>-</td>"
			resulthtml += "</tr>"

			potdsql = "select date(date_add), sum(a.quantity*a.discount) from order_details as a join menu_items as b on a.menu_item_id = b.menu_item_id where (a.discount = 50 or a.discount = 100) and a.order_id in (select order_id from orders where order_status = 3 and date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59') and b.cooking_station = 16 group by 1;"
			potdresult = statsengine.execute(potdsql)
			potdlookup = {fd[0].strftime("%a %b %d, %Y"): fd[1] for fd in potdresult}
			potdlist = []
			for thisdate in daterange:
				if thisdate in potdlookup:
					potdlist.append(float(potdlookup[thisdate]))
				else:
					potdlist.append(0)

			resulthtml += "<tr style='background: #ccc; text-align: right;'><td>Pizza of the Day<br>" + str(round(sum(potdlist),2)) + "<br>" + str(round(sum(potdlist)*100/sum(itemdiscountlist),2)) + "%</td>"
			for index, x  in enumerate(potdlist):
				try:
					resulthtml += ("<td>" + str(round(x,2)) + "<br>" + str(round(x/itemdiscountlist[index]*100,2))+ "%</td>")
				except ZeroDivisionError:
					resulthtml += "<td>-</td>"
			resulthtml += "</tr>"

			freepizzasql = "select date(date_add), sum(a.quantity*a.discount) from order_details as a join menu_items as b on a.menu_item_id = b.menu_item_id where a.price-a.discount = 0 and a.order_id in (select order_id from orders where order_status = 3 and date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59') and b.cooking_station =16 group by 1;"
			freepizzaresult = statsengine.execute(freepizzasql)
			freepizzalookup = {fd[0].strftime("%a %b %d, %Y"): fd[1] for fd in freepizzaresult}
			freepizzalist = []
			for thisdate in daterange:
				if thisdate in freepizzalookup:
					freepizzalist.append(float(freepizzalookup[thisdate]))
				else:
					freepizzalist.append(0)

			resulthtml += "<tr style='background: #ccc; text-align: right;'><td>Free Pizza<br>" + str(round(sum(freepizzalist),2)) + "<br>" + str(round(sum(freepizzalist)*100/sum(itemdiscountlist),2)) + "%</td>"
			for index, x  in enumerate(freepizzalist):
				try:
					resulthtml += ("<td>" + str(round(x,2)) + "<br>" + str(round(x/itemdiscountlist[index]*100,2))+ "%</td>")
				except ZeroDivisionError:
					resulthtml += "<td>-</td>"
			resulthtml += "</tr>"

			resulthtml += "<tr style='border-top: 1px solid #000;'><td style='font-weight: bold; text-align: left;'>Wallet Usage<br>" + str(round(sum(wallettotal),2)) + "<br>" + str(round(sum(wallettotal)*100/sum(totalsales),2)) + "%</td>"
			for index, x  in enumerate(wallettotal):
				try:
					resulthtml += ("<td style='text-align: right;'>" + str(round(x,2)) + "<br>" + str(round(x/totaldiscounts[index]*100,2))+ "%</td>")
				except ZeroDivisionError:
					resulthtml += "<td style='text-align: right;'>-</td>"
			resulthtml += "</tr>"

			firstordersql = "select date(date_add), sum(wallet_amount) from orders where wallet_amount=50 and order_id in (select order_id from orders where order_status in (3) and date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and source in (0,1,2,7) and user_id not in (select user_id from orders where order_status in (3,10,11,12,16) and source in (0,1,2,7) and date_add < '" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00')) group by 1;"
			firstorderresult = statsengine.execute(firstordersql)
			firstorderlookup = {fd[0].strftime("%a %b %d, %Y"): fd[1] for fd in firstorderresult}
			firstorderlist = []
			for thisdate in daterange:
				if thisdate in firstorderlookup:
					firstorderlist.append(float(firstorderlookup[thisdate]))
				else:
					firstorderlist.append(0)

			resulthtml += "<tr style='background: #ccc; text-align: right;'><td>First Order Discount<br>" + str(round(sum(firstorderlist),2)) + "<br>" + str(round(sum(firstorderlist)*100/sum(wallettotal),2)) + "%</td>"
			for index, x  in enumerate(firstorderlist):
				try:
					resulthtml += ("<td>" + str(round(x,2)) + "<br>" + str(round(x/wallettotal[index]*100,2))+ "%</td>")
				except ZeroDivisionError:
					resulthtml += "<td>-</td>"
			resulthtml += "</tr>"

			resulthtml += "<tr style='border-top: 1px solid #000;'><td style='font-weight: bold;'>Coupons Usage<br>" + str(round(sum(coupontotal),2)) + "<br>" + str(round(sum(coupontotal)*100/sum(totalsales),2)) + "%</td>"
			for index, x  in enumerate(coupontotal):
				try:
					resulthtml += ("<td style='text-align: right;'>" + str(round(x,2)) + "<br>" + str(round(x/totaldiscounts[index]*100,2))+ "%</td>")
				except ZeroDivisionError:
					resulthtml += "<td style='text-align: right;'>-</td>"
			resulthtml += "</tr>"

			couponsql = "select date(o.date_add), c.coupon_code, sum(o.coupon_discount) from orders o left join coupons c on o.coupon_id=c.coupon_id where o.coupon_id is not null and o.order_status = 3 and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2 order by 3 desc;"
			couponresult = statsengine.execute(couponsql)

			couponlookup = {}
			coupontotallookup = {}

			for fd in couponresult:
				if fd[0].strftime("%a %b %d, %Y") in couponlookup:
					if fd[1] in couponlookup[fd[0].strftime("%a %b %d, %Y")]:
						couponlookup[fd[0].strftime("%a %b %d, %Y")][fd[1]] += fd[2]
					else:
						couponlookup[fd[0].strftime("%a %b %d, %Y")][fd[1]] = fd[2]
				else:
					couponlookup[fd[0].strftime("%a %b %d, %Y")] = {}
					couponlookup[fd[0].strftime("%a %b %d, %Y")][fd[1]] = fd[2]

				if fd[1] in coupontotallookup:
					coupontotallookup[fd[1]] += fd[2]
				else:
					coupontotallookup[fd[1]] = fd[2]

			sortedcoupons = sorted(coupontotallookup.items(), key=lambda x: -x[1])
			selectedcoupons = sortedcoupons[:10]
			selectedcoupons = [x[0] for x in selectedcoupons]

			for c in selectedcoupons:
				resulthtml += "<tr style='background: #ccc; text-align: right;'><td>" + c + "</td>"
				for index, thisdate in enumerate(daterange):
					if thisdate in couponlookup:
						if c in couponlookup[thisdate]:
							try:
								resulthtml += ("<td>" + str(round(couponlookup[thisdate][c])) + "<br>" + str(round(float(couponlookup[thisdate][c])/coupontotal[index]*100, 2)) + "%</td>")
							except ZeroDivisionError:
								resulthtml += "<td>-</td>"
						else:
							resulthtml += ("<td>0<br>0%</td>")
					else:
						resulthtml += ("<td>0<br>0%</td>")
				resulthtml += "</tr>"

			resulthtml += "</tbody></table>"
			statssession.remove()

			self.render("templates/simpletabletemplate.html", page_url="/discountanalysis", page_title="Discounts Analysis",table_title="",tableSort="", daterange=daterange, outputtable=resulthtml, user=current_user)

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

			active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()
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
	elif (template == 8):
		return ("templates/mailtemplate5.html", "")
	elif (template == 9):
		return ("templates/mailtemplate6.html", "")
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
			image = self.get_argument("image", "none")
			mailtemplate = getMailTemplate(template)
			self.render(template_name = mailtemplate[0], activeitems = finallist, header = header, length = length, sod=sod, dod=dod, color=mailtemplate[1], image=image)

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
			image = self.get_argument("image", "none")
			mailtemplate = getMailTemplate(template)
			
			content = self.render_string(template_name = mailtemplate[0], activeitems = finallist, header = header, length = length, sod=sod, dod=dod, color=mailtemplate[1], image=image).decode("utf-8") 

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


def sendTwiglyMail(fromaddr, toaddr, subject, body, mailtype):
	msg = MIMEMultipart()
	msg['From'] = fromaddr
	msg['To'] = toaddr
	msg['Subject'] = subject
	msg.attach(MIMEText(body, mailtype))
	host = 'email-smtp.us-east-1.amazonaws.com'
	port = 587
	user = "***REMOVED***"
	password = "***REMOVED***"
	server = smtplib.SMTP(host, port)
	server.starttls()
	server.login(user, password)
	server.sendmail(fromaddr, toaddr, msg.as_string())
	server.quit()


def sendTwiglyMailwBCC(fromaddr, toaddr, subject, body, mailtype):
	# bcc=['***REMOVED***']
	bcc=['***REMOVED***','***REMOVED***','***REMOVED***']
	toaddrs = [toaddr]+bcc
	msg = MIMEMultipart()
	msg['From'] = fromaddr
	msg['To'] = toaddr
	msg['Subject'] = subject
	msg.attach(MIMEText(body, mailtype))
	host = 'email-smtp.us-east-1.amazonaws.com'
	port = 587
	user = "***REMOVED***"
	password = "***REMOVED***"
	server = smtplib.SMTP(host, port)
	server.starttls()
	server.login(user, password)
	server.sendmail(fromaddr, toaddrs, msg.as_string())
	server.quit()


def sendTwiglySMS(number, message):
	url="http://enterprise.smsgupshup.com/GatewayAPI/rest?msg="+message+"&send_to="+number+"&password=***REMOVED***&method=SendMessage&v1.1&format=TEXT&msg_type=TEXT&auth_scheme=plain&userid=***REMOVED***&mask=TWIGLY"
	print(url)
	try:
		response = urllib.request.urlopen(url).read()
		print(response)
	except Exception as e:	
		print ("Unexpected error:",e)



def getMailChimpListId():
	if environment_production:#Change this variable to change the list
		# ea0d1e3356 is the main Twigly list
		list_id = "ea0d1e3356"
	else:
		# d2a7019f47 is the test list
		list_id = "d2a7019f47"
	return list_id


class MailchimpUpdateHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			self.expireWalletForLastOrderOn(datetime.date.today()-datetime.timedelta(days=90))
			self.expireRewardsForLastOrderOn(datetime.date.today()-datetime.timedelta(days=120))

			startdate = self.get_argument("startdate", None)
			if startdate is None:
				parsedstartdate = datetime.date.today()
			else:
				parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
			batch_list = self.getUpdateBatch(parsedstartdate)
			list_id = getMailChimpListId()

			mailerror = False
			try:
				m = Mailchimp(mailchimpkey)
				mailchimpresponse = m.lists.batch_subscribe(list_id, batch_list, double_optin=False)
			except Exception as e:
				print ("Unexpected error:",e)
			if (mailchimpresponse['error_count']>0):
				self.write({"result": False})
				sendTwiglyMail('@testmail.com','***REMOVED***',str(mailchimpresponse['error_count'])+" error(s) in mailchimp List for "+parsedstartdate.strftime("%Y-%m-%d"), str(mailchimpresponse),'plain')
			else:
				self.write({"result": True})

	def expireWalletForLastOrderOn(self, lastorderdate):
		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))
		thissql1 = "select distinct u.mobile_number, u.name, u.wallet_money, u.user_id from users u left join orders o on o.user_id=u.user_id where u.wallet_money>0 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.order_status in (3,10,11,12,16) and o.date_add>='" + lastorderdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + lastorderdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + lastorderdate.strftime("%Y-%m-%d") + " 23:59:59');"
		result1 = statsengine.execute(thissql1)
		userids = []
		mobiles = []
		for item in result1:
			userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1])), "wallet":str(item[2]),"id":str(item[3])})
			mobiles.append(str(item[0]).lower())

		thissql2 = "insert into wallet_transactions (type,amount,user_id,category,related_id,description) values"
		thissql3 = "update users set wallet_money=0 where user_id in ("
		separator = " "
		separator3 = " "
		updatewallets = 0
		for item in userids:
			w = float(item['wallet']) 
			if w<=0:
				w=0
			else:
				thissql2 += separator+ "('0'"+","+str(int(w))+","+item['id']+",13,0,'wallet clearance cron')"
				separator=", " 
				thissql3 += separator3+ item['id']
				separator3=", "
				updatewallets=1 
		thissql2+=";"
		thissql3+=");"
		if(updatewallets==1):
			result2 = statsengine.execute(thissql2)
			statssession.commit()
			result3 = statsengine.execute(thissql3)
			statssession.commit()
		statssession.remove()
		sendTwiglyMail('Wallet Clearance Cron <@testmail.com>','Raghav <***REMOVED***>',"Wallet cleared for "+str(len(userids))+" users with last order on "+lastorderdate.strftime("%Y-%m-%d"), "Wallet cleared for '"+"','".join(mobiles)+"'", 'plain')

	def expireRewardsForLastOrderOn(self, lastorderdate):
		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))
		thissql1 = "select distinct u.mobile_number, u.name, u.reward_points, u.user_id from users u left join orders o on o.user_id=u.user_id where u.reward_points>0 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.order_status in (3,10,11,12,16) and o.date_add>='" + lastorderdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + lastorderdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + lastorderdate.strftime("%Y-%m-%d") + " 23:59:59');"
		result1 = statsengine.execute(thissql1)
		userids = []
		mobiles = []
		for item in result1:
			userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1])), "points":str(item[2]),"id":str(item[3])})
			mobiles.append(str(item[0]).lower())
		thissql2 = "insert into reward_transactions (type,points,user_id,reward_type,related_id,reward_id,description) values"
		thissql3 = "update users set reward_points=0 where user_id in ("
		separator = " "
		separator3 = " "
		updaterewards = 0
		for item in userids:
			w = float(item['points']) 
			if w<=0:
				w=0
			else:
				thissql2 += separator+ "('0'"+","+str(int(w))+","+item['id']+",1,0,1,'reward clearance cron')"
				separator=", " 
				thissql3 += separator3+ item['id']
				separator3=", "
				updaterewards=1 
		thissql2+=";"
		thissql3+=");"
		if(updaterewards==1):
			result2 = statsengine.execute(thissql2)
			statssession.commit()
			result3 = statsengine.execute(thissql3)
			statssession.commit()
		statssession.remove()
		sendTwiglyMail('Reward Clearance Cron <@testmail.com>','Raghav <***REMOVED***>',"Rewards cleared for "+str(len(userids))+" users with last order on "+lastorderdate.strftime("%Y-%m-%d"), "Rewards cleared for '"+"','".join(mobiles)+"'", 'plain')


	def getUpdateBatch(self,parsedstartdate):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select email, name from users where email is not null and date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00';" 
			result1 = statsengine.execute(thissql1)
			userids = []
			for item in result1:
				userids.append({"email":str(item[0]).lower(), "name":str(item[1]).title()})
			statssession.remove()
			batch_list = []
			for item in userids:
				batch_list.append({'email':{'email':item['email']}, 'email_type':'html', 'merge_vars':{'FNAME':item['name']}})
			return batch_list
		else:
			batch_list = []
			batch_list.append({'email':{'email':'***REMOVED***'}, 'email_type':'html', 'merge_vars':{'FNAME':'Raghav'}})
			return batch_list



class MailchimpLazySignupHandler(BaseHandler):

	def getLazySignupBatch(self,parsedstartdate):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select u.email from users u where u.email is not null and u.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and u.date_add<='" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select o.user_id from orders o where order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00');" 
			result1 = statsengine.execute(thissql1)
			userids = []
			for item in result1:
				userids.append({"email":str(item[0]).lower()})
			statssession.remove()
			batch_list = []
			for item in userids:
				batch_list.append({'email':item['email']})
			return batch_list
		else:
			batch_list = []
			batch_list.append({'email':'***REMOVED***'})
			return batch_list


	def getLazySignupTemplateId(self):
		lazy_template_id = 139741 # int
		return lazy_template_id

	def getLazySignupSegmentId(self):
		if environment_production:
			lazy_static_segment_id = 60477
		else:
			lazy_static_segment_id = 60389
		return lazy_static_segment_id


	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			parsedstartdate = datetime.date.today() - datetime.timedelta(days=2)
			batch_list = self.getLazySignupBatch(parsedstartdate)
			list_id = getMailChimpListId()
			lazy_template_id = self.getLazySignupTemplateId()
			lazy_static_segment_id = self.getLazySignupSegmentId()
			mre2 = {}
			try:
				m = Mailchimp(mailchimpkey)
				#Create a segment for lazy signups
				# mcresponse = m.lists.static_segment_add(list_id,"Lazy Signups (New)")
				# print(mcresponse)
				mcresponse = m.lists.static_segment_reset(list_id,lazy_static_segment_id)
				mcresponse = m.lists.static_segment_members_add(list_id,lazy_static_segment_id,batch_list)
				subject = "Great food is just 3 clicks away"
				mcresponse = m.campaigns.create(type="regular", options={"list_id": list_id, "subject": subject, "from_email": "@testmail.com", "from_name": "Twigly", "to_name": "*|FNAME|*", "title": subject, "authenticate": True, "generate_text": True, "template_id":lazy_template_id}, content={"sections": {}}, segment_opts={"saved_segment_id":lazy_static_segment_id})
				mre2 = m.campaigns.send(mcresponse["id"])

			except Exception as e:
				print ("Unexpected error:",e)

			if ('complete' in mre2 and mre2['complete']==True):
				self.write({"result": True})
				sendTwiglyMail('@testmail.com','***REMOVED***',str(len(batch_list))+" recepients of Lazy campaign for "+parsedstartdate.strftime("%Y-%m-%d"), "Email sent successfully to " + str(batch_list),'plain')
			else:
				self.write({"result": False})
				sendTwiglyMail('@testmail.com','***REMOVED***',"Some error in the Lazy campaign for "+parsedstartdate.strftime("%Y-%m-%d"), str(mre2),'plain')

class MailchimpDormantUserHandler(BaseHandler):
	def getDormantUsersBatch(self,parsedstartdate):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select u.email from users u left join orders o on o.user_id=u.user_id where u.email is not null and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59');"
			result1 = statsengine.execute(thissql1)
			userids = []
			for item in result1:
				userids.append({"email":str(item[0]).lower()})
			statssession.remove()
			batch_list = []
			for item in userids:
				batch_list.append({'email':item['email']})
			return batch_list
		else:
			batch_list = []
			batch_list.append({'email':'***REMOVED***'})
			return batch_list

	def sendBadDeliveryFeedbackMail(self,parsedstartdate):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select u.email, u.name, o.order_id from users u left join orders o on o.user_id=u.user_id left join feedbacks f on o.order_id = f.order_id left join delivery_zones dz on dz.delivery_zone_id=o.delivery_zone_id  where u.email is not null and o.order_status in (3,10,11,12,16) and o.source in (0,1,2,8) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59') and (f.delivery_rating<4 and f.delivery_rating<f.food_rating) and dz.falls_under_gurantee=0 and u.email not like '%%zomatouseremail.com%%';"

			result1 = statsengine.execute(thissql1)
			userids = []
			orderids = []
			emailids = []
			for item in result1:
				userids.append({"email":str(item[0]).lower(), "name":getFirstName(str(item[1])), "orderid":str(item[2])})
				orderids.append(str(item[2]))
				if len(item[0])>0:
					emailids.append(str(item[0]))

			if len(orderids) > 0:
				thissql2 = "select distinct o.order_id, mi.name from orders o left join order_details od on o.order_id = od.order_id left join menu_items mi on od.menu_item_id = mi.menu_item_id where o.order_id in  ("+",".join(orderids)+");"
				result2 = statsengine.execute(thissql2)

				order_details = {}
				for item in result2:
					thisorderid = str(item[0])
					if (thisorderid in order_details):
						order_details[thisorderid] = order_details[thisorderid] + ", " + str(item[1]).strip() 
					else:
						order_details[thisorderid] = str(item[1]).strip()

				thissql3 = "select o.order_id, time_to_sec(timediff(b.time_add,a.time_add)) from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id=b.order_id where a.order_status=1 and b.order_status=3 and o.order_id in ("+",".join(orderids)+");"
				result3 = statsengine.execute(thissql3)

				order_time = {}
				for item in result3:
					order_time[str(item[0])] = int(int(item[1]/60/5)*5)

				thissql4 = "update users set free_dessert_counter=1 where email in ('"+"','".join(emailids)+"');"
				result4 = statsengine.execute(thissql4)

				statssession.remove()
				for item in userids:
					thisorder = item['orderid']
					content = self.render_string(template_name = "templates/baddeliverytemplate.html", username=item['name'], order_items=order_details[thisorder], order_time=order_time[thisorder])
					content = content.decode("utf-8").strip('\n')

					sendTwiglyMailwBCC('Twigly <@testmail.com>',item['name']+' <'+item['email']+'>',"We apologize if something wasn't right with your last order", str(content), 'html')

			sendTwiglyMail('Bad Delivery <@testmail.com>','Raghav <***REMOVED***>',str(len(emailids))+" emails sent for Bad Delivery on "+parsedstartdate.strftime("%Y-%m-%d"), "Emails sent to '"+"','".join(emailids)+"'", 'plain')

			batch_list = []
			for item in userids:
				batch_list.append({'email':item['email']})
			return batch_list
		else:
			batch_list = []
			batch_list.append({'email':'***REMOVED***'})
			return batch_list

	def sendBadFoodFeedbackMail(self,parsedstartdate):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select u.email, u.name, o.order_id from users u left join orders o on o.user_id=u.user_id left join feedbacks f on o.order_id = f.order_id where u.email is not null and o.order_status in (3,10,11,12,16) and o.source in (0,1,2,8) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59') and (f.food_rating<4 and f.delivery_rating>=f.food_rating and char_length(f.comment)=0) and u.email not like '%%zomatouseremail.com%%';"
			result1 = statsengine.execute(thissql1)
			userids = []
			orderids = []
			emailids = []
			for item in result1:
				userids.append({"email":str(item[0]).lower(), "name":getFirstName(str(item[1])), "orderid":str(item[2])})
				orderids.append(str(item[2]))
				if len(item[0])>0:
					emailids.append(str(item[0]))

			if len(orderids) > 0:
				thissql2 = "select distinct o.order_id, mi.name from orders o left join order_details od on o.order_id = od.order_id left join menu_items mi on od.menu_item_id = mi.menu_item_id where o.order_id in  ("+",".join(orderids)+");"
				result2 = statsengine.execute(thissql2)

				order_details = {}
				for item in result2:
					thisorderid = str(item[0])
					if (thisorderid in order_details):
						order_details[thisorderid] = order_details[thisorderid] + ", " + str(item[1]).strip() 
					else:
						order_details[thisorderid] = str(item[1]).strip()

				thissql4 = "update users set free_dessert_counter=1 where email in ('"+"','".join(emailids)+"');"
				result4 = statsengine.execute(thissql4)

				statssession.remove()
				for item in userids:
					thisorder = item['orderid']
					content = self.render_string(template_name = "templates/badfoodtemplate.html", username=item['name'], order_items=order_details[thisorder])
					content = content.decode("utf-8").strip('\n')

					sendTwiglyMailwBCC('Twigly <@testmail.com>',item['name']+' <'+item['email']+'>',"We apologize if something wasn't right with your last order", str(content), 'html')

			sendTwiglyMail('Bad Food <@testmail.com>','Raghav <***REMOVED***>',str(len(emailids))+" emails sent for Bad Food on "+parsedstartdate.strftime("%Y-%m-%d"), "Emails sent to '"+"','".join(emailids)+"'", 'plain')

			batch_list = []
			for item in userids:
				batch_list.append({'email':item['email']})
			return batch_list
		else:
			batch_list = []
			batch_list.append({'email':'***REMOVED***'})
			return batch_list

	def sendZomatoDormantUserSMS(self,parsedstartdate):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select u.mobile_number, u.name from users u left join orders o on o.user_id=u.user_id where u.verified&2=0 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.source=6 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59');"
			result1 = statsengine.execute(thissql1)
			userids = []
			mobiles = []
			for item in result1:
				userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1]))})
				mobiles.append(str(item[0]).lower())

			statssession.remove()
			if len(userids) > 0:
				for item in userids:
					msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20hope%20you%20liked%20your%20last%20order%20with%20Twigly.%20For%20better%20experience%2C%20recently%20launched%20dishes%20and%20Rs%2050%20off%20on%20your%20first%20order%20try%20our%20Twigly%20app%20%28https%3A%2F%2Fgoo.gl%2FY4jnAt%29."
					number = item['mobile']
					sendTwiglySMS(number,msg)


			sendTwiglyMail('Dormant Zomato Only <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for Dormant Zomato on "+parsedstartdate.strftime("%Y-%m-%d"), "SMS sent to '"+"','".join(mobiles)+"'", 'plain')

	def sendZomatoDormantUserSMSV2(self,parsedstartdate):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select distinct u.mobile_number, u.name, u.wallet_money, u.user_id from users u left join orders o on o.user_id=u.user_id where u.verified&2=0 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.source in (6,9,10) and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59');"
			# print(thissql1)
			result1 = statsengine.execute(thissql1)
			userids = []
			mobiles = []
			for item in result1:
				userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1])), "wallet":str(item[2]),"id":str(item[3])})
				mobiles.append(str(item[0]).lower())

			thissql2 = "insert into wallet_transactions (type,amount,user_id,category,related_id,description) values"
			thissql3 = "update users set wallet_money=100 where user_id in ("
			separator = " "
			separator3 = " "
			updatewallets = 0
			for item in userids:
				w = float(item['wallet']) 
				change = 100-w
				# print(w,change,item['wallet'])
				if change<=0:
					change=0
					# print ("ignoring",item['id'])
				else:
					thissql2 += separator+ "('1'"+","+str(int(change))+","+item['id']+",13,0,'34 day cron')"
					separator=", " 
					thissql3 += separator3+ item['id']
					separator3=", "
					item['wallet'] = '100'
					updatewallets=1 

			thissql2+=";"
			thissql3+=");"
			if(updatewallets==1):
				result2 = statsengine.execute(thissql2)
				statssession.commit()
				result3 = statsengine.execute(thissql3)
				statssession.commit()

			if (len(userids)>0):
				thissql4 = "update users set wallet_cap=100 where mobile_number in ('"+"','".join(mobiles)+"');"
				result4 = statsengine.execute(thissql4)
				statssession.commit()

			# print(thissql2)
			# print(thissql3)
			# print(thissql4)

			statssession.remove()
			if len(userids) > 0:
				for item in userids:
					msg = "Hi%20"+item['name'].replace(" ","%20")+"%21%20You%20have%20Rs%20"+item['wallet']+"%20in%20your%20Twigly%20wallet.%20Order%20on%20the%20Twigly%20app%20for%20Rs%20"+"100"+"%20off%20on%20your%20next%20order.%20https%3A%2F%2Fgoo.gl%2FbMNEr4"
					number = item['mobile']
					# print(number,msg)
					sendTwiglySMS(number,msg)


			sendTwiglyMail('Dormant Third Party SMS <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for Dormant Third Party on "+parsedstartdate.strftime("%Y-%m-%d"), "SMS sent to '"+"','".join(mobiles)+"'", 'plain')

	def sendWalletBalanceSMS(self, parsedstartdate, ignore_mobiles):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select distinct u.mobile_number, u.name, u.wallet_money, u.user_id, u.wallet_cap from users u left join orders o on o.user_id=u.user_id where u.verified&2=0 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59') and u.mobile_number not in ('"+"','".join(ignore_mobiles)+"') and u.wallet_money>1;"
			# print(thissql1)
			result1 = statsengine.execute(thissql1)
			userids = []
			mobiles = []
			for item in result1:
				userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1])), "wallet":int(item[2]), "id":str(item[3]), 'wallet_cap':int(item[4])})
				mobiles.append(str(item[0]).lower())

			statssession.remove()
			if len(userids) > 0:
				for item in userids:
					wallet_cap = item['wallet_cap']
					if wallet_cap>item['wallet']:
						wallet_cap=item['wallet']
					msg = "Hi%20"+item['name'].replace(" ","%20")+"%21%20You%20have%20Rs%20"+str(item['wallet'])+"%20in%20your%20Twigly%20wallet.%20Order%20on%20the%20Twigly%20app%20for%20Rs%20"+str(wallet_cap)+"%20off%20on%20your%20next%20order.%20https%3A%2F%2Fgoo.gl%2FbMNEr4"
					number = item['mobile']
					# print(number,msg)
					sendTwiglySMS(number,msg)
 

			sendTwiglyMail('Wallet Balance 15 day SMS <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for Wallet Balance on "+parsedstartdate.strftime("%Y-%m-%d"), "SMS sent to '"+"','".join(mobiles)+"'", 'plain')
			return mobiles;

	def sendPreorderSMS(self, parsedstartdate, ignore_mobiles, ignore_mobiles2):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select distinct u.mobile_number, u.name from users u left join orders o on o.user_id=u.user_id where u.verified&2=0 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59') and u.mobile_number not in ('"+"','".join(ignore_mobiles)+"') and u.mobile_number not in ('"+"','".join(ignore_mobiles2)+"');"
			# print(thissql1)
			result1 = statsengine.execute(thissql1)
			userids = []
			mobiles = []
			for item in result1:
				userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1]))})
				mobiles.append(str(item[0]).lower())

			statssession.remove()
			if len(userids) > 0:
				for item in userids:
					msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20Plan%20your%20meal%20ahead%20and%20get%2015%25%20cashback%20on%20all%20Pre-orders%20from%20Twigly.%20Call%20011-39595911%20or%20visit%20goo.gl%2FxpAf1i"
					number = item['mobile']
					# print(number,msg)
					sendTwiglySMS(number,msg)

			sendTwiglyMail('Wallet Balance 15 day SMS <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for Wallet Balance on "+parsedstartdate.strftime("%Y-%m-%d"), "SMS sent to '"+"','".join(mobiles)+"'", 'plain')
			return mobiles;



	def sendRewardSMS(self,parsedstartdate):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select u.mobile_number, u.name, u.reward_points from users u left join orders o on o.user_id=u.user_id where u.verified&2=0 and u.reward_points>=15 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59');"
			result1 = statsengine.execute(thissql1)
			userids = []
			mobiles = []
			for item in result1:
				userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1])), 'points':int(item[2])})
				mobiles.append(str(item[0]).lower())

			statssession.remove()
			if len(userids) > 0:
				for item in userids:
					msg=""
					reward_points = item['points']
					if (reward_points>=15 and reward_points<20):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%2015%20points%20to%20get%20zero%20delivery%20charges%20on%20all%20orders%20for%20the%20next%207%20days.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=20 and reward_points<30):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%2020%20points%20for%20Rs%2040%20wallet%20money.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=30 and reward_points<40):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%2030%20points%20for%2010%25%20discount.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=40 and reward_points<50):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%2040%20points%20to%20get%20zero%20delivery%20charges%20on%20all%20orders%20for%20the%20next%2030%20days.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=50 and reward_points<70):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%2050%20points%20for%20Rs%20125%20wallet%20money.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=70 and reward_points<75):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%2070%20points%20for%2010%25%20discount.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=75 and reward_points<100):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%2075%20points%20to%20get%20a%20free%20dessert%20with%20every%20order%20for%20the%20next%2014%20days.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=100 and reward_points<125):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%20100%20points%20for%20Rs%20300%20wallet%20money.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=125 and reward_points<150):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%20100%20points%20to%20get%20zero%20delivery%20charges%20on%20all%20orders%20for%20the%20next%2090%20days.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=150 and reward_points<300):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%20150%20points%20for%2010%25%20discount.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=300 and reward_points<500):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%20300%20points%20for%2020%25%20discount.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					elif (reward_points>=500):
						msg = "Hi%20"+item['name'].replace(" ","%20")+"%2C%20you%20have%20collected%20"+str(reward_points)+"%20reward%20points.%20You%20can%20exchange%20500%20points%20for%2050%25%20discount.%20Visit%20https%3A%2F%2Ftwigly.in%2Frewards"
					number = item['mobile']
					# print(number,msg)
					sendTwiglySMS(number,msg)


			sendTwiglyMail('Reward SMS <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for Rewards on "+parsedstartdate.strftime("%Y-%m-%d"), "SMS sent to '"+"','".join(mobiles)+"'", 'plain')
			return mobiles


	def sendwalletsms(self,lastorderdate, walletexpirydate,statsengine):
		thissql1 = "select distinct u.mobile_number, u.name, u.wallet_money, u.wallet_cap from users u  left join orders o on o.user_id=u.user_id where u.verified&2=0 and u.wallet_money>=1 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.order_status in (3,10,11,12,16) and o.date_add>='" + lastorderdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<='" + lastorderdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + lastorderdate.strftime("%Y-%m-%d") + " 23:59:59');"
		print(thissql1)
		result1 = statsengine.execute(thissql1)
		userids = []
		mobiles = []
		for item in result1:
			userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1])), 'wallet':int(item[2]), 'wallet_cap':int(item[3])})
			mobiles.append(str(item[0]).lower())

		if len(userids) > 0:
			for item in userids:
				msg=""
				wallet = item['wallet']
				wallet_cap = item['wallet_cap']
				if wallet_cap>wallet:
					wallet_cap=wallet
				lastdate = walletexpirydate.strftime("%b %d").replace(" ","%20")
				msg="Hi%20"+item['name'].replace(" ","%20")+"%21%20Your%20Rs%20"+str(wallet)+"%20Twigly%20Wallet%20balance%20will%20expire%20on%20"+lastdate+".%20Order%20from%20the%20Twigly%20app%20to%20get%20Rs%20"+str(wallet_cap)+"%20off%20on%20your%20next%20order.%20goo.gl%2FbMNEr4"
				number = item['mobile']
				# print(number,msg)
				sendTwiglySMS(number,msg)
		sendTwiglyMail('Wallet SMS <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for Wallet Expiry on "+lastdate, "SMS sent to '"+"','".join(mobiles)+"'", 'plain')

	def sendrewardexsms(self,lastorderdate, rewardexpirydate,statsengine):
		thissql1 = "select distinct u.mobile_number, u.name, u.reward_points from users u  left join orders o on o.user_id=u.user_id where u.verified&2=0 and u.reward_points>=1 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.order_status in (3,10,11,12,16) and o.date_add>='" + lastorderdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<='" + lastorderdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + lastorderdate.strftime("%Y-%m-%d") + " 23:59:59');"
		print(thissql1)
		result1 = statsengine.execute(thissql1)
		userids = []
		mobiles = []
		for item in result1:
			userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1])), 'points':int(item[2])})
			mobiles.append(str(item[0]).lower())

		if len(userids) > 0:
			for item in userids:
				msg=""
				rewardpoints = item['points']
				lastdate = rewardexpirydate.strftime("%b %d").replace(" ","%20")
				msg="Hi%20"+item['name'].replace(" ","%20")+"%21%20Your%20"+str(rewardpoints)+"%20points%20Twigly%20Rewards%20balance%20will%20expire%20on%20"+lastdate+".%20Open%20up%20the%20Twigly%20app%20to%20redeem.%20goo.gl%2FbMNEr4"
				number = item['mobile']
				# print(number,msg)
				sendTwiglySMS(number,msg)
		sendTwiglyMail('Reward SMS <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for Reward Expiry on "+lastdate, "SMS sent to '"+"','".join(mobiles)+"'", 'plain')


	def sendExpiryMessages(self):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))

			lastorderdate=datetime.date.today() - datetime.timedelta(days=69)
			walletexpirydate=datetime.date.today() + datetime.timedelta(days=21)
			self.sendwalletsms(lastorderdate,walletexpirydate,statsengine)

			lastorderdate=datetime.date.today() - datetime.timedelta(days=83)
			walletexpirydate=datetime.date.today() + datetime.timedelta(days=7)
			self.sendwalletsms(lastorderdate,walletexpirydate,statsengine)

			lastorderdate=datetime.date.today() - datetime.timedelta(days=99)
			rewardexpirydate=datetime.date.today() + datetime.timedelta(days=21)
			self.sendrewardexsms(lastorderdate,rewardexpirydate,statsengine)

			lastorderdate=datetime.date.today() - datetime.timedelta(days=113)
			rewardexpirydate=datetime.date.today() + datetime.timedelta(days=7)
			self.sendrewardexsms(lastorderdate,rewardexpirydate,statsengine)

			statssession.remove()



	def sendAdhocSMS(self):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1=""
			# thissql1 = "select u.mobile_number, u.name, u.wallet_money from users u where u.verified&2=0 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and u.wallet_money>=50 and u.user_id in (select o.user_id from orders o where o.order_status in (3,10,11,12,16) and o.date_add>'2017-09-06 00:00:00');"
			result1 = statsengine.execute(thissql1)
			userids = []
			mobiles = []
			for item in result1:
				userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1])), 'points':int(item[2])})
				mobiles.append(str(item[0]).lower())

			statssession.remove()
			if len(userids) > 0:
				for item in userids:
					msg=""
					wallet = item['points']
					msg = "Hi%20"+item['name'].replace(" ","%20")+"%21%20You%20have%20"+str(wallet)+"%20balance%20in%20your%20Twigly%20wallet.%20Try%20the%20New%20Chatora%20Falafel%20Sandwich%20launched%20today%21%20Order%20now%20https%3A%2F%2Fgoo.gl%2FbMNEr4"
					number = item['mobile']
					print(number,msg)
					sendTwiglySMS(number,msg)

			sendTwiglyMail('Adhoc SMS <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for Wallet", "SMS sent to '"+"','".join(mobiles)+"'", 'plain')

	def sendDessertForAWeekSMS(self,parsedstartdate,thirdparty):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select distinct u.mobile_number, u.name, u.user_id from users u left join orders o on o.user_id=u.user_id where u.verified&2=0 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59');"
			# print(thissql1)
			if thirdparty:
				thissql1 = "select distinct u.mobile_number, u.name, u.user_id from users u left join orders o on o.user_id=u.user_id where u.verified&2=0 and o.source in (6,9,10) and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00');"

			result1 = statsengine.execute(thissql1)
			userids = []
			mobiles = []
			for item in result1:
				userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1]))})
				mobiles.append(str(item[0]).lower())

			offerenddate = datetime.date.today() + datetime.timedelta(days=7)
			if (len(userids)>0):
				thissql4 = "update users set free_dessert_reward_date='"+offerenddate.strftime("%Y-%m-%d")+" 23:59:59' where mobile_number in ('"+"','".join(mobiles)+"');"
				print(thissql4)
				# result4 = statsengine.execute(thissql4)
				# statssession.commit()

			statssession.remove()

			if len(userids) > 0:
				for item in userids:
					msg = "Dear%20"+item['name'].replace(" ","%20")+"%2C%20Get%20a%20free%20cookie%2C%20drink%20or%20snack%20bar%20with%20every%20Twigly%20order%20till%20"+offerenddate.strftime("%d %b").replace(" ","%20") +"%21%20Order%20from%20goo.gl%2FJZYkYP%20or%20call%20011-39595911"
					number = item['mobile']
					print(number,msg)
					# sendTwiglySMS(number,msg)

			# if thirdparty:
			# 	sendTwiglyMail('Third Party 21 day dessert SMS <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for Dormant Third Party on "+parsedstartdate.strftime("%Y-%m-%d"), "SMS sent to '"+"','".join(mobiles)+"'", 'plain')
			# else:
			# 	sendTwiglyMail('21 day dessert SMS <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for Dormant Third Party on "+parsedstartdate.strftime("%Y-%m-%d"), "SMS sent to '"+"','".join(mobiles)+"'", 'plain')

	def sendBreadForAWeekSMS(self,parsedstartdate):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select distinct u.mobile_number, u.name, u.user_id from users u left join orders o on o.user_id=u.user_id where u.verified&2=0 and (u.mobile_number like '6%%' or u.mobile_number like '7%%' or u.mobile_number like '8%%' or u.mobile_number like '9%%') and length (u.mobile_number)=10 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59');"
			# print(thissql1)

			result1 = statsengine.execute(thissql1)
			userids = []
			mobiles = []
			for item in result1:
				userids.append({"mobile":str(item[0]).lower(), "name":getFirstName(str(item[1]))})
				mobiles.append(str(item[0]).lower())

			offerenddate = datetime.date.today() + datetime.timedelta(days=7)
			if (len(userids)>0):
				thissql4 = "update users set free_breads_reward_date='"+offerenddate.strftime("%Y-%m-%d")+" 23:59:59' where mobile_number in ('"+"','".join(mobiles)+"');"
				print(thissql4)
				# result4 = statsengine.execute(thissql4)
				# statssession.commit()

			statssession.remove()

			if len(userids) > 0:
				for item in userids:
					msg = "Dear%20"+item['name'].replace(" ","%20")+"%2C%20Now%20pick%20any%20bread%20for%20your%20Twigly%20sandwich%20at%20no%20extra%20cost%20on%20every%20order%20till%20"+offerenddate.strftime("%d %b").replace(" ","%20") +".%20Order%20from%20goo.gl%2FJZYkYP%20or%20call%20011-39595911"
					number = item['mobile']
					print(number,msg)
					# sendTwiglySMS(number,msg)

			# sendTwiglyMail('30 day bread SMS <@testmail.com>','Raghav <***REMOVED***>',str(len(userids))+" sms sent for 30 day bread on "+parsedstartdate.strftime("%Y-%m-%d"), "SMS sent to '"+"','".join(mobiles)+"'", 'plain')


	def getDormantTemplateId(self):
		dormant_template_id = 139777 #139749 for missyou10 # int #139773 for summer10 #139777 for winter10
		return dormant_template_id

	def getDormantSegmentId(self):
		if environment_production:
			dormant_static_segment_id = 60401
		else:
			dormant_static_segment_id = 60397
		return dormant_static_segment_id

	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			parsedstartdate = datetime.date.today() - datetime.timedelta(days=30)
			bad_delivery_feedback_list = self.sendBadDeliveryFeedbackMail(parsedstartdate)
			bad_food_feedback_list = self.sendBadFoodFeedbackMail(parsedstartdate)

			parsedrewarddate = datetime.date.today() - datetime.timedelta(days=15)
			ignore_list_1 = self.sendRewardSMS(parsedrewarddate)
			ignore_list_2 = self.sendWalletBalanceSMS(parsedrewarddate, ignore_list_1)
			self.sendPreorderSMS(parsedrewarddate, ignore_list_1, ignore_list_2)
			
			self.sendDessertForAWeekSMS(datetime.date.today() - datetime.timedelta(days=1),True)
			self.sendDessertForAWeekSMS(datetime.date.today() - datetime.timedelta(days=21),False)

			self.sendBreadForAWeekSMS(datetime.date.today() - datetime.timedelta(days=30))
			
			self.sendExpiryMessages()




class MailchimpAdhocMailHandler(BaseHandler):
	def getAdhocBatch(self):#,parsedstartdate):
		if environment_production:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))
			thissql1 = "select distinct u.email from users u left join orders o on o.user_id=u.user_id left join delivery_zones b on o.delivery_zone_id = b.delivery_zone_id where u.email is not null and o.store_id = 2 and o.date_add > '2016-10-01 00:00:00' and b.falls_under_gurantee = 1;"
			#"select u.email from users u left join orders o on o.user_id=u.user_id where u.email is not null and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 23:59:59');"
			result1 = statsengine.execute(thissql1)
			userids = []
			for item in result1:
				if (len(str(item[0]))>0):
					userids.append({"email":str(item[0]).lower()})
			statssession.remove()
			# print(userids)
			# print(len(userids))

			batch_list = []
			for item in userids:
				batch_list.append({'email':item['email']})
			return batch_list
		else:
			batch_list = []
			batch_list.append({'email':'***REMOVED***'})
			return batch_list


	def getAdhocTemplateId(self):
		adhoc_template_id =  139753# int
		return adhoc_template_id

	def getAdhocSegmentId(self):
		if environment_production:
			adhoc_static_segment_id = 60409
		else:
			adhoc_static_segment_id = 60405
		return adhoc_static_segment_id

	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			parsedstartdate = datetime.date.today() #- datetime.timedelta(days=30)
			batch_list = self.getAdhocBatch()#parsedstartdate)
			list_id = getMailChimpListId()
			adhoc_template_id = self.getAdhocTemplateId()
			adhoc_static_segment_id = self.getAdhocSegmentId()		
			try:
				m = Mailchimp(mailchimpkey)
				# Create a segment for ...
				# mcresponse = m.lists.static_segment_add(list_id,"Adhoc Segment")
				# print(mcresponse)
				mcresponse = m.lists.static_segment_reset(list_id,adhoc_static_segment_id)
				mcresponse = m.lists.static_segment_members_add(list_id,adhoc_static_segment_id,batch_list)
				subject = "Buy One Get One Pizza Free!"
				mcresponse = m.campaigns.create(type="regular", options={"list_id": list_id, "subject": subject, "from_email": "@testmail.com", "from_name": "Twigly", "to_name": "*|FNAME|*", "title": subject, "authenticate": True, "generate_text": True, "template_id":adhoc_template_id}, content={"sections": {}}, segment_opts={"saved_segment_id":adhoc_static_segment_id})
				mre2 = m.campaigns.send(mcresponse["id"])
			except Exception as e:
				print ("Unexpected error:",e)
			if ('complete' in mre2 and mre2['complete']==True):
				self.write({"result": True})
				sendTwiglyMail('@testmail.com','***REMOVED***',str(len(batch_list))+" recepients of Adhoc campaign for "+parsedstartdate.strftime("%Y-%m-%d"), "Email sent successfully to " + str(batch_list),'plain')
			else:
				self.write({"result": False})
				sendTwiglyMail('@testmail.com','***REMOVED***',"Some error in the Adhoc campaign for "+parsedstartdate.strftime("%Y-%m-%d"), str(mre2),'plain')


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
		
		from sqlalchemy import text
		relevantordersstr = [str(x) for x in relevantorders]
		thissql1 = text("select a.order_id,a.delivery_address from orders a where a.order_id in ("+",".join(relevantordersstr)+");")
		result1 = statsengine.execute(thissql1)
		delivery_address = {x[0]: x[1] for x in result1}
		# deliver_address =



		results = [{"feedback": thisfeedback, "order": orderslookup[thisfeedback.order_id], "orderdetails": orderdetailslookup[thisfeedback.order_id],"address":delivery_address[thisfeedback.order_id]} for thisfeedback in feedbacks]

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
	eod_quantity = Column("eod_quantity", Integer)


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


class store_orders(statsBase):
    __tablename__ = "store_orders"
    store_order_id = Column('store_order_id', Integer, primary_key=True)
    req_store_id = Column('req_store_id', Integer)
    so_type = Column('type', Integer)
    status = Column('status', Integer)
    expected_delivery = Column('expected_delivery',DateTime)

class store_order_details(statsBase):
    __tablename__ = "store_order_details"
    store_order_detail_id = Column('store_order_detail_id', Integer, primary_key=True)
    store_order_id = Column('store_order_id', Integer, ForeignKey("store_orders.store_order_id"))
    price = Column('price', Float)
    received_quantity = Column('received_quantity', Float)


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

		active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()

		dwactivestates = [1,3,5,7,9]
		dwstoreitemsquery = statssession.query(datewise_store_menu_item).filter(datewise_store_menu_item.date_effective < parsedenddate, datewise_store_menu_item.date_effective >= parsedstartdate, datewise_store_menu_item.is_active.in_(dwactivestates))
		
		storeitemsquery = statssession.query(storemenuitem).all()
		storeitemslookup = {x.store_menu_item_id: x for x in storeitemsquery}
		menuitemsquery = statssession.query(menuitem).all()
		menuitemlookup = {x.menu_item_id: x for x in menuitemsquery}

		dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.is_for_later.op('&')(256)!=256).all()

		#dailyorderids = [thisorder.order_id for thisorder in dailyordersquery]

		storeingredientinventoryquery = statssession.query(sqlalchemy.func.sum(store_order_details.price),store_orders.req_store_id,sqlalchemy.func.date(store_orders.expected_delivery)).join(store_orders).filter(store_orders.expected_delivery < parsedenddate,store_orders.expected_delivery >= parsedstartdate, store_orders.so_type == 3,store_orders.status == 3).group_by(store_orders.req_store_id,sqlalchemy.func.date(store_orders.expected_delivery)).all()

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
			

			grosssalesquery = statssession.query(sqlalchemy.func.date(order.date_add),sqlalchemy.func.sum(orderdetail.quantity*orderdetail.price)).outerjoin(orderdetail).filter(order.order_id.in_(thisstoreorders)).group_by(sqlalchemy.func.date(order.date_add))
				
			grosssaleslookup = {}

			for grossdetail in grosssalesquery:
				if grossdetail[0].strftime("%a %b %d, %Y") in grosssaleslookup:
					grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] += (grossdetail[1])
				else:
				 	grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] = (grossdetail[1])

			grosssalesodoquery = statssession.query(sqlalchemy.func.date(order.date_add),sqlalchemy.func.sum(orderdetail.quantity*orderdetailoption.price)).outerjoin(orderdetail).outerjoin(orderdetailoption).filter(order.order_id.in_(thisstoreorders)).group_by(sqlalchemy.func.date(order.date_add))
			
			for grossdetail in grosssalesodoquery:
				if grossdetail[0].strftime("%a %b %d, %Y") in grosssaleslookup:
					grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] += (grossdetail[1])
				else:
				 	grosssaleslookup[grossdetail[0].strftime("%a %b %d, %Y")] = (grossdetail[1])

			peritemwastagequery = statssession.query(order.date_add,orderdetail.quantity,orderdetail.menu_item_id).outerjoin(orderdetail).outerjoin(orderdetailoption).filter(order.order_id.in_(thisstoreorders))
				
			for grossdetail in peritemwastagequery:
				if grossdetail[0].strftime("%a %b %d, %Y") in peritemwastage:
					if grossdetail[2] in peritemwastage[grossdetail[0].strftime("%a %b %d, %Y")]:
						peritemwastage[grossdetail[0].strftime("%a %b %d, %Y")][grossdetail[2]] -= grossdetail[1]
				else:
					peritemwastage[grossdetail[0].strftime("%a %b %d, %Y")] = {}
					peritemwastage[grossdetail[0].strftime("%a %b %d, %Y")][grossdetail[2]] = -grossdetail[1]

			wastagelookup = {dr: 0 for dr in daterange}
			midlookup = {smi.menu_item_id: smi for smi in storeitemsquery if smi.store_id == thisstore.store_id}
			for dr in peritemwastage:
				for menuitemid in peritemwastage[dr]:
					if peritemwastage[dr][menuitemid] > 0:
						wastagelookup[dr] += (peritemwastage[dr][menuitemid]*midlookup[menuitemid].cost_price)

			storewastagelookup = {dr: 0 for dr in daterange}
			storewastageitems = [(thiswastage,mystore,thisdate) for (thiswastage,mystore,thisdate) in storeingredientinventoryquery if mystore == thisstore.store_id]
			for (thiswastage,mystore,thisdate) in storewastageitems:
				storewastagelookup[thisdate.strftime("%a %b %d, %Y")] = thiswastage

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
					thisstorewastage.append(0.0)	

				try:
					thiswastagepc.append(float(storewastagelookup[daterange[c]])/float(grosssaleslookup[daterange[c]])*100.0)
				except KeyError:
					thiswastagepc.append(0.0)	


			grosssales.append(thisgrosssales)
			predictedsales.append(thispredictedsales)
			wastage.append(thiswastage)
			storewastage.append(thisstorewastage)
			wastagepc.append(thiswastagepc)
			if sum(thisgrosssales)!=0:
				stores.append({"store_id": thisstore.store_id, "name": thisstore.name, "grosssales": sum(thisgrosssales), "predictedsales": sum(thispredictedsales), "wastage": sum(thiswastage), "storewastage":sum(thisstorewastage),"wastagepc": sum(thisstorewastage)/sum(thisgrosssales)*100})
			else:
				stores.append({"store_id": thisstore.store_id, "name": thisstore.name, "grosssales": sum(thisgrosssales), "predictedsales": sum(thispredictedsales), "wastage": sum(thiswastage), "storewastage":sum(thisstorewastage),"wastagepc": 0})


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

		active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()
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
		if current_user not in ["admin","@testmail.com","@testmail.com","@testmail.com","@testmail.com"]:
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
			#parsedenddate = parsedenddate + datetime.timedelta(days=1)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%a %b %d, %Y"))

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		current_store = self.get_argument("store", "All")

		if current_user == "@testmail.com":
			current_store="2"
		elif current_user == "@testmail.com":
			current_store="3"
		elif current_user == "@testmail.com":
			current_store="5"
		elif current_user == "@testmail.com":
			current_store="12"


		active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()
		active_stores_list = [x.store_id for x in active_stores]


		if current_store == "All":
			store_list = active_stores_list
		else:
			store_list = [int(current_store)]


		current_store_name = "All"
		for thisstore in active_stores:
			if str(thisstore.store_id) == current_store:
				current_store_name = thisstore.name
				break

		store_list_str = ",".join(map(str,store_list))

		#delivery boy rating query 1
		from sqlalchemy import text
		thissql1 = text("select a.delivery_boy_id,d.name,count(*),sum(case when c.falls_under_gurantee = 1 then 1 else 0 end) as count_priority,sum(case when c.falls_under_gurantee = 0 then 1 else 0 end) as count_np,sum(case when g.delivery_rating>0 then 1 else 0 end) as total_rated,sum(case when g.delivery_rating>0 then delivery_rating else 0 end)/sum(case when g.delivery_rating>0 then 1 else 0 end) as avg_rated,sum(case when g.delivery_rating=1 then 1 else 0 end) as rated_1,sum(case when g.delivery_rating=2 then 1 else 0 end) as rated_2, sum(case when b.order_status = 10 then 1 else 0 end) as free_orders from orders b left join deliveries a on a.order_id=b.order_id left join delivery_zones c on b.delivery_zone_id=c.delivery_zone_id left join delivery_boys d on d.delivery_boy_id=a.delivery_boy_id left join feedbacks g on g.order_id = b.order_id where b.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and b.order_status in (3,4,10,11) and b.store_id in ("+store_list_str+") group by 1,2;")

		result1 = statsengine.execute(thissql1)

		resultlookup = {x[0]: x[1:] for x in result1}

		#delivery boy rating query 2
		thissql2 = text("select a.delivery_boy_id, d.name, count(*), sum(case when c.falls_under_gurantee = 1 then timestampdiff(minute,e.time_add,f.time_add) else 0 end)/sum(case when c.falls_under_gurantee = 1 then 1 else 0 end) as time_p, sum(case when c.falls_under_gurantee = 0 then timestampdiff(minute,e.time_add,f.time_add) else 0 end)/sum(case when c.falls_under_gurantee = 0 then 1 else 0 end) as time_np , sum(case when c.falls_under_gurantee = 1 then 1 else 0 end) count_p, sum(case when c.falls_under_gurantee = 0 then 1 else 0 end) count_np from orders b left join deliveries a on a.order_id=b.order_id left join delivery_zones c on b.delivery_zone_id=c.delivery_zone_id left join delivery_boys d on d.delivery_boy_id=a.delivery_boy_id left join order_status_times e on b.order_id=e.order_id left join order_status_times f on b.order_id=f.order_id left join feedbacks g on g.order_id = a.order_id where b.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and b.order_status in (3,10,11) and e.order_status=2 and f.order_status =15 and b.store_id in ("+store_list_str+") group by 1,2;")

		result2 = statsengine.execute(thissql2)
		# for row in result2:
		# 	if row[0] in resultlookup:
		# 		resultlookup[row[0]] += row[2:]
		# 	else:
		# 		resultlookup[row[0]] = [row[0],row[1],"-","-","-","-","-","-","-"] + list(row[2:])

		for row in result2:
			resultlookup[row[0]] += row[2:]

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>DB ID</th><th>Name</th><th>Total Orders</th><th>Priority Orders</th><th>Non Priority Orders</th><th>Total Ratings</th><th>Average Rating</th><th>Orders Rated 1</th><th>Orders Rated 2</th><th>Free Orders</th><th class='part2'>Count with Rating</th><th class='part2'>Time for Priority Orders</th><th class='part2'>Time for Non-Priority Orders</th><th class='part2'>Reached Destination Marked -  Priority Orders</th><th class='part2'>Reached Destination Marked - Non-Priority Orders</th></thead>"
		
		rows = ''
		for db in resultlookup:
			if len(resultlookup[db]) == 14:
				rows += "<tr><td>" + str(db) + "</td><td>" + str(resultlookup[db][0]) + "</td><td>" + str(resultlookup[db][1]) + "</td><td>" + str(resultlookup[db][2]) + "</td><td>" + str(resultlookup[db][3]) + "</td><td>" + str(resultlookup[db][4]) + "</td><td>" + str(resultlookup[db][5]) + "</td><td>" + str(resultlookup[db][6]) + "</td><td>" + str(resultlookup[db][7]) + "</td><td>" + str(resultlookup[db][8]) + "</td><td class='part2'>" + str(resultlookup[db][9]) + "</td><td class='part2'>" + str(resultlookup[db][10]) + "</td><td class='part2'>" + str(resultlookup[db][11]) + "</td><td class='part2'>" + str(resultlookup[db][12]) + "</td><td class='part2'>" + str(resultlookup[db][13]) + "</td></tr>"
			else:
				rows += "<tr><td>" + str(db) + "</td><td>" + str(resultlookup[db][0]) + "</td><td>" + str(resultlookup[db][1]) + "</td><td>" + str(resultlookup[db][2]) + "</td><td>" + str(resultlookup[db][3]) + "</td><td>" + str(resultlookup[db][4]) + "</td><td>" + str(resultlookup[db][5]) + "</td><td>" + str(resultlookup[db][6]) + "</td><td>" + str(resultlookup[db][7]) + "</td><td>" + str(resultlookup[db][8]) + "</td><td class='part2'>-</td><td class='part2'>-</td><td class='part2'>-</td><td class='part2'>-</td><td class='part2'>-</td></tr>"
		if (len(rows)):
			outputtable += rows + "</table>"
		else: 
			outputtable = ''


		#delivery boy comments
		thissql3 = text("select c.delivery_boy_id, d.name, b.date_add, a.order_id, a.delivery_rating, a.comment from feedbacks a left join orders b on a.order_id=b.order_id left join deliveries c on b.order_id=c.order_id left join delivery_boys d on c.delivery_boy_id=d.delivery_boy_id where b.order_status in (3,10,11,12,16) and a.delivery_rating in (1,2) and b.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add <'" +parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and b.store_id in ("+store_list_str+");")

		result3 = statsengine.execute(thissql3)
		deliveryfeedback = {}
		
		outputtable2 = "<table class='table tablesorter table-striped table-hover'><thead><th>DB ID</th><th>Name</th><th>Order Date</th><th>Order ID</th><th>Delivery Rating</th><th>Comment</th></thead>"
		
		rows2=''
		for item in result3:
			rows2 += "<tr><td>" + str(item[0]) + "</td><td>" + str(item[1]) + "</td><td>" + str(item[2]) + "</td><td><a href='http://twigly.in/admin/orders?f="+str(item[3])+"'>" + str(item[3]) + "</a></td><td>" + str(item[4]) + "</td><td style='text-align:left;'>" + str(item[5]) + "</td><tr>"

		if (len(rows2)):
			outputtable2 += rows2 + "</table>"
		else: 
			outputtable2 = ''


		# All Free deliveries
		thissql4 = text("select date(o.date_add), o.order_id, timediff(b.time_add,a.time_add), c.delivery_boy_id, d.name from orders o left join order_status_times as a on a.order_id=o.order_id left join order_status_times as b on b.order_id=o.order_id left join deliveries c on c.order_id=o.order_id left join delivery_boys d on d.delivery_boy_id=c.delivery_boy_id where o.order_status in (10) and a.order_status=0 and b.order_status=3 and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <'" +parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and o.store_id in ("+store_list_str+");")

		result4 = statsengine.execute(thissql4)
		deliveryfeedback = {}
		
		outputtable3 = "<table class='table tablesorter table-striped table-hover'><thead><th>Order Date</th><th>Order ID</th><th>Received to Delivery Time</th><th>Delivery Boy ID</th><th>Delivery Boy Name</th></thead>"
		
		rows3=''
		for item in result4:
			rows3 += "<tr><td>" + str(item[0]) + "</td><td><a href='http://twigly.in/admin/orders?f="+str(item[1])+"'>" + str(item[1]) + "</a></td><td>" + str(item[2]) + "</td><td>" + str(item[3]) + "</td><td>" + str(item[4]) + "</td><tr>"

		if (len(rows3)):
			outputtable3 += rows3 + "</table>"
		else: 
			outputtable3 = ''



		statssession.remove()
		self.render("templates/deliveriestemplate.html", outputtable=outputtable, outputtable2=outputtable2, outputtable3=outputtable3, user=current_user,active_stores=active_stores, current_store=current_store, current_store_name=current_store_name)


class LateDeliveryHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ["admin","@testmail.com","@testmail.com","@testmail.com","@testmail.com"]:
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


		thissql1 = "select date(o.date_add), dz.falls_under_gurantee, st.name, o.order_id, us.name, o.delivery_address, timediff(d.time_add,a.time_add), dbs.name from orders o left join delivery_zones dz on o.delivery_zone_id=dz.delivery_zone_id left join stores st on o.store_id = st.store_id left join users us on us.user_id=o.user_id left join deliveries dd on o.order_id=dd.order_id left join delivery_boys dbs on dd.delivery_boy_id=dbs.delivery_boy_id left join order_status_times as a on o.order_id = a.order_id left join order_status_times as d on o.order_id = d.order_id where a.order_status=1 and d.order_status=3 and ((dz.falls_under_gurantee = 1 and timediff(d.time_add,a.time_add)>'00:59:59') or (dz.falls_under_gurantee = 0 and timediff(d.time_add,a.time_add)>'01:29:59')) and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <'" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' order  by 1,3,8,2 desc,7 desc;"
		result1 = statsengine.execute(thissql1)

		result1backup = []
		orderids = []
		totaltimelookup = {}
		for item in result1:
			result1backup.append(item)
			orderids.append(str(item[3]))
			totaltimelookup[str(item[3])] = item[6]

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>Date</th><th>Store</th><th>Delivery Boy</th><th>Priority</th><th>Order ID</th><th>Total Time Taken</th><th>Customer Name</th><th>Delivery Address</th><th>Cooking to Dispatch</th><th>Dispatch to Reached</th><th>Reached to Delivered</th></thead>"

		prioritylookup = {0:"Non Priority", 1:"Priority"}

		if(len(orderids) > 0):

			cookingtodispatchsql = "select o.order_id, timediff(b.time_add,a.time_add) from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id = b.order_id where a.order_status=1 and b.order_status=2 and o.order_id in ("+",".join(orderids)+");"

			result2 = statsengine.execute(cookingtodispatchsql)
			c2dlookup = {oid:0 for oid in orderids}
			for item in result2:
				c2dlookup[str(item[0])] = item[1]

			dispatchtoreachedsql = "select o.order_id, timediff(b.time_add,a.time_add) from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id = b.order_id where a.order_status=2 and b.order_status=15 and o.order_id in ("+",".join(orderids)+");"

			result3 = statsengine.execute(dispatchtoreachedsql)
			d2rlookup = {oid:0 for oid in orderids}
			for item in result3:
				d2rlookup[str(item[0])] = item[1]

			reachedtodeliveredsql = "select o.order_id, timediff(b.time_add,a.time_add) from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id = b.order_id where a.order_status=15 and b.order_status=3 and o.order_id in ("+",".join(orderids)+");"

			result4 = statsengine.execute(reachedtodeliveredsql)
			r2dlookup = {oid:0 for oid in orderids}
			for item in result4:
				r2dlookup[str(item[0])] = item[1]


			for item in result1backup:
				key1 = str(item[3])
				outputtable += "<tr><td>" + str(item[0]) + "</td><td>"+str(item[2])+"</td><td>"+str(item[7])+"</td><td>" + prioritylookup[item[1]] +"</td><td><a href='http://twigly.in/admin/orders?f="+str(item[3])+"'>"+str(item[3])+"</a></td><td>"+str(totaltimelookup[key1])+"</td><td>"+str(item[4])+"</td><td>"+str(item[5])+"</td><td>"+str(c2dlookup[key1])+"</td><td>"+str(d2rlookup[key1])+"</td><td>"+str(r2dlookup[key1])+"</td></tr>"

		else:
			outputtable += "<tr><td colspan=12 style='text-align: left !important;'>No delayed orders in this time frame. Adjust the date range to see order delays.</td></tr>"

		outputtable += "</table>"

		displayenddate = parsedenddate +  datetime.timedelta(days=-1)

		statssession.remove()
		self.render("templates/simpletabletemplate.html", page_url="/latedeliveries", page_title="Twigly Late Orders Summary",table_title="Late Orders Summary - Prioirty orders over 60 mintues and Non Priority orders over 90 minutes - "+parsedstartdate.strftime("%Y-%m-%d")+" to "+displayenddate.strftime("%Y-%m-%d"),tableSort="[]", daterange=daterange, outputtable=outputtable, user=current_user)


class AllOrderTimeHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ["admin"]:
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


		thissql1 = "select date(o.date_add), dz.falls_under_gurantee, st.name, o.order_id, us.name, o.delivery_address, timediff(d.time_add,a.time_add), dbs.name from orders o left join delivery_zones dz on o.delivery_zone_id=dz.delivery_zone_id left join stores st on o.store_id = st.store_id left join users us on us.user_id=o.user_id left join deliveries dd on o.order_id=dd.order_id left join delivery_boys dbs on dd.delivery_boy_id=dbs.delivery_boy_id left join order_status_times as a on o.order_id = a.order_id left join order_status_times as d on o.order_id = d.order_id where a.order_status=1 and d.order_status=3 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <'" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' order  by 1,3,8,2 desc,7 desc;"
		result1 = statsengine.execute(thissql1)

		result1backup = []
		orderids = []
		totaltimelookup = {}
		for item in result1:
			if (str(item[3]) not in orderids):
				result1backup.append(item)
				orderids.append(str(item[3]))
				totaltimelookup[str(item[3])] = item[6]

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>Date</th><th>Store</th><th>Delivery Boy</th><th>Priority</th><th>Order ID</th><th>Total Time Taken</th><th>Customer Name</th><th>Delivery Address</th><th>Cooking to Dispatch</th><th>Dispatch to Reached</th><th>Reached to Delivered</th></thead>"

		prioritylookup = {0:"Non Priority", 1:"Priority"}

		if(len(orderids) > 0):

			cookingtodispatchsql = "select o.order_id, timediff(b.time_add,a.time_add) from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id = b.order_id where a.order_status=1 and b.order_status=2 and o.order_id in ("+",".join(orderids)+");"

			result2 = statsengine.execute(cookingtodispatchsql)
			c2dlookup = {oid:0 for oid in orderids}
			for item in result2:
				c2dlookup[str(item[0])] = item[1]

			dispatchtoreachedsql = "select o.order_id, timediff(b.time_add,a.time_add) from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id = b.order_id where a.order_status=2 and b.order_status=15 and o.order_id in ("+",".join(orderids)+");"

			result3 = statsengine.execute(dispatchtoreachedsql)
			d2rlookup = {oid:0 for oid in orderids}
			for item in result3:
				d2rlookup[str(item[0])] = item[1]

			reachedtodeliveredsql = "select o.order_id, timediff(b.time_add,a.time_add) from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id = b.order_id where a.order_status=15 and b.order_status=3 and o.order_id in ("+",".join(orderids)+");"

			result4 = statsengine.execute(reachedtodeliveredsql)
			r2dlookup = {oid:0 for oid in orderids}
			for item in result4:
				r2dlookup[str(item[0])] = item[1]

			for item in result1backup:
				key1 = str(item[3])
				outputtable += "<tr><td>" + str(item[0]) + "</td><td>"+str(item[2])+"</td><td>"+str(item[7])+"</td><td>" 
				if item[1] in prioritylookup:
					outputtable += prioritylookup[item[1]]
				outputtable += "</td><td><a href='http://twigly.in/admin/orders?f="+str(item[3])+"'>"+str(item[3])+"</a></td><td>"+str(totaltimelookup[key1])+"</td><td>"+str(item[4])+"</td><td>"+str(item[5])+"</td><td>"+str(c2dlookup[key1])+"</td><td>"+str(d2rlookup[key1])+"</td><td>"+str(r2dlookup[key1])+"</td></tr>"

		else:
			outputtable += "<tr><td colspan=12 style='text-align: left !important;'>No orders in this time frame. Adjust the date range to see order delays.</td></tr>"

		outputtable += "</table>"

		displayenddate = parsedenddate +  datetime.timedelta(days=-1)

		statssession.remove()
		self.render("templates/simpletabletemplate.html", page_url="/alldeliveries", page_title="Twigly All Orders Time Summary",table_title="All Order Times - "+parsedstartdate.strftime("%Y-%m-%d")+" to "+displayenddate.strftime("%Y-%m-%d"),tableSort="[]", daterange=daterange, outputtable=outputtable, user=current_user)



class DeliveryStatsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ["admin","@testmail.com","@testmail.com","@testmail.com","@testmail.com"]:
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
		active_stores = statssession.query(store).filter(store.is_active == True, store.store_type.in_(outlet_types)).all()
		active_stores_list = [x.store_id for x in active_stores]

		thissql3 = "select b.store_id, date(b.date_add), sum(case when g.delivery_rating>0 then delivery_rating else 0 end), sum(case when g.delivery_rating>0 then 1 else 0 end), sum(case when g.delivery_rating>0 then delivery_rating else 0 end)/sum(case when g.delivery_rating>0 then 1 else 0 end), sum(case when b.order_id>0 then 1 else 0 end) from orders b left join feedbacks g on g.order_id = b.order_id where b.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and b.order_status in (3,10,11,12,16) group by 1,2;" 
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

		thissql4 = "select o.store_id, date(o.date_add), sum(case when timediff(b.time_add,a.time_add) <= '00:10:00' then 1 else 0 end) as count_0_10, sum(case when timediff(b.time_add,a.time_add) >'00:10:00' and timediff(b.time_add,a.time_add) <='00:20:00' then 1 else 0 end) as count_10_20, sum(case when timediff(b.time_add,a.time_add) >'00:20:00' and timediff(b.time_add,a.time_add) <='00:30:00' then 1 else 0 end) as count_20_30, sum(case when timediff(b.time_add,a.time_add) > '00:30:00' then 1 else 0 end) as count_30_plus from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id=b.order_id where a.order_status=2 and b.order_status=15 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"

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
				if len(deliverytimeresultsbystore[thisstore.store_id][thisdate])==4:
					list0_10.append(int(deliverytimeresultsbystore[thisstore.store_id][thisdate][0]))
					list10_20.append(int(deliverytimeresultsbystore[thisstore.store_id][thisdate][1]))
					list20_30.append(int(deliverytimeresultsbystore[thisstore.store_id][thisdate][2]))
					list30_plus.append(int(deliverytimeresultsbystore[thisstore.store_id][thisdate][3]))
			deliverytimestack.append({"store_id": thisstore.store_id, "name": thisstore.name, "deliverytime010":list0_10,"deliverytime1020":list10_20,"deliverytime2030":list20_30,"deliverytime30plus":list30_plus,})


		# priority vs non priority orders by store

		thissql5 = "select o.store_id, date(o.date_add),sum(case when c.falls_under_gurantee = 1 then 1 else 0 end) as count_priority, sum(case when c.falls_under_gurantee = 0 then 1 else 0 end) as count_np from orders o left join delivery_zones c on o.delivery_zone_id=c.delivery_zone_id where o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"

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
				if (len(priorityorderresultsbystore[thisstore.store_id][thisdate])==2):
					listpriority.append(float(100*priorityorderresultsbystore[thisstore.store_id][thisdate][1]/(priorityorderresultsbystore[thisstore.store_id][thisdate][0]+priorityorderresultsbystore[thisstore.store_id][thisdate][1]))) # non-priority order %age
			priorityorderstack.append({"store_id": thisstore.store_id, "name": thisstore.name,"prioritypc":listpriority})


		# Average cooking to dispatch time by store

		thissql6 = "select o.store_id, date(o.date_add), count(*), sum(time_to_sec(timediff(b.time_add,a.time_add))) as sumtime_cooking  from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id=b.order_id where a.order_status=1 and b.order_status=2 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"

		result6 = statsengine.execute(thissql6)
		cookingtodispatcklookup = {x.store_id: { thisdate:[] for thisdate in daterange} for x in active_stores}
		for item in result6:
			if item[0] in active_stores_list:
				if item[1].strftime("%a %b %d, %Y") in daterange:
					cookingtodispatcklookup[item[0]][item[1].strftime("%a %b %d, %Y")] = item[2:]


		# Average dispatch to reached dest time by store

		thissql7 = "select o.store_id, date(o.date_add), count(*), sum(time_to_sec(timediff(b.time_add,a.time_add))) as sumtime_dispatching  from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id=b.order_id where a.order_status=2 and b.order_status=15 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"
		result7 = statsengine.execute(thissql7)
		dispatchtoreachlookup = {x.store_id: { thisdate:[] for thisdate in daterange} for x in active_stores}
		for item in result7:
			if item[0] in active_stores_list:
				if item[1].strftime("%a %b %d, %Y") in daterange:
					dispatchtoreachlookup[item[0]][item[1].strftime("%a %b %d, %Y")] = item[2:]

		# Average reached to delivere dest time by store
		thissql8 = "select o.store_id, date(o.date_add), count(*), sum(time_to_sec(timediff(b.time_add,a.time_add))) as sumtime_delivering  from orders o left join order_status_times as a on o.order_id = a.order_id left join order_status_times as b on o.order_id=b.order_id where a.order_status=15 and b.order_status=3 and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"
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
				if (len(cookingtodispatcklookup[thisstore.store_id][thisdate])==2):
					list1.append(float(cookingtodispatcklookup[thisstore.store_id][thisdate][1]/cookingtodispatcklookup[thisstore.store_id][thisdate][0]/60)) # avg time in minutes
				if (len(dispatchtoreachlookup[thisstore.store_id][thisdate])==2):
					list2.append(float(dispatchtoreachlookup[thisstore.store_id][thisdate][1]/dispatchtoreachlookup[thisstore.store_id][thisdate][0]/60)) # avg time in minutes
				if (len(reachtodeliverlookup[thisstore.store_id][thisdate])==2):
					list3.append(float(reachtodeliverlookup[thisstore.store_id][thisdate][1]/reachtodeliverlookup[thisstore.store_id][thisdate][0]/60)) # avg time in minutes
			cookingtimes.append({"store_id": thisstore.store_id, "name": thisstore.name,"cookingtime":list1,"dispatchtime":list2,"deliverytime":list3})


		# Average deliveries per delivery boy per day by store
		thissql9 = "select o.store_id, date(o.date_add), count(d.delivery_id), count( distinct db.delivery_boy_id) from orders o left join deliveries d on o.order_id=d.order_id left join delivery_boys db on db.delivery_boy_id = d.delivery_boy_id where o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and o.order_status in (3,10,11,12,16) and o.source not in (7,9,10) and db.delivery_boy_id not in (3,4,5,42,39,57,55,38,64,31,28) group by 1,2;"
		result9 = statsengine.execute(thissql9)
		avgdeliveriesbystorelookup = {x.store_id: { thisdate:[] for thisdate in daterange} for x in active_stores}
		for item in result9:
			if item[0] in active_stores_list:
				if item[1].strftime("%a %b %d, %Y") in daterange:
					avgdeliveriesbystorelookup[item[0]][item[1].strftime("%a %b %d, %Y")] = item[2:]

		averagedeliveries = {}
		for thisstore in active_stores:
			list1 = []
			for thisdate in daterange:
				if (len(avgdeliveriesbystorelookup[thisstore.store_id][thisdate])==2):
					list1.append(float(avgdeliveriesbystorelookup[thisstore.store_id][thisdate][0]/avgdeliveriesbystorelookup[thisstore.store_id][thisdate][1]))  
			averagedeliveries[thisstore.store_id]=list1

		statssession.remove()
		self.render("templates/deliverystatstemplate.html", daterange=daterange,avgdeliveryscorebystore=avgdeliveryscorebystore, deliverytimestack=deliverytimestack, priorityorderstack=priorityorderstack, cookingtimes=cookingtimes, user=current_user, averagedeliveries=averagedeliveries)

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
		thissql2 = "select date(a.date_add),count(distinct b.user_id) from orders a left join orders b on a.user_id=b.user_id where a.order_status in (13,14) and b.order_status in (3,10,11,12,16) and date(a.date_add) = date(b.date_add) and a.date_add > '" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and a.date_add < '" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add > '" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add < '" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and a.payment_status not in (26) group by 1;"

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
		thissql5 = "select date(a.date_add), b.user_id from orders a left join orders b on a.user_id=b.user_id where a.order_status in (13,14) and b.order_status in (3,10,11,12,16) and date(a.date_add) = date(b.date_add) and a.date_add > '" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and a.date_add < '" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add > '" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and b.date_add < '" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' and a.payment_status not in (26);"

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
		userlookup = {}

		if (len(allusers)>0):
			thissql6 = "select user_id, name, mobile_number, date_add from users where user_id in ("+str(allusers).strip('{}')+");"
			result6 = statsengine.execute(thissql6)
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


class CouponHandler(BaseHandler):
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

		thissql1 = "select date(o.date_add), c.coupon_code, count(o.order_id) from orders o left join coupons c on c.coupon_id=o.coupon_id where o.order_status in (3,10,11,12,16) and c.coupon_id is not null and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <'" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00' group by 1,2 order by 1 desc;"
		result1 = statsengine.execute(thissql1)

		responselookup = {thisdate:[] for thisdate in daterange}
		for item in result1:
			if item[0].strftime("%Y-%m-%d") in daterange:
				responselookup[item[0].strftime("%Y-%m-%d")].append(item[1:])
		
		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>Date</th><th>Coupon Code</th><th>Orders Delivered</th></thead>"
		
		for thisdate in daterange:
			currentlist = responselookup[thisdate]
			for (thiscoupon,couponcount) in currentlist:
				outputtable += "<tr><td>" + str(thisdate) + "</td><td>" + thiscoupon + "</td><td>"+str(couponcount)+"</td></tr>"

		outputtable += "</table>"

		statssession.remove()
		self.render("templates/simpletabletemplate.html", page_url="/couponuse", page_title="Twigly Coupons Use",table_title="List of Coupon Users",tableSort="[[0,1],[2,1]]", daterange=daterange, outputtable=outputtable, user=current_user)


class RetentionHandler(BaseHandler):
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

			parsedenddate = datetime.date.today() - datetime.timedelta(days=30)
			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date() 
			parsedenddate = parsedenddate - datetime.timedelta(days=30)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date() - datetime.timedelta(days=30)

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		thissql1 = "select date(o.date_add), count(o.order_id), count(u.user_id), sum(case when f.feedback_id is null then 1 else 0 end), sum(case when f.food_rating=1 then 1 else 0 end), sum(case when f.food_rating=2 then 1 else 0 end), sum(case when f.food_rating=3 then 1 else 0 end),sum(case when f.food_rating=4 then 1 else 0 end),sum(case when f.food_rating=5 then 1 else 0 end), sum(case when f.delivery_rating=1 then 1 else 0 end), sum(case when f.delivery_rating=2 then 1 else 0 end), sum(case when f.delivery_rating=3 then 1 else 0 end), sum(case when f.delivery_rating=4 then 1 else 0 end), sum(case when f.delivery_rating=5 then 1 else 0 end) from users u left join orders o on o.user_id=u.user_id left join feedbacks f on f.order_id=o.order_id where u.user_id in (select o.user_id from orders o where o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59') and u.user_id not in (select o.user_id from orders o where o.order_status in (3,10,11,12,16) and o.date_add>'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59') and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and o.order_status in (3,10,11,12,16) group by 1 order by 1;"
		result1 = statsengine.execute(thissql1)

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>Last Order Date</th><th>Last Orders</th><th>Feedbacks Received (%)</th><th>FR=1</th><th>FR=2</th><th>FR=3</th><th>FR=4</th><th>FR=5</th><th>DR=1</th><th>DR=2</th><th>DR=3</th><th>DR=4</th><th>DR=5</th></thead>"

		outputtable+= "<tr><td>Dormant</td></tr>"

		for item in result1:
			outputtable+= "<tr><td>" + str(item[0]) + "</td><td>" + str(item[1]) + "</td><td>" + str(item[1] - item[3]) + " (" + "{:10.2f}".format((item[1]-item[3])*100/item[1])+"% )" + "</td><td>" + str(item[4]) + "</td><td>" + str(item[5]) + "</td><td>" + str(item[6]) + "</td><td>" + str(item[7]) + "</td><td>" + str(item[8]) + "</td><td>" + str(item[9]) + "</td><td>" + str(item[10]) + "</td><td>" + str(item[11]) + "</td><td>" + str(item[12]) + "</td><td>" + str(item[13]) + "</td></tr>"

		outputtable+= "<tr><td>Dead</td></tr>"


		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 7
			else:
				horizon = int(horizon)

			parsedenddate = datetime.date.today() - datetime.timedelta(days=60)
			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date() 
			parsedenddate = parsedenddate - datetime.timedelta(days=60)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date() - datetime.timedelta(days=60)


		thissql2 = "select date(o.date_add), count(o.order_id), count(u.user_id), sum(case when f.feedback_id is null then 1 else 0 end), sum(case when f.food_rating=1 then 1 else 0 end), sum(case when f.food_rating=2 then 1 else 0 end), sum(case when f.food_rating=3 then 1 else 0 end),sum(case when f.food_rating=4 then 1 else 0 end),sum(case when f.food_rating=5 then 1 else 0 end), sum(case when f.delivery_rating=1 then 1 else 0 end), sum(case when f.delivery_rating=2 then 1 else 0 end), sum(case when f.delivery_rating=3 then 1 else 0 end), sum(case when f.delivery_rating=4 then 1 else 0 end), sum(case when f.delivery_rating=5 then 1 else 0 end) from users u left join orders o on o.user_id=u.user_id left join feedbacks f on f.order_id=o.order_id where u.user_id in (select o.user_id from orders o where o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59') and u.user_id not in (select o.user_id from orders o where o.order_status in (3,10,11,12,16) and o.date_add>'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59') and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and o.order_status in (3,10,11,12,16) group by 1 order by 1;"
		result2 = statsengine.execute(thissql2)

		for item in result2:
			outputtable+= "<tr><td>" + str(item[0]) + "</td><td>" + str(item[1]) + "</td><td>" + str(item[1] - item[3]) + " (" + "{:10.2f}".format((item[1]-item[3])*100/item[1])+"% )" + "</td><td>" + str(item[4]) + "</td><td>" + str(item[5]) + "</td><td>" + str(item[6]) + "</td><td>" + str(item[7]) + "</td><td>" + str(item[8]) + "</td><td>" + str(item[9]) + "</td><td>" + str(item[10]) + "</td><td>" + str(item[11]) + "</td><td>" + str(item[12]) + "</td><td>" + str(item[13]) + "</td></tr>"

		outputtable += "</table>"

		statssession.remove()
		self.render("templates/simpletabletemplate.html", page_url="/retention", page_title="Twigly Retention",table_title="Last order analysis feedback (-30,-60 days)",tableSort="[]", outputtable=outputtable, user=current_user)


class DormantRegularsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("admin","twiglyservice"):
			self.redirect('/stats')

		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 7
			else:
				horizon = int(horizon)

			parsedenddate = datetime.date.today() - datetime.timedelta(days=30)

			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
			daterange = [parsedstartdate.strftime("%Y-%m-%d")]
			for c in range(horizon-1):
				daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%Y-%m-%d"))
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date() 
			parsedenddate = parsedenddate - datetime.timedelta(days=30)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date() - datetime.timedelta(days=30)
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%Y-%m-%d"))

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		thissql1 = "select date(o.date_add), u.mobile_number, u.email, aa.cc, aa.tt from users u left join orders o on o.user_id=u.user_id left join (select n.user_id as u_id, count(n.order_id) as cc, sum(n.total) as tt from orders n where n.order_status in (3,10,11,12,16) group by 1 having cc>=10) as aa on aa.u_id=u.user_id where aa.cc>=10 and u.email is not null and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59');"
		result1 = statsengine.execute(thissql1)

		responselookup = {thisdate:[] for thisdate in daterange}
		usersAlreadyAdded = set()
		for item in result1:
			if item[0].strftime("%Y-%m-%d") in daterange:
				if item[1] not in usersAlreadyAdded:
					responselookup[item[0].strftime("%Y-%m-%d")].append(item[1:])
					usersAlreadyAdded.add(item[1])

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>Last Order Date</th><th>User Mobile Number</th><th>User Email</th><th>Order Count</th><th>Avg Order Total</th></thead>"
		
		for thisdate in daterange:
			currentlist = responselookup[thisdate]
			for (thismobile,thisemail,thisordercount, thisordertotals) in currentlist:
				averageordervalue = 0
				if (thisordercount>0):
					averageordervalue = thisordertotals/thisordercount
				outputtable += "<tr><td>" + str(thisdate) + "</td><td><a href='http://twigly.in/admin/orders?f="+str(thismobile)+"'>" + str(thismobile) + "</a></td><td>" + str(thisemail)+"</td><td>"+str(thisordercount)+"</td><td>"+str(int(averageordervalue))+"</td></tr>"

		outputtable += "</table>"

		statssession.remove()
		self.render("templates/simpletabletemplate.html", page_url="/dormantregulars", page_title="Twigly Dormant Regulars",table_title="List of "+str(len(usersAlreadyAdded))+" Dormant Regulars (Regular users who have not ordered in last 30 days)",tableSort="[[0,1],[3,1]]", daterange=daterange, outputtable=outputtable, user=current_user)


class DeadRegularsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("admin","twiglyservice"):
			self.redirect('/stats')

		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 7
			else:
				horizon = int(horizon)

			parsedenddate = datetime.date.today() - datetime.timedelta(days=60)

			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
			daterange = [parsedstartdate.strftime("%Y-%m-%d")]
			for c in range(horizon-1):
				daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%Y-%m-%d"))
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date() 
			parsedenddate = parsedenddate - datetime.timedelta(days=60)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date() - datetime.timedelta(days=60)
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%Y-%m-%d"))

		# parsedstartdate = datetime.date.today() - datetime.timedelta(days=90)
		# parsedenddate = datetime.date.today() - datetime.timedelta(days=30)
		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		thissql1 = "select date(o.date_add), u.mobile_number, u.email, aa.cc, aa.tt from users u left join orders o on o.user_id=u.user_id left join (select n.user_id as u_id, count(n.order_id) as cc, sum(n.total) as tt from orders n where n.order_status in (3,10,11,12,16) group by 1 having cc>=10) as aa on aa.u_id=u.user_id where aa.cc>=10 and u.email is not null and o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' and u.user_id not in (select m.user_id from orders m where m.order_status in (3,10,11,12,16) and m.date_add>'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59');"
		result1 = statsengine.execute(thissql1)

		responselookup = {thisdate:[] for thisdate in daterange}
		usersAlreadyAdded = set()
		for item in result1:
			if item[0].strftime("%Y-%m-%d") in daterange:
				if item[1] not in usersAlreadyAdded:
					responselookup[item[0].strftime("%Y-%m-%d")].append(item[1:])
					usersAlreadyAdded.add(item[1])

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>Last Order Date</th><th>User Mobile Number</th><th>User Email</th><th>Order Count</th><th>Avg Order Total</th></thead>"
		
		for thisdate in daterange:
			currentlist = responselookup[thisdate]
			for (thismobile,thisemail,thisordercount, thisordertotals) in currentlist:
				averageordervalue = 0
				if (thisordercount>0):
					averageordervalue = thisordertotals/thisordercount
				outputtable += "<tr><td>" + str(thisdate) + "</td><td><a href='http://twigly.in/admin/orders?f="+str(thismobile)+"'>" + str(thismobile) + "</a></td><td>" + str(thisemail)+"</td><td>"+str(thisordercount)+"</td><td>"+str(int(averageordervalue))+"</td></tr>"


		outputtable += "</table>"

		statssession.remove()
		self.render("templates/simpletabletemplate.html", page_url="/deadregulars", page_title="Twigly Dead Regulars",table_title="List of "+str(len(usersAlreadyAdded))+" Dead Regulars (Regular users who have not ordered in last 60 days)",tableSort="[[0,1],[3,1]]", daterange=daterange, outputtable=outputtable, user=current_user)

class SectorsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ["admin","@testmail.com","@testmail.com","@testmail.com","@testmail.com"]:
			self.redirect('/stats')

		horizon = self.get_argument("horizon", None)
		startdate = self.get_argument("startdate", None)
		enddate = self.get_argument("enddate", None)
		if startdate is None:
			if horizon is None:
				horizon = 7
			else:
				horizon = int(horizon)

			parsedenddate = datetime.date.today()

			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
			daterange = [parsedstartdate.strftime("%Y-%m-%d")]
			for c in range(horizon-1):
				daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%Y-%m-%d"))
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date() 
			parsedenddate = parsedenddate
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%Y-%m-%d"))

		# parsedstartdate = datetime.date.today() - datetime.timedelta(days=90)
		# parsedenddate = datetime.date.today() - datetime.timedelta(days=30)
		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		thissql1 = "select o.store_id, dz.delivery_zone_id, dz.name, c.city_name, count(o.order_id) from orders o left join delivery_zones dz on dz.delivery_zone_id=o.delivery_zone_id left join cities c on dz.city_id=c.city_id where o.order_status in (3,10,11,12,16) and o.date_add>'" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"

		# print(thissql1)

		result1 = statsengine.execute(thissql1)

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>Store</th><th>Delivery Zone</th><th>Order Count</th></thead>"

		storemap = {2:"City Court", 3:"Sector 46", 5:"Kalkaji", 12:"Munirka"}
		for row in result1:
			# print(row)
			if row[0] in storemap:
				outputtable+="<tr><td>" + storemap[row[0]] + "</td><td>" + str(row[2])+", "+str(row[3]) + "</td><td>" + str(row[4])+"</td></tr>"

		outputtable += "</table>"

		statssession.remove()
		self.render("templates/simpletabletemplate.html", page_url="/sectors", page_title="Twigly Sectors",table_title="Orders by Store by Sector - "+parsedstartdate.strftime("%Y-%m-%d")+" to "+parsedenddate.strftime("%Y-%m-%d") ,tableSort="[[0,1],[2,1]]", daterange=daterange, outputtable=outputtable, user=current_user)


class FoodCostHandler(BaseHandler):
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

			parsedenddate = datetime.date.today() - datetime.timedelta(days=1)

			parsedstartdate = parsedenddate - datetime.timedelta(days=horizon)
			daterange = [parsedstartdate.strftime("%Y-%m-%d")]
			for c in range(horizon-1):
				daterange.append((parsedstartdate + datetime.timedelta(days=(c+1))).strftime("%Y-%m-%d"))
		
		else:
			parsedenddate = datetime.datetime.strptime(enddate, "%d/%m/%y").date() 
			# parsedenddate = parsedenddate - datetime.timedelta(days=0)
			parsedstartdate = datetime.datetime.strptime(startdate, "%d/%m/%y").date()
			daterange = []
			for c in range((parsedenddate - parsedstartdate).days):
				daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%Y-%m-%d"))

		prevclosingdate = parsedstartdate - datetime.timedelta(days=1)
		closingdate = parsedenddate
		# parsedenddate = datetime.date.today() - datetime.timedelta(days=30)
		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		stores=[2,3,5,7,8]
		productions = [6,4,7,1,5,3,8]

		prevclosinglookup = {s:{p:float(0.0) for p in productions} for s in stores}
		closinglookup = {s:{p:float(0.0) for p in productions} for s in stores}
		issuancelookup = {s:{p:float(0.0) for p in productions} for s in stores}
		issuancelookup2 = {s:{p:float(0.0) for p in productions} for s in stores}
		consumptionlookup = {s:float(0.0) for s in stores}
		wastagelookup = {s:float(0.0) for s in stores}

		prevclosingsql_1 = "select so.res_store_id, ing.production, sum(sod.price) from ingredients ing left join store_order_details sod on ing.ingredient_id=sod.ingredient_id left join store_orders so on sod.store_order_id=so.store_order_id where so.type=5 and so.res_store_id in (2,3,5,7,8) and ing.production in (6,4,7,1,5,3,8) and so.status=3 and date(so.expected_delivery)='" + prevclosingdate.strftime("%Y-%m-%d") + "' group by 1,2;"
		
		result1 = statsengine.execute(prevclosingsql_1)
		# print(prevclosingsql_1)		
		for row in result1:
			# print (row)
			if row[0] in stores and row[1] in productions:
				prevclosinglookup[row[0]][row[1]] = row[2]

		# print(prevclosinglookup)

		closingsql_1 = "select so.res_store_id, ing.production, sum(sod.price) from ingredients ing left join store_order_details sod on ing.ingredient_id=sod.ingredient_id left join store_orders so on sod.store_order_id=so.store_order_id where so.type=5 and so.res_store_id in (2,3,5,7,8) and ing.production in (6,4,7,1,5,3,8) and so.status=3 and date(so.expected_delivery)='" + closingdate.strftime("%Y-%m-%d") + "' group by 1,2;"

		result1 = statsengine.execute(closingsql_1)
		# print(closingsql_1)
		for row in result1:
			# print (row)
			if row[0] in stores and row[1] in productions:
				closinglookup[row[0]][row[1]] = row[2]
		
		# print(closinglookup)

		issuancesql_1 = "select so.req_store_id, ing.production, sum(sod.price) from ingredients ing left join store_order_details sod on ing.ingredient_id=sod.ingredient_id left join store_orders so on sod.store_order_id=so.store_order_id where so.type in (0,1) and so.req_store_id in (2,3,5,7,8) and ing.production in (6,4,7,1,5,3,8) and so.status=3 and date(so.expected_delivery)>'" + prevclosingdate.strftime("%Y-%m-%d") + "' and date(so.expected_delivery)<='" + closingdate.strftime("%Y-%m-%d") + "' group by 1,2;"

		result1 = statsengine.execute(issuancesql_1)
		# print (issuancesql_1)
		for row in result1:
			# print (row)
			if row[0] in stores and row[1] in productions:
				issuancelookup[row[0]][row[1]] = row[2]

		# print(issuancelookup)


		issuancesql_2 = "select so.req_store_id, ing.production, sum(sod.price) from ingredients ing left join store_order_details sod on ing.ingredient_id=sod.ingredient_id left join store_orders so on sod.store_order_id=so.store_order_id where so.type in (1)  and so.req_store_id in (2,3,5,7,8) and ing.production in (6,4,7,1,5,3,8) and so.status=3 and date(so.expected_delivery)>'" + prevclosingdate.strftime("%Y-%m-%d") + "' and date(so.expected_delivery)<='" + closingdate.strftime("%Y-%m-%d") + "' and so.vendor_id in (5,21) group by 1,2;"

		result1 = statsengine.execute(issuancesql_2)
		# print (issuancesql_2)
		for row in result1:
			# print (row)
			if row[0] in stores and row[1] in productions:
				issuancelookup2[row[0]][row[1]] = row[2]
		# print(issuancelookup2)


		consumptionsql_1 = "select so.res_store_id, sum(sod.price) from ingredients ing left join store_order_details sod on ing.ingredient_id=sod.ingredient_id left join store_orders so on sod.store_order_id=so.store_order_id where so.type in (0,2) and so.res_store_id in (2,3,5,7,8) and ing.production in (6,4,7,1,5,3,8) and so.status=3 and date(so.expected_delivery)>'" + prevclosingdate.strftime("%Y-%m-%d") + "' and date(so.expected_delivery)<='" + closingdate.strftime("%Y-%m-%d") + "' group by 1;"

		result1 = statsengine.execute(consumptionsql_1)
		# print (consumptionsql_1)
		for row in result1:
			# print (row)
			if row[0] in stores:
				consumptionlookup[row[0]] = row[1]

		# print(consumptionlookup)

		wastage_1 = "select so.res_store_id, sum(sod.price) from ingredients ing left join store_order_details sod on ing.ingredient_id=sod.ingredient_id left join store_orders so on sod.store_order_id=so.store_order_id where so.type in (3) and so.res_store_id in (2,3,5,7,8) and ing.production in (6,4,7,1,5,3,8) and so.status=3 and date(so.expected_delivery)>'" + prevclosingdate.strftime("%Y-%m-%d") + "' and date(so.expected_delivery)<='" + closingdate.strftime("%Y-%m-%d") + "' group by 1;"

		result1 = statsengine.execute(wastage_1)
		# print(wastage_1)
		for row in result1:
			# print (row)
			if row[0] in stores:
				wastagelookup[row[0]] = row[1]

		# print(wastagelookup)

		
		#gross CC
		store_list = [2]
		gross_cc = getgross(statssession,store_list,parsedstartdate,parsedenddate+datetime.timedelta(days=(1)))
		# print(gross_cc)

		#gross 46
		# store_list = [3]
		# gross_46 = getgross(statssession,store_list,parsedstartdate,parsedenddate+datetime.timedelta(days=(1)))
		# print(gross_46)

		store_list = [5]
		gross_kkj = getgross(statssession,store_list,parsedstartdate,parsedenddate+datetime.timedelta(days=(1)))
		# print(gross_kkj)

		outputtable = "<table style='border-collapse: separate; border-spacing: 6px;'>"
		outputtable += "<thead><tr style='background: #ccc;'><th></th><th colspan='4' style='text-align: center;'>City Court</th><th colspan='4' style='text-align: center;'>Kalkaji</th><th colspan='4' style='text-align: center;'>CK</th><th colspan='4' style='text-align: center;'>Bakery</th><th style='text-align: center;'>Sum</th></tr></thead>"
		outputtable += "<tbody><tr><td style='font-weight: bold;'>Gross Sale</td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(gross_cc)+"</td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(gross_kkj)+"</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(gross_cc+gross_kkj)+"</td></tr>"
		outputtable += "<tr style='font-weight: bold;'><td>Food Cost</td><td>Opening</td><td>Issuance</td><td>Consumption</td><td>Closing</td><td>Opening</td><td>Issuance</td><td>Consumption</td><td>Closing</td><td>Opening</td><td>Issuance</td><td>Consumption</td><td>Closing</td><td>Opening</td><td>Issuance</td><td>Consumption</td><td>Closing</td><td>Sum</td></tr>"

		p=6
		outputtable += "<tr><td style='font-weight: bold;'>Dairy</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p]+issuancelookup[7][p]-closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p]+issuancelookup[8][p]-closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format( prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p] )+"</td></tr>"
		sum1 = prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p]
		if issuancelookup2[2][p]>0 or issuancelookup2[5][p]>0 or issuancelookup2[7][p] or issuancelookup2[8][p]:
			outputtable += "<tr><td style='background: #ccc;'><i>- Bought Out</i></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[2][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[5][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[7][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[8][p])+"</i></td><td></td><td></td><td></td></tr>"


		p=4
		outputtable += "<tr><td style='font-weight: bold;'>Vegetable</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p]+issuancelookup[7][p]-closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p]+issuancelookup[8][p]-closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format( prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p] )+"</td></tr>"
		sum1+=prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p]
		if issuancelookup2[2][p]>0 or issuancelookup2[5][p]>0 or issuancelookup2[7][p] or issuancelookup2[8][p]:
			outputtable += "<tr><td style='background: #ccc;'><i>- Bought Out</i></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[2][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[5][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[7][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[8][p])+"</i></td><td></td><td></td><td></td></tr>"


		p=7
		outputtable += "<tr><td style='font-weight: bold;'>Cheese</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p]+issuancelookup[7][p]-closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p]+issuancelookup[8][p]-closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format( prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p] )+"</td></tr>"
		sum1+=prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p]
		if issuancelookup2[2][p]>0 or issuancelookup2[5][p]>0 or issuancelookup2[7][p] or issuancelookup2[8][p]:
			outputtable += "<tr><td style='background: #ccc;'><i>- Bought Out</i></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[2][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[5][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[7][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[8][p])+"</i></td><td></td><td></td><td></td></tr>"


		p=1
		outputtable += "<tr><td style='font-weight: bold;'>From CPU</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p]+issuancelookup[7][p]-closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p]+issuancelookup[8][p]-closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format( max(prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p], sum(prevclosinglookup[7].values())+sum(issuancelookup[7].values())-sum(closinglookup[7].values()) + sum(prevclosinglookup[8].values())+sum(issuancelookup[8].values())-sum(closinglookup[8].values()) ) )+"</td></tr>"
		sum1+= max(prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p], sum(prevclosinglookup[7].values())+sum(issuancelookup[7].values())-sum(closinglookup[7].values()) + sum(prevclosinglookup[8].values())+sum(issuancelookup[8].values())-sum(closinglookup[8].values()) )
		if issuancelookup2[2][p]>0 or issuancelookup2[5][p]>0 or issuancelookup2[7][p] or issuancelookup2[8][p]:
			outputtable += "<tr><td style='background: #ccc;'><i>- Bought Out</i></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[2][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[5][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[7][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[8][p])+"</i></td><td></td><td></td><td></td></tr>"


		p=5
		outputtable += "<tr><td style='font-weight: bold;'>Meat</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p]+issuancelookup[7][p]-closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p]+issuancelookup[8][p]-closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format( prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p] )+"</td></tr>"
		sum1+=prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p]
		if issuancelookup2[2][p]>0 or issuancelookup2[5][p]>0 or issuancelookup2[7][p] or issuancelookup2[8][p]:
			outputtable += "<tr><td style='background: #ccc;'><i>- Bought Out</i></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[2][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[5][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[7][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[8][p])+"</i></td><td></td><td></td><td></td></tr>"


		p=3
		outputtable += "<tr><td style='font-weight: bold;'>Dry Store</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p]+issuancelookup[7][p]-closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p]+issuancelookup[8][p]-closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format( prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p] )+"</td></tr>"
		sum1+=prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p] 
		if issuancelookup2[2][p]>0 or issuancelookup2[5][p]>0 or issuancelookup2[7][p] or issuancelookup2[8][p]:
			outputtable += "<tr><td style='background: #ccc;'><i>- Bought Out</i></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[2][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[5][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[7][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[8][p])+"</i></td><td></td><td></td><td></td></tr>"


		p=8
		outputtable += "<tr><td style='font-weight: bold;'>Ice Cream</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[2][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[5][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[7][p]+issuancelookup[7][p]-closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[7][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(issuancelookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(prevclosinglookup[8][p]+issuancelookup[8][p]-closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format(closinglookup[8][p])+"</td><td style='text-align: right;'>"+"{:10.2f}".format( prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p] )+"</td></tr>"
		if issuancelookup2[2][p]>0 or issuancelookup2[5][p]>0 or issuancelookup2[7][p] or issuancelookup2[8][p]:
			outputtable += "<tr><td style='background: #ccc;'><i>- Bought Out</i></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[2][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[5][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[7][p])+"</i></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'><i>"+"{:10.2f}".format(issuancelookup2[8][p])+"</i></td><td></td><td></td><td></td></tr>"


		sum1 += prevclosinglookup[2][p]+issuancelookup[2][p]-closinglookup[2][p]+prevclosinglookup[5][p]+issuancelookup[5][p]-closinglookup[5][p] 
		sumcc = sum(prevclosinglookup[2].values())+sum(issuancelookup[2].values())-sum(closinglookup[2].values())
		sumkkj = sum(prevclosinglookup[5].values())+sum(issuancelookup[5].values())-sum(closinglookup[5].values())

		outputtable += "<tr style='font-weight: bold;'><td>Gross Food Cost</td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(sumcc)+"</td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(sumkkj)+"</td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(sum(prevclosinglookup[7].values())+sum(issuancelookup[7].values())-sum(closinglookup[7].values()))+"</td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(sum(prevclosinglookup[8].values())+sum(issuancelookup[8].values())-sum(closinglookup[8].values()))+"</td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(sum1)+"</td></tr>"

		outputtable += "<tr><td style='background: #ccc;'>Gross Food Cost %</td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format(sumcc/gross_cc*100)+"%</td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format(sumkkj/gross_kkj*100)+"%</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format(sum1/(gross_cc+gross_kkj)*100)+"%</td></tr>"

		outputtable += "<tr><td style='font-weight: bold;'>Standard Food Cost</td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(consumptionlookup[2])+"</td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(consumptionlookup[5])+"</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(consumptionlookup[2]+consumptionlookup[5])+"</td></tr>"
		outputtable += "<tr><td style='background: #ccc;'>Standard Food Cost %</td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format(consumptionlookup[2]/gross_cc*100)+"%</td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format(consumptionlookup[5]/gross_kkj*100)+"%</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format((consumptionlookup[2]+consumptionlookup[5])/(gross_cc+gross_kkj)*100)+"%</td></tr>"


		outputtable += "<tr><td style='font-weight: bold;'>Wastage</td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(wastagelookup[2])+"</td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(wastagelookup[5])+"</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(wastagelookup[2]+wastagelookup[5])+"</td></tr>"
		outputtable += "<tr><td style='background: #ccc;'>Wastage %</td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format(wastagelookup[2]/gross_cc*100)+"%</td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format(wastagelookup[5]/gross_kkj*100)+"%</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format((wastagelookup[2]+wastagelookup[5])/(gross_cc+gross_kkj)*100)+"%</td></tr>"
		

		outputtable += "<tr><td style='font-weight: bold;'>Unaccounted</td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(sumcc - consumptionlookup[2]-wastagelookup[2])+"</td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(sumkkj - consumptionlookup[5] - wastagelookup[5])+"</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td style='text-align: right;'>"+"{:10.2f}".format(sum1 - consumptionlookup[2]- consumptionlookup[5]- wastagelookup[2]-wastagelookup[5])+"</td></tr>"
		outputtable += "<tr><td style='background: #ccc;'>Unaccounted %</td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format((sumcc - consumptionlookup[2]-wastagelookup[2])/gross_cc*100)+"%</td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format((sumkkj - consumptionlookup[5] - wastagelookup[5])/gross_kkj*100)+"%</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td style='text-align: right;background: #ccc;'>"+"{:10.2f}".format((sum1 - consumptionlookup[2]- consumptionlookup[5]- wastagelookup[2]-wastagelookup[5])/(gross_cc+gross_kkj)*100)+"%</td></tr>"

		# - Bought Out 
		# Cash Purchase 

		outputtable += "</tbody></table>"

		statssession.remove()
		self.render("templates/simpletabletemplate.html", page_url="/foodcost", page_title="Twigly Food Cost",table_title="Food Cost "+parsedstartdate.strftime("%Y-%m-%d")+" to "+parsedenddate.strftime("%Y-%m-%d") ,tableSort="[]", daterange=daterange, outputtable=outputtable, user=current_user)

def getgross(statssession,store_list,parsedstartdate,parsedenddate):

	daterange = []
	for c in range((parsedenddate - parsedstartdate).days):
		daterange.append((parsedstartdate + datetime.timedelta(days=c)).strftime("%Y-%m-%d"))

	dailyordersquery = statssession.query(order).filter(order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress + returnedStates), order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.store_id.in_(store_list), order.is_for_later.op('&')(256)!=256).all()

	dailyorderids = [thisorder.order_id for thisorder in dailyordersquery if (thisorder.order_status not in returnedStates)]

	grosssalesquery = statssession.query(sqlalchemy.func.date(order.date_add),sqlalchemy.func.sum(orderdetail.quantity*orderdetail.price)).outerjoin(orderdetail).filter(order.order_id.in_(dailyorderids)).group_by(sqlalchemy.func.date(order.date_add))
		
	grosssaleslookup = {}

	for grossdetail in grosssalesquery:
		if grossdetail[0].strftime("%Y-%m-%d") in grosssaleslookup:
			grosssaleslookup[grossdetail[0].strftime("%Y-%m-%d")] += (grossdetail[1])
		else:
		 	grosssaleslookup[grossdetail[0].strftime("%Y-%m-%d")] = (grossdetail[1])

	grosssalesodoquery = statssession.query(sqlalchemy.func.date(order.date_add),sqlalchemy.func.sum(orderdetail.quantity*orderdetailoption.price)).outerjoin(orderdetail).outerjoin(orderdetailoption).filter(order.order_id.in_(dailyorderids)).group_by(sqlalchemy.func.date(order.date_add))
	
	for grossdetail in grosssalesodoquery:
		if grossdetail[0].strftime("%Y-%m-%d") in grosssaleslookup:
			grosssaleslookup[grossdetail[0].strftime("%Y-%m-%d")] += (grossdetail[1])
		else:
		 	grosssaleslookup[grossdetail[0].strftime("%Y-%m-%d")] = (grossdetail[1])

	totalsales = []

	dailysalesquery = statssession.query(order.date_add, sqlalchemy.func.sum(order.delivery_charges)).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.order_status.in_(deliveredStates + inProgress), order.store_id.in_(store_list), order.is_for_later.op('&')(256)!=256).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))

	deliverycharges = []

	thisdeliverydetails = {thisresult[0].strftime("%Y-%m-%d"): float(thisresult[1]) for thisresult in dailysalesquery}

	for thisdate in daterange:
		if thisdate in thisdeliverydetails:
			deliverycharges.append(thisdeliverydetails[thisdate])
		else:
			deliverycharges.append(0) 

	sum=0.0
	for c in range(0, len(daterange)):
		try:
			totalsales.append(float(grosssaleslookup[daterange[c]])+float(deliverycharges[c]))
			sum+=float(grosssaleslookup[daterange[c]])+float(deliverycharges[c])
		except KeyError:
			totalsales.append(0.0)

	return sum


class EsselTestHandler(BaseHandler):
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

		thissql1 = "select date(o.date_add), count(o.order_id) from orders o left join user_addresses ua on ua.user_id=o.user_id where o.order_status in (3,10,11,12,16) and (ua.address1 like '%%essel%%' or ua.address1 like '%%Essel%%' or ua.address2 like '%%essel%%' or ua.address2 like '%%Essel%%') and ua.is_deleted=0 and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add<'" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1 order by 1 desc;"
		
		result1 = statsengine.execute(thissql1)

		responselookup = {thisdate:[] for thisdate in daterange}
		for item in result1:
			if item[0].strftime("%Y-%m-%d") in daterange:
				responselookup[item[0].strftime("%Y-%m-%d")].append(item[1])

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>Order Date</th><th>Order Count</th></thead>"
		
		for thisdate in daterange:
			currentlist = responselookup[thisdate]
			for (thisordercount) in currentlist:
				outputtable += "<tr><td>" + str(thisdate) + "</td><td>"+str(thisordercount)+"</td></tr>"

		outputtable += "</table>"

		thissql2 = "select count(distinct user_id) from user_addresses where address1 like '%%essel%%' or address1 like '%%Essel%%' or address2 like '%%essel%%' or address2 like '%%Essel%%' and is_deleted=0;"
		result2 = statsengine.execute(thissql2)
		totalusercount=0
		for item in result2:
			totalusercount=item[0]

		statssession.remove()
		self.render("templates/simpletabletemplate.html", page_url="/esseltest", page_title="Twigly Essel NB Test",table_title=str(totalusercount)+" Users with Essel in their Addresses. Daily orders below",tableSort="[[0,1]]", daterange=daterange, outputtable=outputtable, user=current_user)

class RewardStatsHandler(BaseHandler):
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

		transaction_type=[{"type":"DEBIT", "value":'0'},{"type":"CREDIT", "value":'1'}]
		transaction_value_list = [x["value"] for x in transaction_type]

		# Total Reward Points Credited and Debited in a day
		thissql1 = "select o.type, date(o.date_add), count(*), sum(o.points) from reward_transactions o where o.description!='reward clearance cron' and o.points > 0 and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"
		result1 = statsengine.execute(thissql1)

		rewardtransactionlookup = {x["value"]: { thisdate:[] for thisdate in daterange} for x in transaction_type}
		for item in result1:
			if item[0] in transaction_value_list:
				if item[1].strftime("%a %b %d, %Y") in daterange:
					rewardtransactionlookup[item[0]][item[1].strftime("%a %b %d, %Y")] = item[2:]

		debittransactions = []
		debitpoints = []
		credittransactions = []
		creditpoints = []

		for thisdate in daterange:
			if (len(rewardtransactionlookup['0'][thisdate])==2):
				debittransactions.append(int(rewardtransactionlookup['0'][thisdate][0])) 
				debitpoints.append(int(rewardtransactionlookup['0'][thisdate][1]))
			else:
				debittransactions.append(0) 
				debitpoints.append(0)

			if (len(rewardtransactionlookup['1'][thisdate])==2):
				credittransactions.append(int(rewardtransactionlookup['1'][thisdate][0])) 
				creditpoints.append(int(rewardtransactionlookup['1'][thisdate][1])) 
			else:
				credittransactions.append(0) 
				creditpoints.append(0) 

		# Total points credit in period
		# Total points debited in period
		# Average (including bulk)
		totalcredittransactions = sum(credittransactions)
		totalcreditpoints = sum(creditpoints)
		totalcreditavgpoints = 0.0
		if (totalcredittransactions>0):
			totalcreditavgpoints = float(totalcreditpoints)/float(totalcredittransactions)

		totaldebittransactions = sum(debittransactions)
		totaldebitpoints = sum(debitpoints)

		totaldebitavgpoints = 0.0
		if (totaldebittransactions>0):
			totaldebitavgpoints = float(totaldebitpoints)/float(totaldebittransactions)

		thissqlcron = "select date(o.date_add), count(*), sum(o.points) from reward_transactions o where o.description='reward clearance cron' and o.type=0 and o.points > 0 and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1;"
		resultcron = statsengine.execute(thissqlcron)
		cleartransactions = []
		clearpoints = []

		cleartransactionlookup = {thisdate:[] for thisdate in daterange}
		for item in resultcron:
			if item[0].strftime("%a %b %d, %Y") in daterange:
				cleartransactionlookup[item[0].strftime("%a %b %d, %Y")] = item[1:]

		for thisdate in daterange:
			if (len(cleartransactionlookup[thisdate])==2):
				cleartransactions.append(int(cleartransactionlookup[thisdate][0])) 
				clearpoints.append(int(cleartransactionlookup[thisdate][1]))
			else:
				cleartransactions.append(0) 
				clearpoints.append(0)

		totalclearpoints = sum(clearpoints) 
		totalcleartransactions = sum(cleartransactions)

		# <50 Reward Points Credited in a day
		# Total points credit in period - small transactions
		# Average /transaction/day (excluding bulk)
		thissql2 = "select o.type, date(o.date_add), count(*), sum(o.points) from reward_transactions o where  o.points > 0 and o.points<50 and o.type=1 and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1,2;"
		result2 = statsengine.execute(thissql2)

		smlrewardtransactionlookup = { thisdate:[] for thisdate in daterange}
		for item in result2:
			if item[1].strftime("%a %b %d, %Y") in daterange:
				smlrewardtransactionlookup[item[1].strftime("%a %b %d, %Y")] = item[2:]

		smlcredittransactions = []
		smlcreditpoints = []
		for thisdate in daterange:
			if (len(smlrewardtransactionlookup[thisdate])==2):
				smlcredittransactions.append(int(smlrewardtransactionlookup[thisdate][0])) 
				smlcreditpoints.append(int(smlrewardtransactionlookup[thisdate][1])) 
			else:
				smlcredittransactions.append(0) 
				smlcreditpoints.append(0) 

		smlcreditavgpoints = []
		for index in range(len(daterange)):
			if (smlcredittransactions[index]>0):
				smlcreditavgpoints.append(float(smlcreditpoints[index])/float(smlcredittransactions[index]))
			else:
				smlcreditavgpoints.append(0.0)

		totalsmlcredittransactions = sum(smlcredittransactions)
		totalsmlcreditpoints = sum(smlcreditpoints)
		totalsmlavgpoints = 0.0
		if (totalsmlcredittransactions>0):
			totalsmlavgpoints = float(totalsmlcreditpoints)/float(totalsmlcredittransactions)


		# %Orders <Total 250 
		thissql3 = "select date(o.date_add), sum(case when o.total<250 then 1 else 0 end), sum(case when o.total>=250 then 1 else 0 end) from orders o where  o.order_status in (3,10,11,12,16) and o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 23:59:59' group by 1;"
		result3 = statsengine.execute(thissql3)

		ordercountlookup = { thisdate:[] for thisdate in daterange}
		for item in result3:
			if item[0].strftime("%a %b %d, %Y") in daterange:
				ordercountlookup[item[0].strftime("%a %b %d, %Y")] = item[1:]

		orderlessthan250pc = []
		for thisdate in daterange:
			if (len(ordercountlookup[thisdate])==2 and (float(ordercountlookup[thisdate][0])+float(ordercountlookup[thisdate][1]))>0.0):
				orderlessthan250pc.append(100.0*float(ordercountlookup[thisdate][0])/(float(ordercountlookup[thisdate][0])+float(ordercountlookup[thisdate][1])))
			else:
				orderlessthan250pc.append(0) 

		statssession.remove()
		self.render("templates/rewardstatstemplate.html", daterange=daterange, debittransactions=debittransactions, debitpoints=debitpoints, credittransactions=credittransactions, creditpoints=creditpoints,cleartransactions=cleartransactions, smlcredittransactions=smlcredittransactions,smlcreditpoints=smlcreditpoints,smlcreditavgpoints=smlcreditavgpoints,totalcredittransactions=totalcredittransactions,totalcreditpoints=totalcreditpoints,totalcreditavgpoints=totalcreditavgpoints,totaldebittransactions=totaldebittransactions, totaldebitpoints=totaldebitpoints,totaldebitavgpoints=totaldebitavgpoints,totalsmlcredittransactions=totalsmlcredittransactions,totalsmlcreditpoints=totalsmlcreditpoints,totalsmlavgpoints=totalsmlavgpoints,orderlessthan250pc=orderlessthan250pc,user=current_user,clearpoints=clearpoints,totalclearpoints=totalclearpoints,totalcleartransactions=totalcleartransactions)

class RewardLeaderHandler(BaseHandler):
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


		
		from sqlalchemy import text
		thissql1 = text("select a.user_id,a.name,a.mobile_number,a.reward_points,date(a.date_add) from users a where a.reward_points>0 order by a.reward_points desc limit 100;")

		result1 = statsengine.execute(thissql1)

		outputtable = "<table class='table tablesorter table-striped table-hover'><thead><th>UserID</th><th>Name</th><th>Mobile Number</th><th>Total Points</th><th>Date Added</th><</thead>"
		for row in result1:
			outputtable += "<tr><td>" + str(row[0]) + "</td><td>" + str(row[1]) + "</td><td><a href='http://twigly.in/admin/orders?f="+str(row[2])+"'>" + str(row[2]) + "</a></td><td>" + str(row[3]) + "</td><td>" + str(row[4]) + "</td></tr>"		
		outputtable += "</table>"


		statssession.remove()
		self.render("templates/rewardleaderstemplate.html", outputtable=outputtable, user=current_user)

class SubscriptionHandler(BaseHandler):
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

			parsedenddate = datetime.date.today() + datetime.timedelta(days=1)

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

		transaction_type=[{"type":"CREDIT", "category": "Recharge", "value":0}, {"type":"DEBIT", "category": "Payment", "value":1}, {"type":"CREDIT", "category": "Revert", "value":3}, {"type":"CREDIT", "category": "Payment failed", "value":4}, {"type":"CREDIT", "category": "Cashback", "value":6}]
		transaction_value_list = [x["value"] for x in transaction_type]

		# 0 Recharge, 1 Payment, 2 Unknown, 3 revert, 4 payment failed, 5 manual, 6 cashback
		thissql1 = "select o.type, o.category, date(o.date_add), o.amount from subscription_transactions o where o.date_add>='" + parsedstartdate.strftime("%Y-%m-%d") + " 00:00:00' and o.date_add <='" + parsedenddate.strftime("%Y-%m-%d") + " 00:00:00';"
		result1 = statsengine.execute(thissql1)

		rechargedata = {}
		rechargevalue = 0
		rechargecount = 0
		cashbackvalue = 0
		transactioncount = [0 for x in daterange]
		transactionvalue = [0 for x in daterange]
		for item in result1:
			if item[1] in transaction_value_list:
				if item[1] == 0: #recharge
					if "Rs. " + str(int(item[3])) in rechargedata:
						rechargedata["Rs. " + str(int(item[3]))][daterange.index(item[2].strftime("%a %b %d, %Y"))] += 1
					else:
						rechargedata["Rs. " + str(int(item[3]))] = [0 for x in daterange]
						rechargedata["Rs. " + str(int(item[3]))][daterange.index(item[2].strftime("%a %b %d, %Y"))] = 1

					rechargevalue += float(item[3])
					rechargecount +=1
				elif item[1] == 6:
					cashbackvalue += float(item[3])
				else:
					if item[1] == 1:
						transactioncount[daterange.index(item[2].strftime("%a %b %d, %Y"))] += 1
						transactionvalue[daterange.index(item[2].strftime("%a %b %d, %Y"))] += float(item[3])
					else:
						transactioncount[daterange.index(item[2].strftime("%a %b %d, %Y"))] -= 1
						transactionvalue[daterange.index(item[2].strftime("%a %b %d, %Y"))] -= float(item[3])

		rechargeshowdata = []
		for rd in rechargedata:
			rechargeshowdata.append({"name": rd, "data": rechargedata[rd]})

		totaltransactions = sum(transactioncount)
		totaltransactionvalue = round(sum(transactionvalue),2)

		statssession.remove()
		self.render("templates/subscriptiontemplate.html", daterange=daterange, rechargecount=rechargecount, rechargedata=rechargeshowdata, rechargevalue=rechargevalue, transactioncount=transactioncount, transactionvalue=transactionvalue, totaltransactions=totaltransactions, totaltransactionvalue=totaltransactionvalue, cashbackvalue=cashbackvalue, user=current_user)

class ResetSegmentHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user not in ("admin"):
			self.redirect('/stats')
		
		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		allorders = statssession.query(order.user_id, order.date_add, order.store_id).filter(order.order_status.in_(deliveredStates + deliveredFreeStates)).order_by(order.date_add.desc())
		#.limit(5000)

		orderUserLookup = {}
		for item in allorders:
			if (item[0] in orderUserLookup):
				if (len(orderUserLookup[item[0]])<10): #limiting to last 10 orders
					orderUserLookup[item[0]].append(item[1:])
			else:
				orderUserLookup[item[0]]=[]
				orderUserLookup[item[0]].append(item[1:])

		morning_users = []
		evening_users = []
		morning_store_users = {thisstore:[] for thisstore in [2,3,5]}
		evening_store_users = {thisstore:[] for thisstore in [2,3,5]}

		for thisuser in orderUserLookup:
			morning_count=0
			evening_count=0
			morning_store=-1
			evening_store=-1
			for (thistime, thisstore) in orderUserLookup[thisuser]:
				thistime.time()
				sameday6pm = thistime.replace(hour=18, minute=0, second=0, microsecond=0)
				if thistime<sameday6pm:
					morning_count+=1
					if morning_count==1:
						morning_store=thisstore						
				else:
					evening_count+=1
					if evening_count==1:
						evening_store=thisstore						
			if morning_count>=evening_count:
				morning_users.append(thisuser)
				if morning_store==4:
					morning_store=2
				morning_store_users[morning_store].append(thisuser)
			else:
				evening_users.append(thisuser)
				if evening_store==4:
					evening_store=2
				evening_store_users[evening_store].append(thisuser)


		# create 8 segments

		# try:
		# 	m = Mailchimp(mailchimpkey)
		# 	mcresponse = m.lists.static_segment_add(list_id,"Morning Users")
		# 	print("Morning Users",mcresponse)
		# 	mcresponse = m.lists.static_segment_add(list_id,"Morning Users - CC")
		# 	print("Morning Users - CC",mcresponse)
		# 	mcresponse = m.lists.static_segment_add(list_id,"Morning Users - 46")
		# 	print("Morning Users - 46",mcresponse)
		# 	mcresponse = m.lists.static_segment_add(list_id,"Morning Users - KKJ")
		# 	print("Morning Users - KKJ",mcresponse)
		# 	mcresponse = m.lists.static_segment_add(list_id,"Evening Users")
		# 	print("Evening Users",mcresponse)
		# 	mcresponse = m.lists.static_segment_add(list_id,"Evening Users - CC")
		# 	print("Evening Users - CC",mcresponse)
		# 	mcresponse = m.lists.static_segment_add(list_id,"Evening Users - 46")
		# 	print("Evening Users - 46",mcresponse)
		# 	mcresponse = m.lists.static_segment_add(list_id,"Evening Users - KKJ")
		# 	print("Evening Users - KKJ",mcresponse)

			# environment_production==True:
				# Morning Users {'id': 60413}
				# Morning Users - CC {'id': 60417}
				# Morning Users - 46 {'id': 60421}
				# Morning Users - KKJ {'id': 60425}
				# Evening Users {'id': 60429}
				# Evening Users - CC {'id': 60433}
				# Evening Users - 46 {'id': 60437}
				# Evening Users - KKJ {'id': 60441}
			# environment_production==False:
				# Morning Users {'id': 60445}
				# Morning Users - CC {'id': 60449}
				# Morning Users - 46 {'id': 60453}
				# Morning Users - KKJ {'id': 60457}
				# Evening Users {'id': 60461}
				# Evening Users - CC {'id': 60465}
				# Evening Users - 46 {'id': 60469}
				# Evening Users - KKJ {'id': 60473}

		# except Exception as e:
		# 	print ("Unexpected error:",e)

		allUsersQuery = statssession.query(user.user_id, user.email)
		userEmailLookup = {}
		emailAlreadyAdded = {}
		for item in allUsersQuery:
			if (item[1] is not None) and len(item[1])>0:
				userEmailLookup[item[0]] = str(item[1]).lower()
				emailAlreadyAdded[userEmailLookup[item[0]]] = False

		morning_batch = []
		morning_cc_batch = []
		morning_46_batch = []
		morning_kkj_batch = []
		evening_batch = []
		evening_cc_batch = []
		evening_46_batch = []
		evening_kkj_batch = []

		for item in morning_users:
			if item in userEmailLookup:
				morning_batch.append({'email':userEmailLookup[item]})
				emailAlreadyAdded[userEmailLookup[item]] = True
		for item in morning_store_users[2]:
			if item in userEmailLookup:
				morning_cc_batch.append({'email':userEmailLookup[item]})
		for item in morning_store_users[3]:
			if item in userEmailLookup:
				morning_46_batch.append({'email':userEmailLookup[item]})
		for item in morning_store_users[5]:
			if item in userEmailLookup:
				morning_kkj_batch.append({'email':userEmailLookup[item]})

		for item in evening_users:
			if item in userEmailLookup:
				evening_batch.append({'email':userEmailLookup[item]})
				emailAlreadyAdded[userEmailLookup[item]] = True
		for item in evening_store_users[2]:
			if item in userEmailLookup:
				evening_cc_batch.append({'email':userEmailLookup[item]})
		for item in evening_store_users[3]:
			if item in userEmailLookup:
				evening_46_batch.append({'email':userEmailLookup[item]})
		for item in evening_store_users[5]:
			if item in userEmailLookup:
				evening_kkj_batch.append({'email':userEmailLookup[item]})

		for item in emailAlreadyAdded:
			if emailAlreadyAdded[item] == False:
				morning_batch.append({'email':item})
				morning_cc_batch.append({'email':item})
				emailAlreadyAdded[item] = True


		allSegments = ['morning', 'morning-cc', 'morning-46', 'morning-kkj', 'evening', 'evening-cc', 'evening-46', 'evening-kkj']
		allSegmentsMap = {thisSegment:{'id':-1,'batch':[]} for thisSegment in allSegments}
		if environment_production==True:
			allSegmentsMap = {'morning':{'id':60413,'batch':morning_batch}, 
								'morning-cc':{'id':60417,'batch':morning_cc_batch},
								'morning-46':{'id':60421,'batch':morning_46_batch},
								'morning-kkj':{'id':60425,'batch':morning_kkj_batch},
								'evening':{'id':60429,'batch':evening_batch},
								'evening-cc':{'id':60433,'batch':evening_cc_batch},
								'evening-46':{'id':60437,'batch':evening_46_batch},
								'evening-kkj':{'id':60441,'batch':evening_kkj_batch}
								}
		if environment_production==False:
			allSegmentsMap = {'morning':{'id':60445,'batch':morning_batch}, 
								'morning-cc':{'id':60449,'batch':morning_cc_batch},
								'morning-46':{'id':60453,'batch':morning_46_batch},
								'morning-kkj':{'id':60457,'batch':morning_kkj_batch},
								'evening':{'id':60461,'batch':evening_batch},
								'evening-cc':{'id':60465,'batch':evening_cc_batch},
								'evening-46':{'id':60469,'batch':evening_46_batch},
								'evening-kkj':{'id':60473,'batch':evening_kkj_batch}
								}

		
		# reset 8 segments
		list_id = getMailChimpListId()
		for thissegment in allSegments:
			static_segment_id = allSegmentsMap[thissegment]['id']

			batch_list = [{'email':'***REMOVED***'}]
			if environment_production == True:
				batch_list = allSegmentsMap[thissegment]['batch']	

			print(thissegment)
			try:
				m = Mailchimp(mailchimpkey)
				mcresponse = m.lists.static_segment_reset(list_id,static_segment_id)
				print(mcresponse)
				mcresponse = m.lists.static_segment_members_add(list_id,static_segment_id,batch_list)
				print(mcresponse)
			except Exception as e:
				print ("Unexpected error:",e)

		statssession.remove()
		
		self.write({"action":True})
		



current_path = path.dirname(path.abspath(__file__))
static_path = path.join(current_path, "static")

application = tornado.web.Application([
	(r"/", LoginHandler),
	(r"/stats", StatsHandler),
	(r"/itemstats", ItemStatsHandler),
	#(r"/userstats", UserStatsHandler),
	(r"/storeitems", StoreItemsHandler),
	(r"/todaysmenu", TodayMenuHandler),
	(r"/discountanalysis", DiscountAnalysisHandler),
	(r"/updateActive", UpdateItemsActiveHandler),
	(r"/moveActive", MoveItemsHandler),
	(r"/updateQuantity", UpdateQuantityHandler),
	(r"/userstats", AnalyticsHandler),
	(r"/sendmail", SendMailHandler),
	(r"/getpreview", MailPreviewHandler),
	(r"/sendtomailchimp", MailchimpHandler),
	(r"/updatemailchimp", MailchimpUpdateHandler),
	(r"/sendtolazysignups", MailchimpLazySignupHandler),
	(r"/sendtodormantusers", MailchimpDormantUserHandler),
	(r"/sendadhoc", MailchimpAdhocMailHandler),
	(r"/couponuse", CouponHandler),
	(r"/feedbacks", FeedbackHandler),
	(r"/wastage", WastageHandler),
	(r"/getstoreitems", GetStoreItemsHandler),
	(r"/setdatewisestoremenu", SetDateWiseMenuHandler),
	(r"/deliveries", DeliveryHandler),
	(r"/latedeliveries", LateDeliveryHandler),
	(r"/alldeliveries", AllOrderTimeHandler),
	(r"/deliverystats", DeliveryStatsHandler),
	(r"/payments", PaymentStatsHandler),
	(r"/orderstats", OrderStatsHandler),
	(r"/customerstats", CustomerStatsHandler),
	(r"/resetsegments", ResetSegmentHandler),
	(r"/retention", RetentionHandler),
	(r"/dormantregulars", DormantRegularsHandler),
	(r"/deadregulars", DeadRegularsHandler),
	(r"/foodcost", FoodCostHandler),
	(r"/sectors", SectorsHandler),
	(r"/esseltest", EsselTestHandler),
	(r"/rewardstats", RewardStatsHandler),
	(r"/rewardleaderboard", RewardLeaderHandler),
	(r"/subscription", SubscriptionHandler),
	(r"/vanvaas", VanvaasHandler),
	(r"/vanvaas/update/", UpdateVanvaasHandler),
	(r"/vanvaas/(.*)", VanvaasViewHandler),
	(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': static_path})
], **settings)

if __name__ == "__main__":
	application.listen(8080)
	print ("Listening on port 8080")
	tornado.ioloop.IOLoop.instance().start()

