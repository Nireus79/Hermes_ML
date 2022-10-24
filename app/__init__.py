import os
import sys
from flask import Flask

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *x: None  # removes Flask server warning
    app = Flask(__name__, template_folder="templates", static_folder='static')

from app import routes
from app.back import kraken, bot
