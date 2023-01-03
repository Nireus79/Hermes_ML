import logging
import time
import threading
import winsound
from app.back.kraken import Api, high_frame_indicators, mid_frame_indicators, low_frame_indicators, time_stamp, \
    add_order, cancel_order, get_condition, high_data, mid_data, low_data, prediction_model
from app.back.spring import check, activation

logging.basicConfig(level=logging.INFO)

condition = None
trend_24h = None
trend_4h = None
buy_flag_4h = False
buy_flag_1h = False
sell_flag_4h = None
sell_flag_1h = None
crypto_balance = None
fiat_balance = 0
limit = None
stop = None
closing_price = None

runningHighFrame = None
runningMidFrame = None
runningLowFrame = None
high_chart_data = None
mid_chart_data = None
low_chart_data = None
high_ema13 = None
high_macd = None
high_d = None
high_ds = None
mid_d = None
mid_ds = None
mid_rs = None
l_atr = None
low_limit = None
low_stop = None
log = 'Please set control parameters to start.'
logs = []
trades = []

break_event = threading.Event()


def signal_handler():
    """
    Setting exit event to allow process end
    within while loops before program stop.
    """
    break_event.set()


def beeper(cond):
    """
    Triggers sound signal user notifications on important trading events.
    :param cond: sell / buy / start (events)
    """
    if cond == 'buy':
        for _ in range(5):
            winsound.Beep(440, 500)
            time.sleep(0.5)
    elif cond == 'sell':
        for _ in range(5):
            winsound.Beep(1000, 500)
            time.sleep(0.1)
    elif cond == 'start':
        winsound.Beep(440, 2000)
    elif cond == 'break':
        winsound.Beep(240, 2000)


def chart_data(high_frame, mid_frame, low_frame):
    global high_chart_data, high_ema13, high_macd, high_d, high_ds, mid_chart_data, mid_d, mid_ds, mid_rs, \
        low_chart_data, low_limit, low_stop, l_atr
    limit_data = []
    stop_data = []
    high_candles, e13, mac = high_data(high_frame)
    mid_candles, d, ds, rs = mid_data(mid_frame)
    low_candles = low_data(low_frame)
    for i in low_candles:
        limit_data.append({
            'x': i['x'],
            'y': limit
        })
        stop_data.append({
            'x': i['x'],
            'y': stop
        })
    high_chart_data = high_candles[-20:]
    high_ema13 = e13[-20:]
    high_macd = mac
    mid_chart_data = mid_candles[-20:]
    mid_d = d
    mid_ds = ds
    mid_rs = rs
    low_chart_data = low_candles[-10:]
    low_limit = limit_data[-10:]
    low_stop = stop_data[-10:]


def order_manager(mode, high, mid, low, cond, crypto_currency, fiat_currency, max_rsi):
    """
    :param mode: limit / market
    :param max_rsi: maximum rsi in mid-frame
    :param crypto_currency: asset a
    :param fiat_currency: asset b
    :param high: high-frame instance
    :param mid: mid-frame instance
    :param low: low-frame instance
    :param cond: buy / sell
    When conditions to buy or sell are aligned in higher frames (buy or sell flag True)
    order_manager is setting limit and stop loss levels.
    Then starts monitoring periodically closing price at current running low time frame duration:
        When intending to buy asset
            if mid-frame momentum is strong:
                if closing price exceeds set limit level:
                    places a market buy order for the asset
                else: (closing price under limit)
                    if new closing price is lower than limit: (mid-frame momentum is still strong)
                        if new higher high of low frame is lower than previous:
                            sets new limit equal to new (lower) higher high.
                        else:
                            waits one low candle
            else:
                breaks to reevaluate conditions. (mid-frame momentum is not strong anymore)
        When intending to sell asset
            if mid-frame momentum is weak:
                if closing price is under stop level:
                    places market sell order for the asset.
                else: (closing price over stop-loss and mid-frame momentum is still weak)
                    if new closing price is higher than stop-loss:
                        if new lower low of low frame is higher than previous set:
                            sets new stop-loss equal to new (higher) lower-low.
                        else:
                            waits one low candle
            else:
                breaks to reevaluate conditions. (mid-frame momentum is not weak anymore)

    In stop-loss/limit levels an extra margin of current atr (average true range) is added,
    to include the volatility factor and limit false positioning.

    WARNING!!!
    When setting market order, volume must be set on the amount of the first asset.
    When setting buy order, vol = (money - money * max kraken fee) / crypto price
    When setting sell order, vol = crypto_balance (fee is calculated by kraken)
    """
    global condition, stop, limit, log, closing_price, runningLowFrame, crypto_balance, fiat_balance, l_atr
    beeper('start')
    log = '{} Order management. Setting {}min low frame {} limits.'.format(time_stamp(), low.interval, cond)
    logging.info(log)
    logs.append(log + '<br>')
    high_f = high_frame_indicators(high.get_frame())
    mid_f = mid_frame_indicators(mid.get_frame(), max_rsi)
    low_f = low_frame_indicators(low.get_frame())
    l_atr = low_f.iloc[-1]['atr']
    candle_time = low_f.iloc[-1]['time']
    if cond == 'buy':
        limit = low_f.iloc[-1]['high'] + l_atr
    elif cond == 'sell':
        stop = low_f.iloc[-1]['low'] - l_atr
    closing_price = low_f.iloc[-1]['close']
    log = 'Balance: {} {}. {} {}'.format(crypto_balance, crypto_currency, fiat_balance, fiat_currency)
    logging.info(log)
    logs.append(log + '<br>')
    log = '{} Current price: {}. limit: {}. Stop loss: {}'.format(time_stamp(), closing_price, limit, stop)
    logging.info(log)
    logs.append(log + '<br>')
    log = '{} Waiting until next {}min candle close.'.format(time_stamp(), low.interval)
    logging.info(log)
    logs.append(log + '<br>')
    chart_data(high_f, mid_f, low_f)
    time.sleep(60)
    while True:
        low_f = low_frame_indicators(low.get_frame())
        high_f = high_frame_indicators(high.get_frame())
        mid_f = mid_frame_indicators(mid.get_frame(), max_rsi)
        buy_flag = mid_f.iloc[-1]['buy flag']
        sell_flag = mid_f.iloc[-1]['sell flag']
        l_atr = low_f.iloc[-1]['atr']
        chart_data(high_f, mid_f, low_f)
        new_limit = low_f.iloc[-1]['high'] + l_atr
        new_stop = low_f.iloc[-1]['low'] - l_atr
        closing_price = low_f.iloc[-1]['close']
        new_candle_time = low_f.iloc[-1]['time']
        if break_event.is_set():  # thread "kill" by user
            cancel_order()
            log = '{} Break ordering.'.format(time_stamp())
            logging.info(log)
            logs.append(log + '<br>')
            break
        elif cond == 'buy':
            if buy_flag:
                if new_candle_time > candle_time + low.candle:  # wait one candle to close
                    if closing_price > limit:
                        asset_vol = (fiat_balance - fiat_balance * 0.0026) / closing_price
                        # kraken max trading fee: 0.0026 * asset_vol
                        log = '{} order to {} {} {} using {} {}.' \
                            .format(mode, cond, asset_vol, crypto_currency, fiat_balance, fiat_currency)
                        logging.info(log)
                        tx = add_order(mode, cond, asset_vol, closing_price, crypto_currency, fiat_currency)
                        log = tx
                        logging.info(log)
                        beeper(cond)
                        log = '{} Bought {} at: {}.'.format(time_stamp(), crypto_currency, closing_price)
                        trades.append(log + '<br>')
                        stop = None
                        limit = None
                        break
                    else:
                        candle_time = low_f.iloc[-2]['time']
                        if new_limit < limit:
                            limit = new_limit
                            log = '{} limit set to {}. Waiting until next {}min candle close.'\
                                .format(time_stamp(), limit, low.interval)
                            logging.info(log)
                            logs.append(log + '<br>')
                        else:
                            log = '{} Closing price under limit. Waiting until next {}min candle close.'\
                                .format(time_stamp(), low.interval)
                            logging.info(log)
                            logs.append(log + '<br>')
                else:
                    time.sleep(60)
            elif buy_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp())
                logging.info(log)
                logs.append(log + '<br>')
                beeper('break')
                time.sleep(10)
                limit = None
                stop = None
                break
        elif cond == 'sell':
            if sell_flag:
                if new_candle_time > candle_time + low.candle:  # wait one candle to close
                    if closing_price < stop:
                        log = '{} order to {} {} {} at {}.' \
                            .format(mode, cond, crypto_balance, crypto_currency, closing_price)
                        logging.info(log)
                        tx = add_order(mode, cond, crypto_balance, closing_price, crypto_currency, fiat_currency)
                        log = tx
                        logging.info(log)
                        beeper(cond)
                        log = '{} Sold {} at: {}.'.format(time_stamp(), crypto_currency, closing_price)
                        trades.append(log + '<br>')
                        limit = None
                        stop = None
                        break
                    else:
                        candle_time = low_f.iloc[-2]['time']
                        if new_stop > stop:
                            stop = new_stop
                            candle_time = low_f.iloc[-1]['time']
                            log = '{} Stop loss set to {}. Waiting until next {}min  candle close.'\
                                .format(time_stamp(), stop, low.interval)
                            logging.info(log)
                            logs.append(log + '<br>')
                        else:
                            log = '{} Closing price over stop. Waiting until next {}min candle close.'\
                                .format(time_stamp(), low.interval)
                            logging.info(log)
                            logs.append(log + '<br>')
                else:
                    time.sleep(60)
            elif sell_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp())
                logging.info(log)
                logs.append(log + '<br>')
                beeper('break')
                limit = None
                stop = None
                break


def limit_manager(mode, high, mid, low, cond, max_rsi):
    """
    Same as order_manager.
    No actual order is set. (Function is used in simulator and consulting mode.)
    User is just informed for the action he has to take.
    :param max_rsi: maximum rsi in mid-frame
    :param mode: simulation or consulting
    :param high: The high frame instance, used for chart data.
    :param mid: The middle frame instance, used to check if buy/sell flag is still True.
    :param low: The low frame instance, used to set limit/stop-loss borders.
    :param cond: Condition sell/buy
    """
    global condition, stop, limit, log, closing_price, runningLowFrame, l_atr
    beeper('start')
    log = '{} Limit management. Setting {}min low frame {} limits.'.format(time_stamp(), low.interval, cond)
    logging.info(log)
    logs.append(log + '<br>')
    high_f = high_frame_indicators(high.get_frame())
    mid_f = mid_frame_indicators(mid.get_frame(), max_rsi)
    low_f = low_frame_indicators(low.get_frame())
    l_atr = low_f.iloc[-1]['atr']
    limit = low_f.iloc[-1]['high'] + l_atr
    stop = low_f.iloc[-1]['low'] - l_atr
    closing_price = low_f.iloc[-1]['close']
    candle_time = low_f.iloc[-1]['time']
    log = '{} Current price {}. limit: {}. Stop loss: {}'.format(time_stamp(), closing_price, limit, stop)
    logging.info(log)
    logs.append(log + '<br>')
    if cond == 'buy':
        log = '{} Please wait 1 low candle time and give buy order if price exceeds {}. Wait {}min.' \
            .format(time_stamp(), limit, low.interval)
    elif cond == 'sell':
        log = '{} Please wait 1 low candle time and give sell order if price under {}. Wait {}min.' \
            .format(time_stamp(), stop, low.interval)
    logging.info(log)
    logs.append(log + '<br>')
    log = '{} Waiting until next {}min candle close.'.format(time_stamp(), low.interval)
    logging.info(log)
    logs.append(log + '<br>')
    chart_data(high_f, mid_f, low_f)
    time.sleep(low.candle)
    while True:
        high_f = high_frame_indicators(high.get_frame())
        mid_f = mid_frame_indicators(mid.get_frame(), max_rsi)
        low_f = low_frame_indicators(low.get_frame())
        buy_flag = mid_f.iloc[-1]['buy flag']
        sell_flag = mid_f.iloc[-1]['sell flag']
        l_atr = low_f.iloc[-1]['atr']
        new_limit = low_f.iloc[-1]['high'] + l_atr
        new_stop = low_f.iloc[-1]['low'] - l_atr
        closing_price = low_f.iloc[-1]['close']
        chart_data(high_f, mid_f, low_f)
        new_candle_time = low_f.iloc[-1]['time']
        if break_event.is_set():  # thread "kill" by user
            log = '{} Operation interrupted by user.'.format(time_stamp())
            logging.info(log)
            logs.append(log + '<br>')
            break
        elif cond == 'buy':
            if buy_flag:
                if new_candle_time > candle_time + low.candle:  # wait one candle to close
                    if closing_price > limit:
                        log = '{} Closing price exceeded limit. Please add buy order'.format(time_stamp())
                        logging.info(log)
                        logs.append(log + '<br>')
                        beeper(cond)
                        if mode == 'simulator':
                            logging.info('')
                            logs.append('<br>')
                            log = '{} Bought at: {}'.format(time_stamp(), closing_price)
                            logging.info(log)
                            logs.append(log + '<br>')
                            trades.append(log + '<br>')
                            condition = 'sell'
                        runningLowFrame = None
                        break
                    else:
                        candle_time = low_f.iloc[-2]['time']
                        if new_limit < limit:
                            limit = new_limit
                            stop = new_stop
                            log = '{} New limit set to {}. Waiting until next {}min candle close.'\
                                .format(time_stamp(), limit, low.interval)
                            logging.info(log)
                            logs.append(log + '<br>')
                        else:
                            log = '{} Closing price not exceeded limit. Waiting until next {}min candle close.'\
                                .format(time_stamp(), low.interval)
                            logging.info(log)
                            logs.append(log + '<br>')
                else:
                    time.sleep(60)
            else:
                log = '{} Conditions re-evaluation.'.format(time_stamp())
                logging.info(log)
                logs.append(log + '<br>')
                beeper('break')
                limit = None
                stop = None
                break
        elif cond == 'sell':
            if sell_flag:
                if new_candle_time > candle_time + low.candle:  # wait one candle to close
                    if closing_price < stop:
                        log = '{} Closing price under stop loss. Please add sell order' \
                            .format(time_stamp())
                        logging.info(log)
                        logs.append(log + '<br>')
                        beeper(cond)
                        if mode == 'simulator':
                            logging.info('')
                            logs.append('<br>')
                            log = '{} Sold at: {}'.format(time_stamp(), closing_price)
                            logging.info(log)
                            logs.append(log + '<br>')
                            trades.append(log + '<br>')
                            condition = 'buy'
                        limit = None
                        stop = None
                        break
                    else:
                        candle_time = low_f.iloc[-2]['time']
                        if new_stop > stop:
                            limit = new_limit
                            stop = new_stop
                            log = '{} New stop-loss set to {}. Waiting until next {}min candle close.'\
                                .format(time_stamp(), stop, low.interval)
                            logging.info(log)
                            logs.append(log + '<br>')
                        else:
                            log = '{} Closing price over stop-loss level. Waiting until next {}min candle close.'\
                                .format(time_stamp(), low.interval)
                            logging.info(log)
                            logs.append(log + '<br>')
                else:
                    time.sleep(60)
            elif sell_flag is not True:
                log = '{} Conditions re-evaluation.'.format(time_stamp())
                logging.info(log)
                logs.append(log + '<br>')
                beeper('break')
                limit = None
                stop = None
                break


def elderbot(mode, crypto_currency, fiat_currency, depth, max_rsi):
    """
    Custom, real time, multiple time frame, consulting-trading bot application,
    interpretation of Alexander Elder's "triple screen" forex market trading strategy.
    The strategy.
    The strategy is using data from three time frames, calculating indicators on first two and acts on the third.

    First frame used for establishing a trading bias.
    Second frame applies technical indicators to identify retracements against the trading bias established earlier.
    Third frame is used for timing entries using short-term breakouts in the direction of your trading bias.
    Program starts with higher degree time frame and subsequently downgrades time frames lower progressively.

    Frames combinations:
    Combination 1: High 24hours - mid 4 hours - low 1 hour.
    Combination 2: High 4 hours - mid 1 hour - low 15 min.

    Evaluation phases
    1) Trend. The long-term trend is evaluated. – Alex Elder calls this as being the tide, and it's evaluation gives
    the general trend direction.
    2) Correction. The medium-term trend is evaluated. – This trend is also known as the wave, gives the trend momentum
    strength and position.
    3) Specification. - The short-term trend – It is also referred to as the ripple used to set limits of buy and stop
    loss. Exact entry point is corrected by closely monitoring price movement.
    High frame.
    General trend can be detected with the use of 200 periods EMA, combination of 9, 20, 50 periods EMA, macd, etc.
    According to Elder the highly profitable spectrum of a positive trend is when price overcomes a pullback,
    entering the bullish zone.
    In our case a preset combination of 13p EMA and macd indicators (Closing > EMA13 and macd > 0)
    is used to determine the high frame trend.
    Mid-frame.
    Trend momentum and position is detected with the use of stochastic slow indicator. Stochastic fast can be used for
    quicker response but in this case more force signals are generated. Stochastic slow is used as it is a 'smothered'
    version of stoch fast. (d > ds > 20 buy Flag / d < ds < 80 sell Flag)
    An additional indicator of strength is added (RSI) as choice for safety reasons,
    as when current price strength is above safety, price is actually 'overbought' and probability of descent is high.
    Low frame.
    When conditions are aligned in the higher frames action limits are set, according to the last low frame
    closed candle range. Next candle price gives action flag or sets new limits.
    Low frame current candle ATR is added to the limit and subtracted to stop-loss, so current volatility
    of the price is taken into consideration to avoid false transactions.

    https://en.wikipedia.org/wiki/Alexander_Elder
    elder.com
    tradingstrategyguides.com
    www.elearnmarkets.com

    Original strategy dictates to wait the whole time of each candle to set condition flag,
        but as api provides data in real time, duration is divided optionally to make bot faster.
        Next, condition (get_condition()) is taken from users account balance (when in trading or consulting mode)
        and bot constantly evaluates the flags in a while loop.
        if condition is 'buy':
            if 24 hour high frame trend is positive (True trend flag):
                If 24 momentum (stochastic) is negative:
                    wait 5min.
                else:
                    if 4 hour mid-frame is strong (buy flag True):
                        if 4 hour prediction model gives possible profitable trade:
                            order_manager() evaluates to buy on 1 hour low frame.
                    elif 4 hour mid-frame conditions are NOT aligned:
                        if 4 hour high frame trend is positive:
                            if 1 hour momentum is strong and 4hour momentum is not weak:
                                if 1 hour prediction model gives possible profitable trade:
                                    order_manager() evaluates to buy on 15 min low frame.
                            elif 1 hour mid-frame conditions are NOT aligned:
                                sleep 5 minutes to review conditions.
            elif 4 hour high frame trend is positive ...same as above for lower frames (H4 M1 L15)...
            else: (conditions at all time frame combinations are not aligned)
                bot sleeps for 5 minutes to review conditions.
        elif condition is 'sell':
            if 24 hour high frame trend is positive:
                if 4 hour momentum is weak:
                    order_manager() kicks in to sell on 1 hour low frame.
                else:
                    waits 5min.
            elif 4 hour high-frame is positive:
                if 1 hour mid-frame is weak:
                    order_manager() kicks in to sell on 15 min low frame.
                else:
                    waits 5min.
            else: (all high frames trend is negative)
                order_manager() kicks in to sell on 15minute low frame.
    :param max_rsi: maximum rsi in mid-frame
    :param mode: trading / consulting
    :param crypto_currency: the crypto asset to be traded
    :param fiat_currency: the fiat asset to be traded
    :param depth: the time periods back to be analysed
    """
    global condition, log, trend_24h, trend_4h, buy_flag_4h, buy_flag_1h, sell_flag_4h, sell_flag_1h, \
        crypto_balance, fiat_balance, closing_price, runningHighFrame, runningMidFrame, runningLowFrame
    licence = check()['license_active']
    if licence:
        log = 'Your product licence is active. Thank you for using Hermes.'
        logging.info(log)
        logs.append(log + '<br>')
        if mode == 'simulator':
            condition = 'buy'
        i24h = Api(crypto_currency, fiat_currency, 1440, depth)
        i4h = Api(crypto_currency, fiat_currency, 240, depth)
        i1h = Api(crypto_currency, fiat_currency, 60, depth)
        i15m = Api(crypto_currency, fiat_currency, 15, depth)
        log = '{} Operation start. Mode is {}. Max RSI set to: {}.'.format(time_stamp(), mode, max_rsi)
        logging.info(log)
        logs.append(log + '<br>')
        while True:
            if break_event.is_set():  # thread "kill" by user
                cancel_order()
                log = '{} Breaking operation.'.format(time_stamp())
                logging.info(log)
                logs.append(log + '<br>')
                break
            i24h_frame = i24h.get_frame()
            i4h_frame = i4h.get_frame()
            i1h_frame = i1h.get_frame()
            i15m_frame = i15m.get_frame()
            high_frame_24h = high_frame_indicators(i24h_frame)
            high_frame_4h = high_frame_indicators(i4h_frame)
            mid_frame_4h = mid_frame_indicators(i4h_frame, max_rsi)
            mid_frame_1h = mid_frame_indicators(i1h_frame, max_rsi)
            closing_price = high_frame_24h.iloc[-1]['close']
            trend_24h = high_frame_24h.iloc[-1]['trend']
            trend_4h = high_frame_4h.iloc[-1]['trend']
            negative_momentum24h = high_frame_24h.iloc[-1]['negative momentum']
            negative_momentum4h = high_frame_4h.iloc[-1]['negative momentum']
            buy_flag_4h = mid_frame_4h.iloc[-1]['buy flag']
            sell_flag_4h = mid_frame_4h.iloc[-1]['sell flag']
            buy_flag_1h = mid_frame_1h.iloc[-1]['buy flag']
            sell_flag_1h = mid_frame_1h.iloc[-1]['sell flag']
            prediction4h = prediction_model(mid_frame_4h)
            prediction1h = prediction_model(mid_frame_1h)
            if mode == 'consulting' or mode == 'trading':
                condition, crypto_balance, fiat_balance = get_condition(crypto_currency, fiat_currency, closing_price)
            log = '{} Condition is {}.'.format(time_stamp(), condition)
            logging.info(log)
            logs.append(log + '<br>')
            if condition == 'buy':
                if trend_24h:
                    log = '{} 24hour trend is {}'.format(time_stamp(), trend_24h)
                    logging.info(log)
                    logs.append(log + '<br>')
                    runningHighFrame = '24Hour'
                    runningMidFrame = '4Hour'
                    runningLowFrame = '1Hour'
                    chart_data(high_frame_24h, mid_frame_4h, low_frame_indicators(i1h_frame))
                    if negative_momentum24h:
                        log = '{} 24hour momentum is weak. No buying opportunity. Wait 1 min.' \
                            .format(time_stamp())
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(60)
                    else:
                        if buy_flag_4h:
                            log = '{} 4hour momentum is {}. 4hour prediction is {}.'\
                                .format(time_stamp(), buy_flag_4h, prediction4h)
                            logging.info(log)
                            logs.append(log + '<br>')
                            if prediction4h:
                                if mode == 'trading':
                                    order_manager('market', i24h, i4h, i1h, condition,
                                                  crypto_currency, fiat_currency, max_rsi)
                                elif mode == 'consulting' or mode == 'simulator':
                                    limit_manager(mode, i24h, i4h, i1h, condition, max_rsi)
                            else:
                                log = '{} 4hour prediction is {}. Wait 1 min.'\
                                    .format(time_stamp(), prediction4h)
                                logging.info(log)
                                logs.append(log + '<br>')
                                time.sleep(60)
                        else:
                            log = '{} 4hour momentum is {}.'.format(time_stamp(), buy_flag_4h)
                            logging.info(log)
                            logs.append(log + '<br>')
                            if trend_4h:
                                log = '{} 4hour trend is {}.'.format(time_stamp(), trend_4h)
                                logging.info(log)
                                logs.append(log + '<br>')
                                runningHighFrame = '4Hour'
                                runningMidFrame = '1Hour'
                                runningLowFrame = '15minutes'
                                chart_data(high_frame_4h, mid_frame_1h, low_frame_indicators(i15m_frame))
                                if negative_momentum4h:
                                    log = '{} 4hour momentum is weak. No buying opportunity. Wait 1 min.' \
                                        .format(time_stamp())
                                    logging.info(log)
                                    logs.append(log + '<br>')
                                    time.sleep(60)
                                else:
                                    if buy_flag_1h:
                                        log = '{} 1hour momentum is {}.'.format(time_stamp(), buy_flag_1h)
                                        logging.info(log)
                                        logs.append(log + '<br>')
                                        if prediction1h:
                                            if mode == 'trading':
                                                order_manager('market', i4h, i1h, i15m, condition,
                                                              crypto_currency, fiat_currency, max_rsi)
                                            elif mode == 'consulting' or mode == 'zero':
                                                limit_manager(mode, i4h, i1h, i15m, condition, max_rsi)
                                        else:
                                            log = '{} 1hour prediction is {}. Wait 1 min.' \
                                                .format(time_stamp(), prediction1h)
                                            logging.info(log)
                                            logs.append(log + '<br>')
                                            time.sleep(60)
                                    else:
                                        log = '{} 1hour momentum is {}. Wait 1 min.' \
                                            .format(time_stamp(), buy_flag_1h)
                                        logging.info(log)
                                        logs.append(log + '<br>')
                                        time.sleep(60)
                            else:
                                log = '{} 4hour trend is {}. No buying opportunity. Wait 1 min.'\
                                    .format(time_stamp(), buy_flag_4h)
                                logging.info(log)
                                logs.append(log + '<br>')
                                time.sleep(60)
                elif trend_4h:
                    log = '{} 4hour trend is {}.'.format(time_stamp(), trend_4h)
                    logging.info(log)
                    logs.append(log + '<br>')
                    runningHighFrame = '4Hour'
                    runningMidFrame = '1Hour'
                    runningLowFrame = '15minutes'
                    chart_data(high_frame_4h, mid_frame_1h, low_frame_indicators(i15m_frame))
                    if negative_momentum4h:
                        log = '{} 4hour momentum is weak. No buying opportunity. Wait 1 min.' \
                            .format(time_stamp())
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(60)
                    else:
                        if buy_flag_1h:
                            log = '{} 1hour momentum is {}.'.format(time_stamp(), buy_flag_1h)
                            logging.info(log)
                            logs.append(log + '<br>')
                            if prediction1h:
                                if mode == 'trading':
                                    order_manager('market', i4h, i1h, i15m, condition,
                                                  crypto_currency, fiat_currency, max_rsi)
                                elif mode == 'consulting' or mode == 'simulator':
                                    limit_manager(mode, i4h, i1h, i15m, condition, max_rsi)
                            else:
                                log = '{} 1hour prediction is {}. Wait 1 min.' \
                                    .format(time_stamp(), prediction1h)
                                logging.info(log)
                                logs.append(log + '<br>')
                                time.sleep(60)
                        else:
                            log = '{} 1hour momentum is {}. Wait 1 min'.format(time_stamp(), buy_flag_1h)
                            logging.info(log)
                            logs.append(log + '<br>')
                            time.sleep(60)
                else:
                    log = '{} All trend frames negative. No buying opportunity. Wait 5 min.' \
                        .format(time_stamp())
                    logging.info(log)
                    logs.append(log + '<br>')
                    runningHighFrame = '4Hour'
                    runningMidFrame = '1Hour'
                    runningLowFrame = '15minutes'
                    chart_data(high_frame_4h, mid_frame_1h, low_frame_indicators(i15m_frame))
                    time.sleep(300)
            elif condition == 'sell':
                if trend_24h:
                    log = '{} 24hour trend is {}.'.format(time_stamp(), trend_24h)
                    logging.info(log)
                    logs.append(log + '<br>')
                    runningHighFrame = '24Hour'
                    runningMidFrame = '4Hour'
                    runningLowFrame = '1Hour'
                    chart_data(high_frame_24h, mid_frame_4h, low_frame_indicators(i1h_frame))
                    if sell_flag_4h:
                        log = '{} 4hour sell flag is {}.'.format(time_stamp(), sell_flag_4h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        if mode == 'trading':
                            order_manager('market', i24h, i4h, i1h, condition, crypto_currency, fiat_currency, max_rsi)
                        elif mode == 'consulting' or mode == 'simulator':
                            limit_manager(mode, i24h, i4h, i1h, condition, max_rsi)
                    else:
                        log = '{} 4hour sell flag is {}. Wait 1 minute.'.format(time_stamp(), sell_flag_4h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(60)
                elif trend_4h:
                    log = '{} 4hour trend is {}.'.format(time_stamp(), trend_4h)
                    logging.info(log)
                    logs.append(log + '<br>')
                    runningHighFrame = '4Hour'
                    runningMidFrame = '1Hour'
                    runningLowFrame = '15minutes'
                    chart_data(high_frame_4h, mid_frame_1h, low_frame_indicators(i15m_frame))
                    if sell_flag_1h:
                        log = '{} 1hour sell flag is {}.'.format(time_stamp(), sell_flag_1h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        if mode == 'trading':
                            order_manager('market', i4h, i1h, i15m, condition, crypto_currency, fiat_currency, max_rsi)
                        elif mode == 'consulting' or mode == 'simulator':
                            limit_manager(mode, i4h, i1h, i15m, condition, max_rsi)
                    else:
                        log = '{} 1hour sell flag is {}. Wait 1 minute.'.format(time_stamp(), sell_flag_1h)
                        logging.info(log)
                        logs.append(log + '<br>')
                        time.sleep(60)
                else:
                    log = '{} All high-frame trends are negative.'.format(time_stamp())
                    logging.info(log)
                    logs.append(log + '<br>')
                    runningHighFrame = '4Hour'
                    runningMidFrame = '1Hour'
                    runningLowFrame = '15minutes'
                    chart_data(high_frame_4h, mid_frame_1h, low_frame_indicators(i15m_frame))
                    if mode == 'trading':
                        order_manager('market', i4h, i1h, i15m, condition, crypto_currency, fiat_currency, max_rsi)
                    elif mode == 'consulting' or mode == 'simulator':
                        limit_manager(mode, i4h, i1h, i15m, condition, max_rsi)
    else:
        activation()
        log = 'Your product licence is not active. Please activate or contact technical support. ' \
              'Hermes_algotrading@proton.me'
        logging.info(log)
        logs.append(log + '<br>')
        exit()


def data_feed():
    if len(logs) > 300:
        del logs[:len(logs) - 299]
    return {
        'log': log,
        'logs': logs,
        'trades': trades,
        'condition': condition,
        'crypto_balance': crypto_balance,
        'fiat_balance': fiat_balance,
        'runningHighFrame': runningHighFrame,
        'runningMidFrame': runningMidFrame,
        'runningLowFrame': runningLowFrame,
        'trend_24h': str(trend_24h),
        'trend_4h': str(trend_4h),
        'buy_flag_4h': str(buy_flag_4h),
        'sell_flag_4h': str(sell_flag_4h),
        'buy_flag_1h': str(buy_flag_1h),
        'sell_flag_1h': str(sell_flag_1h),
        'high_chart_data': high_chart_data,
        'mid_chart_data': mid_chart_data,
        'high_ema13': high_ema13,
        'high_macd': high_macd,
        'mid_d': mid_d,
        'mid_ds': mid_ds,
        'mid_rs': mid_rs,
        'low_chart_data': low_chart_data,
        'price': closing_price,
        'l_atr': l_atr,
        'low_limit': low_limit,
        'low_stop': low_stop
    }
