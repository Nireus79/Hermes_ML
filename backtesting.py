import pandas as pd
from backtesting import Backtest
from ta.trend import macd_diff, sma_indicator
from ta.momentum import rsi, stoch
from ta.volatility import average_true_range
from backtesting import Strategy
from backtesting.lib import resample_apply
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np

ml_cond = 'Sold'
buy_price = 0

dt4h = pd.read_csv("ETHUSDT_4h.csv", index_col='Timestamp', parse_dates=True)
dt4h = dt4h[~dt4h.index.duplicated(keep='first')]

dt1h = pd.read_csv("ETHUSDT_1h.csv", index_col='Timestamp', parse_dates=True)
dt1h = dt1h[~dt1h.index.duplicated(keep='first')]

df15m = pd.read_csv("ETHUSDT_15m.csv", index_col='Timestamp', parse_dates=True)
df15m.drop(['Date', 'Time'], axis=1, inplace=True)
df15m = df15m[~df15m.index.duplicated(keep='first')]


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


def df_indicated(df):
    df['sma13'] = sma_indicator(df['Close'], 13)
    df['macd'] = macd_diff(df['Close'], window_slow=26, window_fast=12, window_sign=9, fillna=False)
    df['%K'] = stoch(df['High'], df['Low'], df['Close'], window=14, smooth_window=3, fillna=False)
    df['%D'] = sma_indicator(df['%K'], 3)
    df['%DS'] = sma_indicator(df['%D'], 3)
    df['rsi'] = rsi(df['Close'], window=14, fillna=False)
    df['atr'] = average_true_range(df['High'], df['Low'], df['Close'], window=14, fillna=False)

    df['buy flag'] = df.apply(lambda x: x['%D'] > x['%DS'] > 20 and x['rsi'] < 70, axis=1)
    df['sell flag'] = df.apply(lambda x: x['%D'] < x['%DS'] < 80, axis=1)
    df['sale'] = df.apply(lambda row: check_flag_action(row['buy flag'], row['sell flag'], row['Close']), axis=1).str[1]
    df['profit'] = df.apply(lambda row: check_flag_action(row['buy flag'], row['sell flag'], row['Close']),
                            axis=1).str[2]
    df['prediction boolean'] = df.apply(lambda x: x['profit'] > 0, axis=1)
    df = df.dropna().astype(float)
    return df


def k_wrapper(frame):
    return stoch(frame.High, frame.Low, frame.Close)


def atr_wrapper(frame):
    return average_true_range(frame.High, frame.Low, frame.Close)


class Hermes(Strategy):
    upper_bound = 80
    lower_bound = 20
    max_rsi = 70

    def init(self):
        high = self.data.High
        low = self.data.Low
        close = self.data.Close

        self.model = DecisionTreeClassifier()
        self.df1 = df_indicated(dt1h)
        self.df4 = df_indicated(dt4h)
        self.x1 = self.df1.drop(columns=['prediction boolean', 'buy flag', 'sell flag', 'sale', 'profit', '%DS']).values
        self.y1 = self.df1['prediction boolean'].values
        self.x4 = self.df4.drop(columns=['prediction boolean', 'buy flag', 'sell flag', 'sale', 'profit', '%DS']).values
        self.y4 = self.df4['prediction boolean'].values

        self.x1_train, self.x1_test, self.y1_train, self.y1_test = train_test_split(self.x1, self.y1, test_size=0.2)
        self.x4_train, self.x4_test, self.y4_train, self.y4_test = train_test_split(self.x4, self.y4, test_size=0.2)
        self.model1 = self.model.fit(self.x1_train, self.y1_train)
        self.model4 = self.model.fit(self.x4_train, self.y4_train)
        self.predictions1 = self.model1.predict(self.x1_test)
        self.score1 = accuracy_score(self.y1_test, self.predictions1)
        self.predictions4 = self.model4.predict(self.x4_test)
        self.score4 = accuracy_score(self.y4_test, self.predictions4)
        print('score1', self.score1, 'score4', self.score4)

        self.m15_sma13 = self.I(sma_indicator, pd.Series(close), 13, plot=False)
        self.m15_sma13[np.isnan(self.m15_sma13)] = 0
        self.m15_macd = self.I(macd_diff, pd.Series(close), plot=False)
        self.m15_macd[np.isnan(self.m15_macd)] = 0
        self.m15_k = self.I(k_wrapper, self.data.df, plot=False)
        self.m15_k[np.isnan(self.m15_k)] = 0
        self.m15_d = self.I(sma_indicator, pd.Series(self.m15_k), 3, plot=False)
        self.m15_d[np.isnan(self.m15_d)] = 0
        self.m15_ds = self.I(sma_indicator, pd.Series(self.m15_d), 3, plot=False)  # %DS
        self.m15_ds[np.isnan(self.m15_ds)] = 0
        self.m15_rsi = resample_apply('1H', rsi, close, plot=False)
        self.m15_rsi[np.isnan(self.m15_rsi)] = 0
        self.m15_atr = self.I(atr_wrapper, self.data.df, plot=False)
        self.m15_lim = high + self.m15_atr
        self.m15_stop = low - self.m15_atr

        self.h1_sma13 = resample_apply('1H', sma_indicator, close, plot=False)
        self.h1_sma13[np.isnan(self.h1_sma13)] = 0
        self.h1_macd = resample_apply('1H', macd_diff, close, plot=False)
        self.h1_macd[np.isnan(self.h1_macd)] = 0
        self.h1_k = resample_apply('1H', k_wrapper, self.data.df, plot=False)
        self.h1_k[np.isnan(self.h1_k)] = 0
        self.h1_d = self.I(sma_indicator, pd.Series(self.h1_k), 3, plot=False)  # %D
        self.h1_d[np.isnan(self.h1_d)] = 0
        self.h1_ds = self.I(sma_indicator, pd.Series(self.h1_d), 3, plot=False)  # %DS
        self.h1_ds[np.isnan(self.h1_ds)] = 0
        self.h1_rsi = resample_apply('1H', rsi, close, plot=False)
        self.h1_rsi[np.isnan(self.h1_rsi)] = 0
        self.h1_atr = resample_apply('1H', atr_wrapper, self.data.df, plot=False)
        self.h1_atr[np.isnan(self.h1_atr)] = 0
        self.h1_lim = high + self.h1_atr
        self.h1_stop = low - self.h1_atr
        self.h1_close = close

        self.h4_sma13 = resample_apply('4H', sma_indicator, close, plot=False)
        self.h4_sma13[np.isnan(self.h4_sma13)] = 0
        self.h4_macd = resample_apply('4H', macd_diff, close, plot=False)
        self.h4_macd[np.isnan(self.h4_macd)] = 0
        self.h4_k = resample_apply('4H', k_wrapper, self.data.df, plot=False)
        self.h4_k[np.isnan(self.h4_k)] = 0
        self.h4_d = self.I(sma_indicator, pd.Series(self.h4_k), 3, plot=False)  # %D
        self.h4_d[np.isnan(self.h4_d)] = 0
        self.h4_ds = self.I(sma_indicator, pd.Series(self.h4_d), 3, plot=False)  # %DS
        self.h4_ds[np.isnan(self.h4_ds)] = 0
        self.h4_rsi = resample_apply('4H', rsi, close, plot=False)
        self.h4_rsi[np.isnan(self.h4_rsi)] = 0
        self.h4_atr = resample_apply('4H', atr_wrapper, self.data.df, plot=False)
        self.h4_atr[np.isnan(self.h4_atr)] = 0

        self.day_sma13 = resample_apply('D', sma_indicator, close, plot=False)
        self.day_macd = resample_apply('D', macd_diff, close, plot=False)
        self.day_k = resample_apply('D', k_wrapper, self.data.df, plot=False)
        self.day_d = self.I(sma_indicator, pd.Series(self.day_k), 3, plot=False)  # %D
        self.day_ds = self.I(sma_indicator, pd.Series(self.day_d), 3, plot=False)  # %DS

        self.sma13_1 = (self.h1_sma13 + self.m15_sma13) / 2
        self.macd_1 = (self.h1_macd + self.m15_macd) / 2
        self.k_1 = (self.h1_k + self.m15_k) / 2
        self.d_1 = (self.h1_d + self.m15_d) / 2
        self.ds_1 = (self.h1_ds + self.m15_ds) / 2
        self.rsi_1 = (self.h1_rsi + self.m15_rsi) / 2
        self.atr_1 = (self.h1_atr + self.m15_atr) / 2
        self.buy_flag_1 = self.d_1 > self.ds_1 > self.lower_bound and self.rsi_1 < self.max_rsi
        self.sell_flag_1 = self.d_1 < self.ds_1 < self.upper_bound

        self.sma13_4 = (self.h4_sma13 + self.m15_sma13) / 2
        self.macd_4 = (self.h4_macd + self.m15_macd) / 2
        self.k_4 = (self.h4_k + self.m15_k) / 2
        self.d_4 = (self.h4_d + self.m15_d) / 2
        self.ds_4 = (self.h4_ds + self.m15_ds) / 2
        self.rsi_4 = (self.h4_rsi + self.m15_rsi) / 2
        self.atr_4 = (self.h4_atr + self.m15_atr) / 2
        self.buy_flag_4 = self.d_4 > self.ds_4 > self.lower_bound and self.rsi_4 < self.max_rsi
        self.sell_flag_4 = self.d_4 < self.ds_4 < self.upper_bound
        self.neg_mom_4 = self.d_4 < self.ds_4 < self.upper_bound
        self.trend_4 = close > self.sma13_4 and self.macd_4 > 0 and self.neg_mom_4 is not True

        self.buy_signal_4 = self.trend_4 and self.buy_flag_1
        self.sell_signal_4 = self.trend_4 and self.sell_flag_1

        self.sma13_24 = (self.day_sma13 + self.m15_sma13) / 2
        self.macd_24 = (self.day_macd + self.m15_macd) / 2
        self.k_24 = (self.day_k + self.m15_k) / 2
        self.d_24 = (self.day_d + self.m15_d) / 2
        self.ds_24 = (self.day_ds + self.m15_ds) / 2
        self.neg_mom_24 = self.d_24 < self.ds_24 < self.upper_bound
        self.trend_24 = close > self.sma13_24 and self.macd_24 > 0 and self.neg_mom_24 is not True

        self.buy_signal_24 = self.trend_24 and self.buy_flag_4
        self.sell_signal_24 = self.trend_24 and self.sell_flag_4

    def next(self):
        close = self.data.Close

        prediction4 = self.model4.predict([[self.data.Open[-1], self.data.High[-1], self.data.Low[-1],
                                            self.data.Close[-1], self.data.Volume[-1],
                                            self.k_4[-1], self.d_4[-1], self.rsi_4[-1], self.atr_4[-1],
                                            self.sma13_4[-1], self.macd_4[-1]]])
        prediction1 = self.model1.predict([[self.data.Open[-1], self.data.High[-1], self.data.Low[-1],
                                            self.data.Close[-1], self.data.Volume[-1],
                                            self.k_1[-1], self.d_1[-1], self.rsi_1[-1], self.atr_1[-1],
                                            self.sma13_1[-1], self.macd_1[-1]]])

        if self.buy_signal_24[-2] and prediction4 == 1 and self.h1_lim[-2] < self.h1_close[-1]:
            self.buy()
        elif self.buy_signal_4[-2] and prediction1 == 1 and self.m15_lim[-2] < close[-1]:
            self.buy()
        elif self.trend_24 is not True:
            self.position.close()
        elif self.trend_4 is not True:
            self.position.close()
        elif self.sell_signal_24[-2] and self.h1_stop[-2] > self.h1_close[-1]:
            self.position.close()
        elif self.sell_signal_4[-2] and self.m15_stop[-2] > close[-1]:
            self.position.close()


bt = Backtest(df15m, Hermes, cash=100000, commission=0.004, exclusive_orders=True)
output = bt.run()
print(output)
bt.plot(resample=False)
