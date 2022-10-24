var intervalID = setInterval(update_values, 1000);

        function update_values() {
            $.getJSON($SCRIPT_ROOT + '/update',

          function(data) {

            $('#logs').html(data.logs);
            $('#trades').html(data.trades);

//            console.log(data)
          });
        };