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

import tornado.ioloop
import tornado.web

settings = {
    "cookie_secret": "twiglyrocks",
    "login_url": "/"
}
statsBase = declarative_base()
#statsengine_url = 'mysql+pymysql://twigly_ro:tw1gl7r0@***REMOVED***/twigly_prod?charset=utf8'
statsengine_url = 'mysql+pymysql://root@localhost:3306/twigly_dev?charset=utf8'

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

def authenticate(thisusername, thispassword):
	if (thisusername == "admin" and thispassword == "tw1gl7st4ts") or (thisusername == "review" and thispassword == "h1twigl7"):
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
		self.write(authresult)

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


		dailysalesquery = statssession.query(order.date_add, sqlalchemy.func.sum(order.total)).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status == 3).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))

		totalsales = []

		thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): float(thisresult[1]) for thisresult in dailysalesquery}
		for thisdate in daterange:
			if thisdate in thiscountdetails:
				totalsales.append(thiscountdetails[thisdate])
			else:
				totalsales.append(0)

		totalsalesvalue = sum(totalsales)

		dailyorderscountquery = statssession.query(order.date_add, sqlalchemy.func.count(order.order_id)).filter(order.date_add <= parsedenddate, order.date_add >= parsedstartdate, sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status == 3).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))


		thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): int(thisresult[1]) for thisresult in dailyorderscountquery}
		totalcount = []
		for thisdate in daterange:
			if thisdate in thiscountdetails:
				totalcount.append(thiscountdetails[thisdate])
			else:
				totalcount.append(0)

		dailyapc = []

		for c in range(len(daterange)):
			try: 
				dailyapc.append(totalsales[c]/totalcount[c])
			except ZeroDivisionError:
				dailyapc.append(0)

		firstorderquery = statssession.query(order).filter(sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status == 3).order_by(order.date_add).group_by(order.mobile_number)

		firstordersmap = {}
		for thisorder in firstorderquery:
			firstordersmap[thisorder.mobile_number] = thisorder.date_add.strftime("%c")

		ordercounts = {thisdate: {"new": 0, "old": 0} for thisdate in daterange}
		ordertotals = {thisdate: {"new": 0.0, "old": 0.0} for thisdate in daterange}

		dailyordersquery = statssession.query(order).filter(sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status == 3, order.date_add <= parsedenddate, order.date_add >= parsedstartdate)

		dailyorderids = [thisorder.order_id for thisorder in dailyordersquery]

		feedbackonorders = statssession.query(feedback).filter(feedback.order_id.in_(dailyorderids), sqlalchemy.or_(feedback.food_rating > 0, feedback.delivery_rating > 0)).all()

		totalorders = len(dailyorderids)

		try:
			averageapc = totalsalesvalue/totalorders
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

		platformcounts = {thisdate: {"Android": 0, "Web": 0, "iOS": 0} for thisdate in daterange}

		for thisorder in dailyordersquery:
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

		statssession.remove()
		self.render("templates/statstemplate.html", daterange=daterange, totalsales=totalsales, totalcount=totalcount, neworders=neworders, repeatorders=repeatorders, newsums=newsums, repeatsums=repeatsums, dailyapc=dailyapc, feedback_chart_data=feedback_chart_data, food_rating_counts=food_rating_counts, delivery_rating_counts=delivery_rating_counts, totalsalesvalue=totalsalesvalue, totalorders=totalorders, totalneworders=totalneworders, totalrepeatorders=totalrepeatorders, averageapc=averageapc, androidorders=androidorders, weborders=weborders, iosorders=iosorders)

class ItemStatsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		relevantStates = [3,10,11,12]

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

			dailyordersquery = statssession.query(order).filter(sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status.in_(relevantStates), order.date_add <= parsedenddate, order.date_add >= parsedstartdate)

			dailyorderids = [thisorder.order_id for thisorder in dailyordersquery]

			tags = statssession.query(tag).all()
			tagsmap = []

			for thistag in tags:
				relevantmenuitems = statssession.query(menu_item_tag.menu_item_id).filter(menu_item_tag.tag_id == thistag.tag_id)
				thiscountquery = statssession.query(orderdetail.date_add, sqlalchemy.func.sum(orderdetail.quantity)).filter(orderdetail.date_add <= parsedenddate, orderdetail.date_add >= parsedstartdate, orderdetail.order_id.in_(dailyorderids), orderdetail.menu_item_id.in_(relevantmenuitems)).group_by(sqlalchemy.func.year(orderdetail.date_add), sqlalchemy.func.month(orderdetail.date_add), sqlalchemy.func.day(orderdetail.date_add))
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
				menuitems[suborder.menu_item_id]["datelookup"][suborder.date_add.strftime("%a %b %d, %Y")] += suborder.quantity
				menuitems[suborder.menu_item_id]["total"] += suborder.quantity

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
			self.render("templates/itemstatstemplate.html", daterange=daterange, tagsmap=tagsmap, itemhtml=itemhtml)

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

			dailyordersquery = statssession.query(order).filter(sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status, order.date_add <= parsedenddate, order.date_add >= parsedstartdate)
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
			self.render("templates/userstemplate.html", daterange=daterange, lossmakers=lossmakers, med1makers=med1makers, med2makers=med2makers, med3makers=med3makers, highmakers=highmakers, counter1=counter1, counter2=counter2, counter3=counter3, counter4=counter4, counter5=counter5, users=users, lossmakerids=lossmakerids)

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

class StoreItemsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		current_user = self.get_current_user().decode()
		if current_user != "admin":
			self.redirect('/stats')
		else:
			statsengine = sqlalchemy.create_engine(statsengine_url)
			statssession = scoped_session(sessionmaker(bind=statsengine))

			store_items = statssession.query(storemenuitem).all()
			menu_items = statssession.query(menuitem).all()
			menu_item_mapping = {thismenuitem.menu_item_id: thismenuitem for thismenuitem in menu_items}
			store_items.sort(key=lambda x: (-x.is_active, -x.priority))
			activelist = [{"name": menu_item_mapping[x.menu_item_id].name, "menu_item_id": x.menu_item_id, "store_menu_item_id": x.store_menu_item_id, "quantity": x.avl_quantity, "is_active": x.is_active, "priority": x.priority} for x in store_items if x.is_active]
			inactivelist = [{"name": menu_item_mapping[x.menu_item_id].name, "menu_item_id": x.menu_item_id, "store_menu_item_id": x.store_menu_item_id, "quantity": x.avl_quantity, "is_active": x.is_active, "priority": x.priority} for x in store_items if not x.is_active]
			self.render("templates/storeitems.html", activelist = activelist, inactivelist = inactivelist)
			statssession.remove()

class UpdateItemsActiveHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		store_menu_item_id = int(self.get_argument("store_menu_item_id"))
		status = self.get_argument("checked")

		statsengine = sqlalchemy.create_engine(statsengine_url)
		statssession = scoped_session(sessionmaker(bind=statsengine))

		store_items = statssession.query(storemenuitem).all()
		store_items.sort(key=lambda x: (-x.is_active, -x.priority))
		active_store_items = []
		inactive_store_items = []
		selected_menu_item = None
		for store_item in store_items:
			if (store_item.store_menu_item_id == store_menu_item_id):
				selected_menu_item = store_item
			elif store_item.is_active:
				active_store_items.append(store_item)
			else:
				inactive_store_items.append(store_item)

		if status == "true":
			selected_menu_item.is_active = 1
			selected_menu_item.priority = len(active_store_items)+1
		else:
			selected_menu_item.is_active = 0
			selected_menu_item.priority = len(inactive_store_items)+1
		
		for i in range(0, len(active_store_items)):
			active_store_items[i].priority = len(active_store_items) - i
		for i in range(0, len(inactive_store_items)):
			inactive_store_items[i].priority = len(inactive_store_items) - i

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

		store_items = statssession.query(storemenuitem).filter(storemenuitem.is_active == True).all()
		store_items.sort(key=lambda x: (-x.priority))
		finallist = [x for x in store_items if x.store_menu_item_id != store_menu_item_id]
		thisitem = [x for x in store_items if x.store_menu_item_id == store_menu_item_id][0]
		finallist.insert(index, thisitem)
		
		for i in range(0, len(finallist)):
			finallist[i].priority = len(finallist) - i

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

current_path = path.dirname(path.abspath(__file__))
static_path = path.join(current_path, "static")

application = tornado.web.Application([
	(r"/", LoginHandler),
	(r"/stats", StatsHandler),
	(r"/itemstats", ItemStatsHandler),
	(r"/userstats", UserStatsHandler),
	(r"/storeitems", StoreItemsHandler),
	(r"/updateActive", UpdateItemsActiveHandler),
	(r"/moveActive", MoveItemsHandler),
	(r"/updateQuantity", UpdateQuantityHandler),
	(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': static_path})
], **settings)

if __name__ == "__main__":
	application.listen(8080)
	print ("Listening on port 8080")
	tornado.ioloop.IOLoop.instance().start()

