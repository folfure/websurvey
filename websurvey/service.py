# -*- coding: utf-8 -*-
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template
import os
import json
import sqlite3
import time
import thread

TITLE = 'BIG BUZZ'
TEMPLATES = tornado.template.Loader("static/template")


class SurveyManager(object):
    TIMER_DURATION = 5  # time to answer a question in seconds

    def __init__(self, db_name):
        new_db = not os.path.exists(db_name)
        # sqlite3 database
        self.db_conn = sqlite3.connect(db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        # cursor for making queries to sql db
        self.cursor = self.db_conn.cursor()
        # map of player name to websocket {playerName: socketObject}
        self.sockets = dict()
        # websocket to screen display
        self.screens = []
        # admin web socket
        self.results = {}
        self.admin = None
        self.question_id = None
        self.questions = json.loads(open("questions.json").read())

        if new_db:
            print "creating db"
            with self.db_conn:
                self.cursor.execute(
                    "CREATE TABLE answer(question_id INTEGER, answer VARCHAR, response_time REAL)")
                print "db created"
        else:
            with self.db_conn:
                pass





    def add_screen(self, screen):
        self.screens.append(screen)

    def remove_screen(self, screen):
        self.screens.remove(screen)

    def set_admin(self):
        if self.admin:
            return 1
        else:
            self.admin = True
            return 0

    def set_admin_socket(self, socket):
        # what if self.admin is True ?
        if self.admin is None:
            self.admin = socket

    # Sets socket for player.
    def set_socket(self, socket, name):
        self.sockets[name] = socket
        socket.player = name

    def publish_players(self, type, **kwargs):
        for player in self.sockets:
            msg = dict(type=type)
            msg.update(kwargs)
            self.sockets[player].write_message(msg)
            return 0
        return 1

    def publish_admin(self, type, **kwargs):
        msg = dict(type=type)
        msg.update(kwargs)
        if self.admin and self.admin != True:
            print msg
            self.admin.write_message(msg)

    def publish_screen(self, type, **kwargs):
        msg = dict(type=type)
        msg.update(kwargs)
        for screen in self.screens:
            screen.write_message(msg)

    def socket_disconnected(self, player):
        self.sockets.pop(player)
        self.publish_admin(type='player_disconnected', name=player)

    def socket_admin_disconnected(self):
        self.admin = None

    def next_question(self):
        self.set_question((self.question_id + 1) % len(self.questions))

    def set_question(self, question_id):
        self.question_id = question_id
        self.publish_screen(type="question", **self.questions[self.question_id])
        self.publish_admin(type="question", **self.questions[self.question_id])
        self.publish_players(type="question", **self.questions[self.question_id])


    def __del__(self):
        self.db_conn.close()


IOLOOP = tornado.ioloop.IOLoop.instance()

SURVEY = SurveyManager(db_name="shadow_falcons_2017.db")


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

    @property
    def current_admin(self):
        return self.get_secure_cookie("admin")

    @current_admin.setter
    def current_admin(self, value):
        self.set_secure_cookie("admin", value)

    def logoff_user(self):
        if self.current_user:
            self.clear_cookie("user")

    def logoff_admin(self):
        if self.current_admin:
            self.clear_cookie("admin")


# Called when players connects to ipaddress. Either he never connects and he is redirected to /login.
# or he already connected and he is redirected to his buzz page.
class PlayerHandler(BaseHandler):
    def get(self, *args, **kwargs):
        print args, kwargs
        if not self.current_user:
            self.redirect('/login')
            print "redirecting login"
            return

        player = tornado.escape.xhtml_escape(self.current_user)
        if SURVEY.players.has_key(player):
            self.write(TEMPLATES.load("player.html").generate(player=player))
            self.finish()
        else:
            # shouldn't happen (user with cookie but not registered in the game...)
            self.clear_cookie("user")
            print "redirecting login"
            self.redirect('/login')


# Called when someone connects to ipaddress/admin
class AdminHandler(BaseHandler):
    def get(self, *args, **kwargs):
        print "AdminHandler.get : SURVEY admin", SURVEY.admin
        if not self.current_admin:
            self.redirect("/login/admin")
            return
        else:
            print(repr(self.request))
            SURVEY.socket_admin_disconnected()
            self.write(TEMPLATES.load("admin.html").generate(
                title=TITLE,
                questions=SURVEY.questions,
                question_id=SURVEY.question_id))
            self.finish()
            return


class WebSocketScreenHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        tornado.websocket.WebSocketHandler.__init__(self, *args, **kwargs)

    def open(self, *args, **kwargs):
        print("open", "WebSocketScreenHandler")
        SURVEY.add_screen(self)
        self.set_nodelay(True)

    def on_close(self):
        SURVEY.remove_screen(self)

    def send_msg(self, type, **kwargs):
        msg = dict(type=type)
        msg.update(kwargs)
        self.write_message(msg)


class HTMLQuizzHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(TEMPLATES.load("screen.html").generate(
            title=TITLE,
            scores=sorted(SURVEY.team_scores.values()),
            slide=SURVEY.quizz_screen.get_current_content()
        ))
        self.finish()


# Websocket to admin.
class WebSocketAdminHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        tornado.websocket.WebSocketHandler.__init__(self, *args, **kwargs)
        self.admin = None

    def open(self, *args, **kwargs):
        print("open", "WebSocketAdminHandler")
        SURVEY.set_admin_socket(self)
        self.set_nodelay(True)
        SURVEY.publish_admin(type='info', msg='websocket opened')

    def on_message(self, msg):
        if msg == "Keep alive":
            print msg, "admin"
            return
        msg = json.loads(msg)
        typ = msg['type']
        if typ == "go_to_question":
            print "go_to_question", msg
            SURVEY.set_question(question_id=msg['q_id'])
        elif typ == "next_question":
            print "next_question", msg
            SURVEY.next_question()
        elif typ == "next":
            print "next", msg
            SURVEY.next_slide()

    def on_close(self):
        print "WebSocketAdminHandler.on_close : SURVEY admin", SURVEY.admin
        SURVEY.socket_admin_disconnected()
        print "no more admin ? ", SURVEY.admin

    def send_msg(self, type, **kwargs):
        msg = dict(type=type)
        msg.update(kwargs)
        self.write_message(msg)


# Websocket to player.
class WebSocketBuzzHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):

        tornado.websocket.WebSocketHandler.__init__(self, *args, **kwargs)
        self.player = None

    def open(self, *args, **kwargs):
        print("open", "WebSocketPlayerHandler")
        playerName = self.get_argument('user')
        SURVEY.set_socket(self, playerName)
        self.set_nodelay(True)
        SURVEY.publish_player(playerName, type='info', msg='Reference Timestamp : %d' % SURVEY.reference_time_stamp)
        print playerName + " Just Connected."
        SURVEY.publish_all(type="info", msg="New Player Connected")
        SURVEY.check_status()

    def on_message(self, msg):
        if msg == "Keep alive":
            print msg, self.player
            return
        msg = json.loads(msg)
        if msg['type'] == 'answer':
            SURVEY.publish_admin(type='info', msg='%s answered %s to %s at %d' % (self.player, msg['answer'], msg['question'], msg['when']))
            SURVEY.handle_answer(self.player, int(msg['when']))

    def on_close(self):
        SURVEY.socket_disconnected(self.player)

    def send_msg(self, type, **kwargs):
        msg = dict(type=type)
        msg.update(kwargs)
        self.write_message(msg)


class LoginHandler(BaseHandler):
    def get(self,*args,**kwargs):
        params = self.request.arguments
        if params.has_key('logoff') :
            if '/admin' in args:
                self.logoff_admin()
                self.redirect('/login/admin')
            else:
                self.logoff_user()
                self.redirect('/login')
            return

        if '/admin' in args :
            print kwargs
            if self.current_admin :
                SURVEY.socket_admin_disconnected()
                self.redirect('/admin')
            else:
                self.write(TEMPLATES.load("login.html").generate(title=TITLE,
                            post_url='/login/admin', password_display='block', name_display='none'))
                self.finish()

        elif self.current_user:
            SURVEY.create_player(self.current_user)
            self.redirect('/')

        else:
            self.write(TEMPLATES.load("login.html").generate(title=TITLE,
                            post_url='/login', password_display='none', name_display='block'))
            self.finish()

    def post(self,*args,**kwargs):
        #to do secure
        if '/admin' in args:
            error = SURVEY.set_admin()
            if error:
                #to do add error div in all pages
                self.redirect('/login/admin?errid=5')
                return
            self.current_admin = '1'
            self.redirect('/admin')
        else:
            player=self.get_argument("name")
            self.set_secure_cookie("user", player)
            try:
                SURVEY.create_player(player)
                self.redirect('/')
            except Exception as e:
                print e, e.__class__
                print "couldn't add player %s"%(player)
                self.redirect('/login')



app = tornado.web.Application([
    (r'/', PlayerHandler),
    (r'/buzz', WebSocketBuzzHandler),
    (r'/adminws', WebSocketAdminHandler),
    (r'/screenws', WebSocketScreenHandler),
    (r'/login(.*)', LoginHandler),
    (r'/quizz', HTMLQuizzHandler),
    (r'/admin', AdminHandler),
    (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "static"})
],
    debug=True,
    cookie_secret="WOUHOUWCEQUIZZESTEXAGE"
)

app.listen(8083)
IOLOOP.start()



