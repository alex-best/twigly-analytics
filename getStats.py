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
statsengine_url = 'mysql+pymysql://twigly_ro:tw1gl7r0@***REMOVED***/twigly_prod?charset=utf8'

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

def authenticate(thisusername, thispassword):
	if (thisusername == "admin" and thispassword == "tw1gl7st4ts"):
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
			dailyapc.append(totalsales[c]/totalcount[c])

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

		averageapc = totalsalesvalue/totalorders

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

		for thisorder in dailyordersquery:
			if (thisorder.date_add.strftime("%c") == firstordersmap[thisorder.mobile_number]):
				ordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["new"] += 1
				ordertotals[thisorder.date_add.strftime("%a %b %d, %Y")]["new"] += float(thisorder.total)
			else:
				ordercounts[thisorder.date_add.strftime("%a %b %d, %Y")]["old"] += 1
				ordertotals[thisorder.date_add.strftime("%a %b %d, %Y")]["old"] += float(thisorder.total)

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
			

		predefs = {"Combos": [41,42,47,48], "Minute Maid": [25], "Pasta": [10,11,13,14,18,19,26,37,45], "Sandwich": [5,7,8,9,12,15,22,32,35,36], "Cheese Cake": [30], "Carrot Cake": [31], "Pita (/3)": [28,29], "Apple Strudel": [46], "Blueberry Brainfreezer": [49]}

		predefitems = [cat for cat in predefs]

		inputsmap = []

		for cat in predefitems:
			salecountquery = statssession.query(orderdetail.date_add, sqlalchemy.func.sum(orderdetail.quantity)).filter(orderdetail.date_add <= parsedenddate, orderdetail.date_add >= parsedstartdate, orderdetail.order_id.in_(dailyorderids), orderdetail.menu_item_id.in_(predefs[cat])).group_by(sqlalchemy.func.year(orderdetail.date_add), sqlalchemy.func.month(orderdetail.date_add), sqlalchemy.func.day(orderdetail.date_add))
			
			thiscountdetails = {thisresult[0].strftime("%a %b %d, %Y"): int(thisresult[1]) for thisresult in salecountquery}
			thisinputslist = []
			for thisdate in daterange:
				if thisdate in thiscountdetails:
					thisinputslist.append(thiscountdetails[thisdate])
				else:
					thisinputslist.append(0)

			inputsmap.append({"name": cat, "data":thisinputslist})		

		statssession.remove()
		self.render("templates/statstemplate.html", daterange=daterange, totalsales=totalsales, totalcount=totalcount, neworders=neworders, repeatorders=repeatorders, tagsmap=tagsmap, inputsmap=inputsmap, newsums=newsums, repeatsums=repeatsums, dailyapc=dailyapc, feedback_chart_data=feedback_chart_data, food_rating_counts=food_rating_counts, delivery_rating_counts=delivery_rating_counts, totalsalesvalue=totalsalesvalue, totalorders=totalorders, totalneworders=totalneworders, totalrepeatorders=totalrepeatorders, averageapc=averageapc)


current_path = path.dirname(path.abspath(__file__))
static_path = path.join(current_path, "static")

application = tornado.web.Application([
	(r"/", LoginHandler),
	(r"/stats", StatsHandler),
	(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': static_path}),
], **settings)

if __name__ == "__main__":
	application.listen(8080)
	print ("Listening on port 8080")
	tornado.ioloop.IOLoop.instance().start()

