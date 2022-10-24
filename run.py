import os
import sys
from app import app
import webbrowser

if sys.executable.endswith('pythonw.exe'):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.path.join(os.getenv('TEMP'), 'stderr-{}'.format(os.path.basename(sys.argv[0]))), "w")

if __name__ == '__main__':
    webbrowser.open_new('http://127.0.0.1:5000')
    app.run()
