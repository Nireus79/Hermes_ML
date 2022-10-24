var intervalID = setInterval(update_values, 1000);
function update_values() {
    $.getJSON($SCRIPT_ROOT + '/update',
        function(data) {
                $('#current_time').text('Current time: '+data.current_time);
                $('#mode').text('Mode: '+data.mode);
                $('#rsi').text('Max RSI: '+data.rsi);
                $('#condition').text('Evaluating to '+data.condition+':');
                $('#crypto_currency').text(data.crypto_currency);
                $('#fiat_currency').text('for  '+data.fiat_currency);
                $('#crypto_balance').text('asset A: '+data.crypto_balance);
                $('#fiat_balance').text('asset B: '+data.fiat_balance);
                $('#trend_24h').text(data.trend_24h);
                $('#buy_flag_4h').text(data.buy_flag_4h);
                $('#sell_flag_4h').text(data.sell_flag_4h);
                $('#trend_4h').text(data.trend_4h);
                $('#buy_flag_1h').text(data.buy_flag_1h);
                $('#sell_flag_1h').text(data.sell_flag_1h);
                $('#price').text('Closing price: '+data.price);
                $('#limit').text('Buy limit: '+data.limit);
                $('#stop').text('Stop loss: '+data.stop);
                $('#log').text('Log: '+data.log);
        });
};