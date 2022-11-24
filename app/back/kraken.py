from pykrakenapi import KrakenAPI
import krakenex
import requests
import urllib.parse
import hashlib
import hmac
import base64
from ta.momentum import rsi, stoch
from ta.trend import macd_diff
from ta.volatility import average_true_range
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import os
import time

api_url = "https://api.kraken.com"
api_key = os.environ['API_KEY_KRAKEN']
api_sec = os.environ['API_SEC_KRAKEN']

ml_cond = 'Sold'
buy_price = 0


def get_kraken_signature(url, data, secret):
    post_data = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + post_data).encode()
    message = url.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sig_digest = base64.b64encode(mac.digest())
    return sig_digest.decode()


def kraken_request(uri_path, data, key, sec):
    headers = {'API-Key': key, 'API-Sign': get_kraken_signature(uri_path, data, sec)}
    req = requests.post((api_url + uri_path), headers=headers, data=data)
    return req


def get_private_balance():
    resp = kraken_request('/0/private/Balance', {
        "nonce": str(int(1000 * time.time()))
    }, api_key, api_sec)
    return resp.json()


def get_condition(crypto_currency, fiat_currency, closing_price):
    """
    Takes the private user's account balance and gives condition to buy or sell to the bot.
    If balance has less crypto value than fiat returns condition "buy"
    for the bot to look for good crypto buy conditions.
    If balance has more crypto value than fiat returns condition "sell"
    for the bot to look for good crypto sell conditions.
    :return: Conditions to buy/sell crypto.
    """
    fiat_currency = 'Z' + fiat_currency
    balance = get_private_balance()
    crypto_balance = float(balance['result'][crypto_currency])
    crypto_value = crypto_balance * closing_price
    fiat_balance = float(balance['result'][fiat_currency])
    if crypto_value < fiat_balance:
        return 'buy', crypto_balance, fiat_balance
    elif crypto_value >= fiat_balance:
        return 'sell', crypto_balance, fiat_balance
    else:
        log = 'No balance found. Please select existing assets in your account.'
        print(log)


def add_order(ordertype, cond, vol, price, crypto_currency, fiat_currency):
    """
    https://support.kraken.com/hc/en-us/articles/360022839631-Open-Orders
    :param crypto_currency:
    :param fiat_currency:
    :param ordertype: market / limit
    :param cond: buy / sell
    :param vol: vol of fiat or crypto
    :param price: order price
    :return: order response
    """
    pair = crypto_currency + fiat_currency
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000 * time.time())),
        "ordertype": ordertype,
        "type": cond,
        "volume": vol,
        "pair": pair,
        "price": price
    }, key=api_key, sec=api_sec)
    return resp.json()


def cancel_order():
    """
    Cancel all orders
    :return:
    """
    resp = kraken_request('/0/private/CancelAll', {
        "nonce": str(int(1000 * time.time()))
    }, api_key, api_sec)
    """
    or cancel specific order (needs txid)
    resp = kraken_request('/0/private/CancelOrder', {
    "nonce": str(int(1000*time.time())),
    "txid": "OG5V2Y-RYKVL-DT3V3B" EXAMPLE!!! (Give txid as argument)
    }, api_key, api_sec)
    """
    return resp.json()


def get_order_info(txid):
    resp = kraken_request('/0/private/QueryOrders', {
        "nonce": str(int(1000 * time.time())),
        "txid": txid,
        "trades": True
    }, api_key, api_sec)
    return resp.json()


def time_stamp():
    """
    Takes unix time and gives datetime format.
    :return: Readable local datetime format.
    """
    curr_time = time.localtime()
    curr_clock = time.strftime("%Y-%m-%d %H:%M:%S", curr_time)
    return curr_clock


def check_flag_action(cb, cs, closing):
    global ml_cond, buy_price
    if cb and ml_cond == 'Sold':
        ml_cond = 'Bought'
        buy_price = closing
        return ml_cond, buy_price
    elif cs and ml_cond == 'Bought':
        ml_cond = 'Sold'
        sell_price = closing
        profit = sell_price - buy_price
        return ml_cond, sell_price, profit


def high_frame_indicators(df):
    """
    Takes a pandas dataframe provided by Kraken rest api containing ohlc data,
    adding columns to each row with the technical indicators of ohlc (EMA13, macd),
    using the "ta" library.
    Then after comparing the indicators of the last df row, is adding columns with triggers and buy/sell flags.
    : param hdf: raw api dataframe
    :return: hdf enriched with technical indicators and flags
    """
    hdf = df.copy()
    hdf['EMA13'] = hdf['close'].rolling(13).mean()
    hdf['macd'] = macd_diff(hdf['close'], window_slow=26, window_fast=12, window_sign=9, fillna=False)
    hdf['%K'] = stoch(hdf['high'], hdf['low'], hdf['close'], window=14, smooth_window=3, fillna=False)
    hdf['%D'] = hdf['%K'].rolling(3).mean()
    hdf['%DS'] = hdf['%D'].rolling(3).mean()  # Stochastic slow.
    hdf['negative momentum'] = hdf.apply(lambda x: x['%D'] < x['%DS'] < 80, axis=1)
    hdf['trend'] = hdf.apply(lambda x: x['close'] > x['EMA13'] and x['macd'] > 0, axis=1)
    return hdf


def mid_frame_indicators(df, max_rsi):
    """
    Takes a pandas dataframe provided by Kraken rest api containing ohlc data,
    adding columns to each row with the technical indicators of ohlc (stochastic %k, stochastic%d, rsi, %atr),
    using the "ta" library.
    : param mdf: raw api dataframe
    :return: mdf enriched with technical indicators and flags
    """
    mdf = df.copy()
    mdf['%K'] = stoch(mdf['high'], mdf['low'], mdf['close'], window=14, smooth_window=3, fillna=False)
    mdf['%D'] = mdf['%K'].rolling(3).mean()
    mdf['%DS'] = mdf['%D'].rolling(3).mean()  # Stochastic slow.
    mdf['rsi'] = rsi(mdf['close'], window=14, fillna=False)
    mdf['atr'] = average_true_range(mdf['high'], mdf['low'], mdf['close'], window=14, fillna=False)
    mdf['EMA13'] = mdf['close'].rolling(13).mean()
    mdf['macd'] = macd_diff(mdf['close'], window_slow=26, window_fast=12, window_sign=9, fillna=False)
    mdf['buy flag'] = mdf.apply(lambda x: x['%D'] > x['%DS'] > 20 and x['rsi'] < max_rsi, axis=1)
    mdf['sell flag'] = mdf.apply(lambda x: x['%D'] < x['%DS'] < 80, axis=1)
    mdf['sale'] = mdf.apply(lambda row: check_flag_action(row['buy flag'], row['sell flag'], row['close']),
                            axis=1).str[1]
    mdf['profit'] = mdf.apply(lambda row: check_flag_action(row['buy flag'], row['sell flag'], row['close']),
                              axis=1).str[2]
    mdf['prediction boolean'] = mdf.apply(lambda x: x['profit'] > 0, axis=1)
    return mdf


def low_frame_indicators(df):
    """
    Takes a pandas dataframe provided by Kraken rest api containing ohlc data,
    adding column to each row with the technical indicators of atr,
    using the "ta" library.
    :param df: low data frame
    :return: ldf enriched with atr
    """
    ldf = df.copy()
    ldf['atr'] = average_true_range(ldf['high'], ldf['low'], ldf['close'], window=14, fillna=False)
    return ldf


def prediction_model(df):
    pdf = df.copy()
    pdf.dropna(inplace=True)
    x = pdf.drop(columns=['prediction boolean', 'time', 'buy flag', 'sell flag', 'sale', 'profit', '%DS'])
    y = pdf['prediction boolean']
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.1)

    model = DecisionTreeClassifier()
    model.fit(x_train, y_train)

    open_tst = pdf.iloc[-1]['open']
    high = pdf.iloc[-1]['high']
    low = pdf.iloc[-1]['low']
    close = pdf.iloc[-1]['close']
    vwap = pdf.iloc[-1]['vwap']
    volume = pdf.iloc[-1]['volume']
    count = pdf.iloc[-1]['count']
    k = pdf.iloc[-1]['%K']
    d = pdf.iloc[-1]['%D']
    rs = pdf.iloc[-1]['rsi']
    atr = pdf.iloc[-1]['atr']
    m13 = pdf.iloc[-1]['EMA13']
    mac = pdf.iloc[-1]['macd']
    predictions = model.predict(x_test)
    score = accuracy_score(y_test, predictions)
    prediction = model.predict([[open_tst, high, low, close, vwap, volume, count, k, d, rs, atr, m13, mac]])
    # print(prediction, score)
    if prediction and score > 0.5:
        return prediction
    else:
        return False


def high_data(frame):
    """
        FOR USE IN APEXCHARTS
        Takes a pandas dataframe and creates a tuple of lists with
        the needed values for the apexcharts candle charts.
        Axis X values are all multiplied by 1000.
        JavaScript Date object however uses milliseconds since 1 January 1970 UTC.
        Therefore, you should multiply your timestamps by 1000 prior to assign the data to the chart configuration.
        :param frame: The modified pandas dataframe from high_frame_indicators.
        :return: json and last running indicators to be displayed.
    """
    front_df = frame.fillna(0)
    front_df['time'] = front_df['time'].apply(lambda x: (x * 1000) + 10800000)  # *1000 javascript time + 3hours
    data_list = front_df.values.tolist()
    candle_data = []
    ema13_data = []
    macd_data = round(data_list[-1][9], 4)
    for i in data_list:
        candle_data.append({
            'x': i[0],
            'y': [i[1], i[2], i[3], i[4]]
        })
    for i in data_list:
        if i[8] != 0:
            ema13_data.append({
                'x': i[0],
                'y': round(i[8], 4)
            })
    return candle_data, ema13_data, macd_data


def mid_data(frame):
    """
    Same as above (high) FOR USE IN APEXCHARTS
    """
    front_df = frame.fillna(0)
    front_df['time'] = front_df['time'].apply(lambda x: (x * 1000) + 10800000)
    data_list = front_df.values.tolist()
    candle_data = []
    stoch_d_data = round(data_list[-1][9], 4)
    stoch_ds_data = round(data_list[-1][10], 4)
    rsi_data = round(data_list[-1][11], 4)
    for i in data_list:
        candle_data.append({
            'x': i[0],
            'y': [i[1], i[2], i[3], i[4]]
        })
    return candle_data, stoch_d_data, stoch_ds_data, rsi_data


def low_data(frame):
    """
    Same as above (mid) FOR USE IN APEXCHARTS
    """
    front_df = frame.fillna(0)
    front_df['time'] = front_df['time'].apply(lambda x: (x * 1000) + 10800000)
    data_list = front_df.values.tolist()
    candle_data = []
    for i in data_list:
        candle_data.append({
            'x': i[0],
            'y': [i[1], i[2], i[3], i[4]]
        })
    return candle_data


class Api:
    """
    crypto: the name of crypto
    fiat: the name of monetary currency
    interval: candle in min
    frame_len: the length of frame (how many candles)
    """

    def __init__(self, crypto, fiat, interval, frame_len):
        self.frame_len = frame_len
        self.crypto = crypto
        self.fiat = fiat
        self.interval = interval  # candle in minutes
        self.pair = self.crypto + self.fiat
        self.candle = interval * 60  # candle in seconds
        self.last_candle = int(time.time()) - self.candle  # 1 candle in seconds
        self.frame = int(time.time()) - self.candle * self.frame_len
        self.key = os.environ['API_KEY_KRAKEN']
        self.sec = os.environ['API_SEC_KRAKEN']

    def get_frame(self):
        api = krakenex.API()
        k = KrakenAPI(api)
        ohlc, last = k.get_ohlc_data(self.pair, interval=self.interval, since=self.frame)
        return ohlc.iloc[::-1]  # reverse rows

# i24h = Api('DOT', 'EUR', 1440, 40)
# i4h = Api('DOT', 'EUR', 240, 40)
# i1h = Api('DOT', 'EUR', 60, 40)
# i15m = Api('DOT', 'EUR', 15, 40)
# i24h_frame = i24h.get_frame()
# i4h_frame = i4h.get_frame()
# i1h_frame = i1h.get_frame()
# i15m_frame = i15m.get_frame()
#
# f = mid_frame_indicators(i24h_frame, 70)
#
# print(f.to_string())
# # pr = prediction_model(fr)
# # print(pr)
