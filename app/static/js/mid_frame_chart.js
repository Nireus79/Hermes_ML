var options = {
          series: [
          {
          name: 'Momentum frame: ',
          type: 'candlestick',
          data: []
          },{
          name: 'Stochastic %D: ',
          type: 'line',
          data: []
          },{
          name: 'Stochastic %DS: ',
          type: 'line',
          data: []
          },{
          name: 'RSI: ',
          type: 'line',
          data: []
          }
          ],
          chart: {
          height: 230,
          type: 'line',
          stacked: false
        },
        title: {
          text: 'Momentum frame',
          align: 'left'
        },
        stroke: {
          width: [3, 1]
        },
        tooltip: {
          shared: true,
          custom: [function({seriesIndex, dataPointIndex, w}) {
            return w.globals.series[seriesIndex][dataPointIndex]
          }, function({ seriesIndex, dataPointIndex, w }) {
            var o = w.globals.seriesCandleO[seriesIndex][dataPointIndex]
            var h = w.globals.seriesCandleH[seriesIndex][dataPointIndex]
            var l = w.globals.seriesCandleL[seriesIndex][dataPointIndex]
            var c = w.globals.seriesCandleC[seriesIndex][dataPointIndex]
            return (
              ''
            )
          }]
        },
        xaxis: {
          type: 'datetime'
        }
        };

var mid_frame_chart = new ApexCharts(document.querySelector("#mid_frame_chart"), options);
mid_frame_chart.render();

var intervalID = setInterval(update_values, 1000);

function update_values() {
    $.getJSON($SCRIPT_ROOT + '/update',
        function(data_update) {
            mid_frame_chart.updateSeries([{
              name: 'Middle frame: ' + data_update.runningMidFrame,
              data: data_update.mid_chart_data
              },{
              name: 'Stochastic %D: ' + data_update.mid_d
              },{
              name: 'Stochastic %DS: ' + data_update.mid_ds
              },{
              name: 'RSI: ' + data_update.mid_rs
              }
            ])
        }
    );
};