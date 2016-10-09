import facebook

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    TIMESTAMP
    )
import tornado.web

facebook_app_id = "***REMOVED***"
facebook_app_secret = "***REMOVED***"

fbBase = declarative_base()
fbengine_url = 'mysql+pymysql://root:***REMOVED***@localhost/fb?charset=utf8'

class fb_user(fbBase):
    __tablename__ = "fb_users"
    id = Column('id', String, primary_key=True)
    name = Column("name", String)
    profile_url = Column("profile_url", String)
    email = Column("email", String)
    access_token = Column("access_token", String)
    birthday = Column("birthday", Date)
    updated = Column("updated", TIMESTAMP)

class FBBaseHandler(tornado.web.RequestHandler):
    """Implements authentication via the Facebook JavaScript SDK cookie."""
    def get_current_user(self):
        cookies = dict((n, self.cookies[n].value) for n in self.cookies.keys())
        cookie = facebook.get_user_from_cookie(
            cookies, facebook_app_id, facebook_app_secret)
        if not cookie:
            return None

        fbengine = sqlalchemy.create_engine(fbengine_url)
        fbsession = scoped_session(sessionmaker(bind=fbengine))
        user = fbsession.query(fb_user).filter(fb_user.id == cookie["uid"]).all()
        if not user:
            # TODO: Make this fetch async rather than blocking
            graph = facebook.GraphAPI(cookie["access_token"])
            profile = graph.get_object("me?fields=email,link,birthday,name")
            newUser = fb_user()
            newUser.id = profile["id"]
            newUser.name = profile["name"]
            newUser.profile_url = profile["link"]
            newUser.access_token = cookie["access_token"]
            newUser.email = profile["email"]
            newUser.birthday = profile["birthday"]
            fbsession.add(newUser)
            fbsession.commit()
        elif user.access_token != cookie["access_token"]:
            user.access_token = cookie["access_token"]
            fbsession.commit()
        return user

class VanvaasHandler(FBBaseHandler):
    def get(self):
        self.render("templates/fbexample.html", facebook_app_id=facebook_app_id)