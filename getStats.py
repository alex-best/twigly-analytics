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
statsengine_url = 'mysql+pymysql://twigly:***REMOVED***@***REMOVED***/twigly_prod?charset=utf8'
statsengine = sqlalchemy.create_engine(statsengine_url)
statssession = scoped_session(sessionmaker(bind=statsengine))

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
		returnstring = "<style>td {padding: 10px;}</style>"
		todaydate = datetime.date.today()
		oneweekago = todaydate - datetime.timedelta(days=7)

		dailyordersquery = statssession.query(order).filter(order.date_add < todaydate, order.date_add >= oneweekago, sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status == 3)

		dailyorderids = [order.order_id for order in dailyordersquery]

		dailysalesquery = statssession.query(order.date_add, sqlalchemy.func.sum(order.total)).filter(order.date_add < todaydate, order.date_add >= oneweekago, sqlalchemy.not_(order.mobile_number.like("1%")), order.order_status == 3).group_by(sqlalchemy.func.year(order.date_add), sqlalchemy.func.month(order.date_add), sqlalchemy.func.day(order.date_add))

		returnstring += "Total sales: <br><table class='table-striped table-bordered table-hover'>"
		for sales in dailysalesquery:
			returnstring += "<tr><td>" + sales[0].strftime("%a %b %d, %Y") + "</td><td>" + str(sales[1]) + "</td></tr>"

		returnstring += ("</table><br><br>")

		tags = statssession.query(tag).all()

		for thistag in tags:
			returnstring += thistag.name + ": <br><table class='table-striped table-bordered table-hover'>"
			relevantmenuitems = statssession.query(menu_item_tag.menu_item_id).filter(menu_item_tag.tag_id == thistag.tag_id)
			thiscountquery = statssession.query(orderdetail.date_add, sqlalchemy.func.sum(orderdetail.quantity)).filter(orderdetail.date_add < todaydate, orderdetail.date_add >= oneweekago, orderdetail.order_id.in_(dailyorderids), orderdetail.menu_item_id.in_(relevantmenuitems)).group_by(sqlalchemy.func.year(orderdetail.date_add), sqlalchemy.func.month(orderdetail.date_add), sqlalchemy.func.day(orderdetail.date_add))
			for count in thiscountquery:
				returnstring += "<tr><td>" + count[0].strftime("%a %b %d, %Y") + "</td><td>" + str(count[1]) + "</td></tr>"
			returnstring += ("</table><br><br>")

		predefs = {"Combos": [41,42,47,48], "Minute Maid": [25], "Pasta": [10,11,13,14,18,19,26,37,45], "Sandwich": [5,7,8,9,12,15,22,32,35,36], "Cheese Cake": [30], "Carrot Cake": [31], "Pita (/3)": [28,29], "Apple Strudel": [46], "Blueberry Brainfreezer": [49]}

		predefitems = [cat for cat in predefs]

		for cat in predefitems:
			returnstring += cat + ": <br><table class='table-striped table-bordered table-hover'>"
			salecountquery = statssession.query(orderdetail.date_add, sqlalchemy.func.sum(orderdetail.quantity)).filter(orderdetail.date_add < todaydate, orderdetail.date_add >= oneweekago, orderdetail.order_id.in_(dailyorderids), orderdetail.menu_item_id.in_(predefs[cat])).group_by(sqlalchemy.func.year(orderdetail.date_add), sqlalchemy.func.month(orderdetail.date_add), sqlalchemy.func.day(orderdetail.date_add))
			for count in salecountquery:
				returnstring += "<tr><td>" + count[0].strftime("%a %b %d, %Y") + "</td><td>" + str(count[1]) + "</td></tr>"
			returnstring += ("</table><br><br>")
		self.render("templates/statstemplate.html", returnstring=returnstring)


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

