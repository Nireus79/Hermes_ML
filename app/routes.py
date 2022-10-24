import time
import threading
from app.back.bot import elderbot, data_feed, signal_handler
from app.back.kraken import cancel_order, time_stamp
from app import app
from flask import render_template, request, jsonify
import logging

# Default values given as preset
asset_a = None
asset_b = None
mode = None
rsi = 70

# Flask logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


@app.route('/')
@app.route('/home')
def main():
    return render_template('overview.html')


@app.route('/control', methods=['POST', 'GET'])
def control():
    global asset_a, asset_b, mode, rsi
    if request.method == 'POST':
        try:
            asset_a = request.form['assetA']
            asset_b = request.form['assetB']
            mode = request.form['mode']
            rsi = float(request.form['rsi'])
        except Exception as e:
            logging.info(e)
    else:
        render_template('control.html')
    return render_template('control.html')


@app.route('/manual')
def doc():
    return render_template('doc.html')


@app.route('/history')
def history():
    return render_template('history.html')


@app.route('/update', methods=['GET'])
def update():
    dt = data_feed()
    dt['current_time'] = time_stamp(time.time())
    dt['crypto_currency'] = asset_a
    dt['fiat_currency'] = asset_b
    dt['mode'] = mode
    dt['rsi'] = rsi
    return jsonify(dt)


@app.route('/start')
def starter():
    if mode is None:
        logging.info('Mode not set.')
        return render_template('control.html')
    elif asset_a is None or asset_b is None:
        logging.info('Set assets.')
        return render_template('control.html')
    elif rsi is None:
        logging.info('Set rsi.')
        return render_template('control.html')
    else:
        trading = threading.Thread(target=elderbot, args=(mode, asset_a, asset_b, 720, rsi))
        # minimum depth argument is 35 needed for technical indicators
        # maximum is 720, needed for machine learning analysis
        trading.daemon = True
        trading.start()
        return render_template('overview.html')


@app.route('/stop')
def stopper():
    signal_handler()
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return render_template('overview.html')


@app.route('/cancel')
def canceler():
    cancel_order()
    return render_template('overview.html')
