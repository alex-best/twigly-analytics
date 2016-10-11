import facebook

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    TIMESTAMP
    )
import tornado.web
import datetime
from ast import literal_eval as le

facebook_app_id = "***REMOVED***"
facebook_app_secret = "***REMOVED***"

fbBase = declarative_base()
fbengine_url = 'mysql+pymysql://root:***REMOVED***@localhost/fb?charset=utf8'
fbengine = sqlalchemy.create_engine(fbengine_url)
fbsession = scoped_session(sessionmaker(bind=fbengine))

class fb_user(fbBase):
    __tablename__ = "fb_users"
    id = Column('id', String, primary_key=True)
    name = Column("name", String)
    profile_url = Column("profile_url", String)
    email = Column("email", String)
    access_token = Column("access_token", String)
    birthday = Column("birthday", Date)
    updated = Column("updated", TIMESTAMP)
    frienddata = Column("frienddata", String)

class FBBaseHandler(tornado.web.RequestHandler):
    """Implements authentication via the Facebook JavaScript SDK cookie."""
    def get_current_user(self):
        cookies = dict((n, self.cookies[n].value) for n in self.cookies.keys())
        cookie = facebook.get_user_from_cookie(
            cookies, facebook_app_id, facebook_app_secret)
        if not cookie:
            return None

        try:
            user = fbsession.query(fb_user).filter(fb_user.id == cookie["uid"]).one()
        except NoResultFound:
            user = None
        
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
            if "birthday" in profile:
                newUser.birthday = datetime.datetime.strptime(profile["birthday"], "%m/%d/%Y").date()
            fbsession.add(newUser)
            fbsession.commit()
        elif user.access_token != cookie["access_token"]:
            user.access_token = cookie["access_token"]
            fbsession.commit()
        
        return user

class VanvaasHandler(FBBaseHandler):
    def get(self):
        thisuser = self.get_current_user()
        reactionsresult = {}
        commentsresult = {}
        if thisuser:
            graph = facebook.GraphAPI(access_token=thisuser.access_token, version="2.7")
            posts = graph.get_object("me/posts?fields=object_id,message,story,comments.limit(999),reactions.limit(999)&limit=20me/posts?fields=object_id,message,story,comments.limit(999),reactions.limit(999)&limit=100")
            reactions = {}
            comments = {}
            lookup = {}
            if "data" in posts:
                for post in posts["data"]:
                    if "reactions" in post:
                        for reaction in post["reactions"]["data"]:
                            lookup[reaction["id"]] = reaction["name"]
                            if reaction["id"] in reactions:
                                reactions[reaction["id"]] += 1
                            else:
                                reactions[reaction["id"]] = 1
                    if "comments" in post:
                        for comment in post["comments"]["data"]:
                            lookup[comment["from"]["id"]] = comment["from"]["name"]
                            if comment["from"]["id"] in comments:
                                comments[comment["from"]["id"]] += 1
                            else:
                                comments[comment["from"]["id"]] = 1

            commentcharacters = [{"character": "Sugriv", "image": "v4.jpg", "description": "A great friend and always ready with their opinion"},{"character": "Jambavan", "image": "v5.jpg", "description": "You can always trust their advice"},{"character": "Vibhishan", "image": "v6.jpg", "description": "Always available when you need their opinion"}]
            reactioncharacters = [{"character": "Hanuman", "image": "v3.jpg", "description": "Fiercely loyal and happy to help"},{"character": "Laxman", "image": "v2.jpg", "description": "Viciously opinionated and quick to respond"},{"character": "Angad", "image": "v7.jpg", "description": "A bit hot headed but a true friend"}]

            commentslist = sorted([{"id": x, "count": comments[x], "name": lookup[x]} for x in comments], key=lambda x: -x["count"])
            
            commentslookup = [x["id"] for x in commentsresult]
            counter = 0
            commentsresult = []
            for comment in commentslist:
                if comment["id"] != thisuser.id:
                    comment["character"] = commentcharacters[counter]["character"]
                    comment["image"] = commentcharacters[counter]["image"]
                    comment["description"] = commentcharacters[counter]["description"]
                    commentsresult.append(comment)
                    counter += 1
                if counter == 3:
                    break

            reactionslist = sorted([{"id": x, "count": reactions[x], "name": lookup[x]} for x in reactions], key=lambda x: -x["count"])
            reactionsresult = []
            counter = 0
            for reaction in reactionslist:
                if reaction["id"] not in commentslookup and reaction["id"] != thisuser.id:
                    reaction["character"] = reactioncharacters[counter]["character"]
                    reaction["image"] = reactioncharacters[counter]["image"]
                    reaction["description"] = reactioncharacters[counter]["description"]
                    reactionsresult.append(reaction)
                    counter += 1
                if counter == 3:
                    break

            if (len(reactionsresult) > 0 or len(commentsresult) > 0):
                thisuser.frienddata = str({"reactionsresult": reactionsresult, "commentsresult": commentsresult})
                fbsession.commit()
        
        self.render("templates/fbexample.html", facebook_app_id=facebook_app_id, reactionsresult=reactionsresult, commentsresult=commentsresult, thisuser=thisuser, type="Your")

class VanvaasViewHandler(FBBaseHandler):
    def get(self, id):
        try:
            thisuser = fbsession.query(fb_user).filter(fb_user.id == id).one()
        except NoResultFound:
            self.write("Page not found - Please check the id given")
        else:
            resultdata = le(thisuser.frienddata)
            self.render("templates/fbexample.html", facebook_app_id=facebook_app_id, reactionsresult=resultdata["reactionsresult"], commentsresult=resultdata["commentsresult"], thisuser=thisuser, type="Their")