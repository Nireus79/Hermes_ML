Hermes
A custom real time, multiple time frame, consulting-trading bot application,
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
1) Trend. The long-term trend is evaluated. � Alex Elder calls this as being the tide, and it's evaluation gives the general trend direction.
2) Correction. The medium-term trend is evaluated. � This trend is also known as the wave, gives the trend momentum strength and position.
3) Specification. - The short-term trend � It is also referred to as the ripple used to set limits of buy and stop loss. Exact entry point is corrected by closely monitoring price movement.
High frame.
General trend can be detected with the use of 200 periods EMA, combination of 9, 20, 50 periods EMA, macd, etc. According to Elder the highly profitable spectrum of a positive trend is when price overcomes a pullback, entering the bullish zone.
In our case a preset combination of 13p EMA and macd indicators is used to determine the high frame trend.
Mid frame.
Trend momentum and position is detected with the use of stochastic slow indicator. Stochastic fast can be used for quicker response but in this case more force signals are generated. Stochastic slow is used as it is a 'smothered' version of stoch fast. An additional indicator of strength is added (RSI) as choice for safety reasons, as when current price strength is above safety, price is actually 'overbought' and probability of descent is high. An extra condition of %ATR is given as choice, to avoid false buy flags in price consolidation instances. ATR of middle frame is also subtracted by lowest low of last mid-candle, to be used as pillow and avoid false pillow alarm. If trend frame momentum (Stochastic) is negative, bot will not buy asset. Same rule does not apply when selling.
Low frame.
When conditions are aligned in the higher frames action limits are set, according to the last low frame closed candle range. Next time fragment of candle price gives action flag or sets new limits. Low frame current candle ATR is added to the limit and subtracted to stop-loss, so current volatility of the price is taken into consideration to avoid false transactions. Reevaluation of limits can be taken after a full low frame candle period or this period can be half, one fourth or one sixth of that time by user's choice.
Wiki/Elder, elder.com
Instructions.
Setting up your credentials:
(This process needs to be done only once.)
1) Go to kraken.com and log in or create a new account.
2) Then proceed to support: How to generate an API key pair
and follow instructions to create your personal API key, Secret Key and product licence key.
These are essential for your app operation. The app will use them access your account.
3) Carefully save your Api Key and secret. If you loose them you will have to generate new.
A. Proceed to your windows "Control panel".
B. Click on "System and security".
C. Navigate to "System" and "Advanced system settings".
D. Navigate to "Advanced" and "Environment variables".
E. Click "New" button under "User variables" window.
F. Type or paste API_KEY_KRAKEN on "Variable name" input field and your Api key on "Variable value" input field.
G. Repeat "E" step and
type or paste API_SEC_KRAKEN on "Variable name" input field and your Api secret key on "Variable value" input field.
Repeat for product licence key.
Now you have safely stored your credentials, and you can operate your app.
Operating your app:
A. Click "control" on nav bar field.
B. Select mode, assets pair and press submit button.
PLEASE BE SURE YOUR CHOICE IS SUPPORTED BEFORE YOU SUBMIT!!!
General info:
On "Simulator" mode, app ignores private balance and starts evaluating,
given pair of assets from willing to 'buy' position.
On "Consulting" mode app will only process data in real time and advice you
to manually place or cancel orders on your trading platform.
On "Trading" mode app will automatically place these orders.
The app is designed to operate in Windows systems.
Using Kraken trading platform to collect data and trade.
"Stop bot" button terminates the app operation after the completion
of current evaluation period.
Message appears on Overview when done.
"Cancel active order" has immediate effect.
In stop-loss/limit levels an extra margin of current atr (average true range) is added,
to include the volatility factor and limit false positioning.

FOR ANY ISSUES OR ADDITIONAL INFORMATION PLEASE CONTACT TECHNICAL SUPPORT Hermes_algotrading@proton.me