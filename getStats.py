import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean
    )
from sqlalchemy.orm.exc import NoResultFound
import datetime
from os import path
from json import dumps, loads
from urllib import parse
from mailchimp import Mailchimp
from re import sub

import tornado.ioloop
import tornado.web

import argparse

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools

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

def getTotalCount(parsedstartdate, parsedenddate, daterange, statssession):
	dailyorderscountquery = statssession.query(order.date_add, sqlalchemy.func.count(order.order_id)).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress)).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))

	thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): int(thisresult[1]) for thisresult in dailyorderscountquery}
	totalcount = []
	for thisdate in daterange:
		if thisdate in thiscountdetails:
			totalcount.append(thiscountdetails[thisdate])
		else:
			totalcount.append(0)

	return totalcount

def getOrderCounts(parsedstartdate, parsedenddate, dailyordersquery, daterange, statssession):
	firstorderquery = statssession.query(order).filter(sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress)).order_by(order.date_add).group_by(order.mobile_number)

	firstordersmap = {}
	for thisorder in firstorderquery:
		firstordersmap[thisorder.mobile_number] = thisorder.date_add.strftime("%c")

	ordercounts = {thisdate: {"new": 0, "old": 0} for thisdate in daterange}
	ordertotals = {thisdate: {"new": 0.0, "old": 0.0} for thisdate in daterange}

	platformcounts = {thisdate: {"Android": 0, "Web": 0, "iOS": 0} for thisdate in daterange}

	for thisorder in dailyordersquery:
		if thisorder.mobile_number in firstordersmap:
			if (thisorder.date_add.strftime("%c") == firstordersmap[thisorder.mobile_number]):
				ordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["new"] += 1
				ordertotals[thisorder.date_add.strftime("%a %b %d, %Y")]["new"] += float(thisorder.total)
			else:
				ordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["old"] += 1
				ordertotals[thisorder.date_add.strftime("%a %b %d, %Y")]["old"] += float(thisorder.total)
		
		if (thisorder.source == 0):
			platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["Android"] += 1
		elif (thisorder.source == 1):
			platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["Web"] += 1
		elif (thisorder.source ==2):
			platformcounts[thisorder.date_add.strftime("%a %b %d, %Y")]["iOS"] += 1

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

	androidorders = []
	weborders = []
	iosorders = []

	for thisdate in daterange:
		androidorders.append(platformcounts[thisdate]["Android"])
		weborders.append(platformcounts[thisdate]["Web"])
		iosorders.append(platformcounts[thisdate]["iOS"])

	result = {"neworders": neworders, "repeatorders": repeatorders, "totalneworders": totalneworders, "totalrepeatorders": totalrepeatorders, "newsums": newsums, "repeatsums": repeatsums, "androidorders": androidorders, "weborders": weborders, "iosorders": iosorders}
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

			parsedenddate = datetime.date.today()
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

		dailysalesquery = statssession.query(order.date_add, sqlalchemy.func.sum(order.total), sqlalchemy.func.sum(order.vat)).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status.in_(deliveredStates + inProgress)).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))

		totalsales = []

		thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[1]) for thisresult in dailysalesquery}
		for thisdate in daterange:
			if thisdate in thiscountdetails:
				totalsales.append(thiscountdetails[thisdate])
			else:
				totalsales.append(0)

		totalsalesvalue = sum(totalsales)

		totalcount = getTotalCount(parsedstartdate, parsedenddate, daterange, statssession)

		dailyordersquery = statssession.query(order).filter(sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate).all()

		detailedordercounts = getOrderCounts(parsedstartdate, parsedenddate, dailyordersquery, daterange, statssession)

		dailyorderids = [thisorder.order_id for thisorder in dailyordersquery]

		grosssalesquery = statssession.query(orderdetail.date_add, orderdetail.quantity, orderdetail.price).filter(orderdetail.order_id.in_(dailyorderids))
		grosssaleslookup = {}
		for grossdetail in grosssalesquery:
			if grossdetail.date_add.strftime("%a %b %d, %Y") in grosssaleslookup:
				grosssaleslookup[grossdetail.date_add.strftime("%a %b %d, %Y")] += (grossdetail.quantity*grossdetail.price)
			else:
				grosssaleslookup[grossdetail.date_add.strftime("%a %b %d, %Y")] = (grossdetail.quantity*grossdetail.price)

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
		self.render("templates/statstemplate.html", daterange=daterange, totalsales=totalsales, totalcount=totalcount, neworders=detailedordercounts["neworders"], repeatorders=detailedordercounts["repeatorders"], newsums=detailedordercounts["newsums"], repeatsums=detailedordercounts["repeatsums"], dailyapc=dailyapc, feedback_chart_data=feedback_chart_data, food_rating_counts=food_rating_counts, delivery_rating_counts=delivery_rating_counts, totalsalesvalue=totalsalesvalue, totalorders=totalorders, totalneworders=detailedordercounts["totalneworders"], totalrepeatorders=detailedordercounts["totalrepeatorders"], averageapc=averageapc, androidorders=detailedordercounts["androidorders"], weborders=detailedordercounts["weborders"], iosorders=detailedordercounts["iosorders"], grosssales = grosssales, totalgrosssales = totalgrosssales, netsalespretax = netsalespretax, totalnetsalespretax = totalnetsalespretax, user=current_user)

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
			current_store = self.get_argument("store", "All")
			
			if current_user == "chef03":
				current_store = [3]
			elif current_user == "chef":
				current_store = [2]
			else:
				if current_store == "All":
					current_store = [2,3]
				else:
					current_store = [int(current_store)]


			if startdate is None:
				if horizon is None:
					horizon = 7
				else:
					horizon = int(horizon)

				parsedenddate = datetime.date.today()
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

			dailyordersquery = statssession.query(order).filter(sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate, order.store_id.in_(current_store))

			dailyorderids = [thisorder.order_id for thisorder in dailyordersquery]
			dailyordersdatelookup = {thisorder.order_id: thisorder.date_add.strftime("%a %b %d, %Y") for thisorder in dailyordersquery}

			tags = statssession.query(tag).all()
			tagsmap = []

			for thistag in tags:
				relevantmenuitems = statssession.query(menu_item_tag.menu_item_id).filter(menu_item_tag.tag_id == thistag.tag_id)
				thiscountquery = statssession.query(orderdetail.date_add, sqlalchemy.func.sum(orderdetail.quantity), orderdetail.order_id).filter(orderdetail.order_id.in_(dailyorderids), orderdetail.menu_item_id.in_(relevantmenuitems)).group_by(sqlalchemy.func.year(orderdetail.date_add), sqlalchemy.func.month(orderdetail.date_add), sqlalchemy.func.day(orderdetail.date_add))
				thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): int(thisresult[1]) for thisresult in thiscountquery}
				thistaglist = []
				for thisdate in daterange:
					if thisdate in thiscountdetails:
						thistaglist.append(thiscountdetails[thisdate])
					else:
						thistaglist.append(0)

				tagsmap.append({"name": thistag.name, "data":thistaglist})
				

			menuitems = {thismenuitem.menu_item_id: {"name": thismenuitem.name, "total": 0, "datelookup": {thisdate: 0 for thisdate in daterange}} for thismenuitem in statssession.query(menuitem)}
			for suborder in statssession.query(orderdetail).filter(orderdetail.order_id.in_(dailyorderids)):
				menuitems[suborder.menu_item_id]["datelookup"][dailyordersdatelookup[suborder.order_id]] += suborder.quantity
				menuitems[suborder.menu_item_id]["total"] += suborder.quantity

			active_stores = statssession.query(store).filter(store.is_active == True).all()

			current_store_name = "All"
			for thisstore in active_stores:
				if [thisstore.store_id] == current_store:
					current_store_name = thisstore.name
					break

			itemhtml = "<table class='table table-striped table-hover tablesorter' style='width: 100%;'><thead><tr><th>Dish</th><th>Total</th>"
			for thisdate in daterange:
				itemhtml += "<th>" + thisdate + "</th>"

			itemhtml += "</tr><tbody>"
			for thismenuitem in menuitems:
				if menuitems[thismenuitem]["total"] == 0:
					continue
				itemhtml += "<tr><td style='font-weight: bold;'>" + menuitems[thismenuitem]["name"] + "</td>"
				itemhtml += "<td style='font-weight: bold;'>" + str(menuitems[thismenuitem]["total"]) + "</td>"
				for thisdate in daterange:
					if menuitems[thismenuitem]["datelookup"][thisdate] == 0:
						itemhtml += "<td>-</td>"
					else:
						itemhtml += "<td>" + str(menuitems[thismenuitem]["datelookup"][thisdate]) + "</td>"
				itemhtml += "</tr>"
			itemhtml += "</tbody></table>"

			statssession.remove()
			self.render("templates/itemstatstemplate.html", daterange=daterange, tagsmap=tagsmap, itemhtml=itemhtml, active_stores=active_stores, current_store=current_store, current_store_name=current_store_name, user=current_user)

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

				parsedenddate = datetime.date.today()
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

			dailyordersquery = statssession.query(order).filter(sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate)
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
	activelist = [{"name": menu_item_mapping[x.menu_item_id].name, "menu_item_id": x.menu_item_id, "store_menu_item_id": x.store_menu_item_id, "quantity": x.avl_quantity, "is_active": isActiveItem(x), "priority": x.priority, "image": menu_item_mapping[x.menu_item_id].img_url, "description": menu_item_mapping[x.menu_item_id].description} for x in store_items if isActiveItem(x)]
	inactivelist = [{"name": menu_item_mapping[x.menu_item_id].name, "menu_item_id": x.menu_item_id, "store_menu_item_id": x.store_menu_item_id, "quantity": x.avl_quantity, "is_active": isActiveItem(x), "priority": x.priority, "image": menu_item_mapping[x.menu_item_id].img_url, "description": menu_item_mapping[x.menu_item_id].description} for x in store_items if not isActiveItem(x)]
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

				parsedenddate = datetime.date.today()
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

			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))

			totalcount = getTotalCount(parsedstartdate, parsedenddate, daterange, statssession)

			dailyordersquery = statssession.query(order).filter(sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate).all()

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

			statssession.remove()

			self.render("templates/userstatstemplate.html", daterange=daterange, userslist=userslist, newuserslist=newuserslist, totalusers=totalusers, totalnewusers=totalnewusers, dailyconversion=dailyconversion, newconversion=newconversion, overallconversion=overallconversion, overallnewconversion=overallnewconversion, trafficdatatodisplay=dumps(trafficdatatodisplay), platformdatatoshow=dumps(platformdatatoshow), androidconversionseries=androidconversionseries, webconversionseries=webconversionseries, iosconversionseries=iosconversionseries, androidconversion=androidconversion, webconversion=webconversion, iosconversion=iosconversion, user=current_user)

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
		return "templates/mailtemplate2.html"
	elif (template == 3):
		return "templates/mailtemplate3.html"
	else:
		return "templates/mailtemplate.html"

class MailPreviewHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			subject = parse.unquote(self.get_argument("subject"))
			header = parse.unquote(self.get_argument("header"))
			length = int(self.get_argument("items"))
			itemlist = self.get_argument("itemlist")
			finallist = createMail(itemlist)
			sod = int(self.get_argument("sod", "-1"))
			dod = int(self.get_argument("dod", "-1"))
			template = int(self.get_argument("template", "1"))
			self.render(template_name = getMailTemplate(template), activeitems = finallist, header = header, length = length, sod=sod, dod=dod)

class MailchimpHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			current_store = 2
			activelist = getStoreItems(current_store)[0]
			subject = parse.unquote(self.get_argument("subject"))
			header = parse.unquote(self.get_argument("header"))
			length = int(self.get_argument("items"))
			itemlist = self.get_argument("itemlist")
			finallist = createMail(itemlist)
			sod = int(self.get_argument("sod", "-1"))
			dod = int(self.get_argument("dod", "-1"))
			template = int(self.get_argument("template", "1"))
			
			content = self.render_string(template_name = getMailTemplate(template), activeitems = finallist, header = header, length = length, sod=sod, dod=dod)

			#Change this variable to change the list
			list_id = "ea0d1e3356"
			# ea0d1e3356 is the main Twigly list
			#list_id = "d2a7019f47"
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

			parsedenddate = datetime.date.today()
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

		dailyordersquery = statssession.query(order).filter(sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status.in_(deliveredStates + deliveredFreeStates + inProgress), order.date_add <= parsedenddate, order.date_add >= parsedstartdate).all()

		#dailyorderids = [thisorder.order_id for thisorder in dailyordersquery]

		grosssales = []
		predictedsales = []
		wastage = []
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
			grosssalesquery = statssession.query(orderdetail.date_add, orderdetail.quantity, orderdetail.price, orderdetail.menu_item_id).filter(orderdetail.order_id.in_(thisstoreorders))
			
			grosssaleslookup = {}
			for grossdetail in grosssalesquery:
				if grossdetail.date_add.strftime("%a %b %d, %Y") in grosssaleslookup:
					grosssaleslookup[grossdetail.date_add.strftime("%a %b %d, %Y")] += (grossdetail.quantity*grossdetail.price)
				else:
					grosssaleslookup[grossdetail.date_add.strftime("%a %b %d, %Y")] = (grossdetail.quantity*grossdetail.price)

				if grossdetail.menu_item_id in peritemwastage[grossdetail.date_add.strftime("%a %b %d, %Y")]:
					peritemwastage[grossdetail.date_add.strftime("%a %b %d, %Y")][grossdetail.menu_item_id] -= grossdetail.quantity

			wastagelookup = {dr: 0 for dr in daterange}
			midlookup = {smi.menu_item_id: smi for smi in storeitemsquery if smi.store_id == thisstore.store_id}
			for dr in peritemwastage:
				for menuitemid in peritemwastage[dr]:
					if peritemwastage[dr][menuitemid] > 0:
						wastagelookup[dr] += (peritemwastage[dr][menuitemid]*midlookup[menuitemid].cost_price)

			thisgrosssales = []
			thispredictedsales = []
			thiswastage = []
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

			grosssales.append(thisgrosssales)
			predictedsales.append(thispredictedsales)
			wastage.append(thiswastage)
			stores.append({"store_id": thisstore.store_id, "name": thisstore.name, "grosssales": sum(thisgrosssales), "predictedsales": sum(thispredictedsales), "wastage": sum(thiswastage)})

		totalgrosssales = 0
		totalpredictedsales = 0
		totalwastage = 0
		companygrosssales = [0 for dr in daterange]
		companypredictedsales = [0 for dr in daterange]
		companywastage = [0 for dr in daterange]
		for i in range(len(stores)):
			totalgrosssales += stores[i]["grosssales"]
			totalpredictedsales += stores[i]["predictedsales"]
			totalwastage += stores[i]["wastage"]
		
			for j in range(len(daterange)):
				companygrosssales[j] += grosssales[i][j]
				companypredictedsales[j] += predictedsales[i][j]
				companywastage[j] += wastage[i][j]
		
		stores.insert(0, {"store_id": 0, "name": "Twigly", "grosssales": totalgrosssales, "predictedsales": totalpredictedsales, "wastage": totalwastage})
		grosssales.insert(0, companygrosssales)
		predictedsales.insert(0, companypredictedsales)
		wastage.insert(0, companywastage)
		statssession.remove()

		self.render("templates/wastagetemplate.html", daterange=daterange, grosssales=grosssales, predictedsales=predictedsales, wastage=wastage, stores=stores, numstores=len(stores), user=current_user)

class GetStoreItemsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		storeitems = statssession.query(storemenuitem).all()
		menuitems = statssession.query(menuitem).all()

		response = {"storeitems": [x.getJson() for x in storeitems], "menuitems": [y.getJson() for y in menuitems]}

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
	(r"/feedbacks", FeedbackHandler),
	(r"/wastage", WastageHandler),
	(r"/getstoreitems", GetStoreItemsHandler),
	(r"/setdatewisestoremenu", SetDateWiseMenuHandler),
	(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': static_path})
], **settings)

if __name__ == "__main__":
	application.listen(8080)
	print ("Listening on port 8080")
	tornado.ioloop.IOLoop.instance().start()

