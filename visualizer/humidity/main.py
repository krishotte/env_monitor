import requests
import time
from os import path
from datetime import datetime, date
from bokeh.plotting import figure, output_file, show, ColumnDataSource, curdoc
from bokeh.models import HoverTool, DateRangeSlider, DateSlider, RangeSlider, CustomJS
from bokeh.layouts import column
from bokeh.driving import count
from m_file import ini2


output_file("humidity.html")

config_path = path.join(path.dirname(path.realpath(__file__)), 'conf.json')
config = ini2().read(config_path)
print(config)


def get_data_ubidots(verbose=None, from_ubidots=True):
    """
    downloads all humidity data from ubidots
    :return: source, source for view, initial graph state
    """
    if from_ubidots:
        url = "https://industrial.api.ubidots.com/api/v1.6/devices/{}/{}/values/?token={}&page_size={}".\
            format(config['device'], config['variable1'], config['token'], config['size'])
    else:
        # url = "http://192.168.0.14:5000/envdata"
        url = "http://10.147.20.112:5000/envdata"
    if verbose:
        print(url)

    request = requests.get(url)
    status = request.status_code
    if from_ubidots:
        json_data = request.json()['results']  # ["results"]
    else:
        json_data = request.json()

    print("status: ", status)
    print("downloaded data length: ", len(json_data))

    time1 = []
    value1 = []
    for each in json_data:
        if from_ubidots:
            time1.append(datetime.fromtimestamp(each['timestamp']//1000))
            value1.append(each['value'])
        else:
            time1.append(datetime.strptime(each[1], '%Y-%m-%dT%H:%M:%S.%fZ'))
            value1.append(each[3])

    if from_ubidots:
        time1.reverse()
        value1.reverse()

    print('first timestamp: ', time1[0], ' last timestamp: ', time1[-1])

    # initial graph data length
    initial_end = len(time1)-1
    if len(time1) > 2880:
        initial_start = initial_end - 2880
    else:
        initial_start = 0  # index1[0]
    initial_state = (initial_start, initial_end)

    # source = ColumnDataSource(data=dict(x=time1[:initial_end], y=value1[:initial_end], index=index1[:initial_end]))
    # source_orig = ColumnDataSource(data=dict(x=time1, y=value1, index=index1))
    source = ColumnDataSource(data=dict(x=time1[initial_start:], y=value1[initial_start:]))
    source_orig = ColumnDataSource(data=dict(x=time1, y=value1))

    return source_orig, source, initial_state


source_orig, source, initial_state = get_data_ubidots(verbose=1, from_ubidots=False)


def create_plot(verbose=None):
    """
    creates plot output to static HTML file
    :param verbose:
    :return: plot
    """
    p = figure(title="humidity@krishotte", x_axis_label='x', y_axis_label='y',
               #width=1600, height=800,
               x_axis_type="datetime")

    # add a line renderer with legend and line thickness
    p.line('x', 'y', legend='humidity', line_width=1, source=source)

    hover_tool = HoverTool(
        tooltips=[
            ('ts', '@x{%F %T}'),  # format timestamp
            ('value', '@y')
        ],
        formatters={
            'x': 'datetime',
            'value': 'printf',
        }
    )

    p.add_tools(hover_tool)
    p.sizing_mode = "stretch_both"

    return p


def slider2_callback_2(source=source, window=None, source2=source_orig):
    data = source2.data
    start1 = cb_obj.value[0]
    end1 = cb_obj.value[1]
    x = data['x']
    y = data['y']
    x = x[start1:end1]
    y = y[start1:end1]
    cb_obj.title = source2.data['x'][start1] + ",  " + str(source2.data['x'][end1])
    source.data = {'x': x, 'y': y}
    source.change.emit()


def create_slider(initial_state, verbose=None):
    """

    """
    slider2 = RangeSlider(
        start=0,
        end=len(source_orig.data['x']),
        value=(initial_state[0], initial_state[1]),
        step=1,
        title=str(source_orig.data['x'][initial_state[0]]) + ", " + str(source_orig.data['x'][initial_state[1]]),
        callback=CustomJS.from_py_func(slider2_callback_2)
    )
    # slider2.on_change('value', slider2_callback)
    return slider2


p = create_plot()
slider2 = create_slider(initial_state)
layout1 = column(p, slider2)
layout1.sizing_mode = "scale_width"


@count()
def update(t):
    last_data = get_new_data(from_ubidots=False)
    print('last data', last_data)

    print('last valid timestamp: ', source_orig.data['x'][-1])

    if last_data[0] > source_orig.data['x'][-1]:
        print('we have new data...')
        new_data = dict(x=[last_data[0]], y=[last_data[1]])
        print('new data: ', new_data)

        print('slider end: ', slider2.value[1], ' len data: ', len(source_orig.data['x']))

        print('slider size: ', slider2.value[1])
        slider2.end = slider2.end + 1

        if slider2.value[1] >= len(source_orig.data['x']) - 1:
            slider_selected_length = slider2.value[1] - slider2.value[0]

            slider2.value = (slider2.value[0] + 1, slider2.value[1] + 1)

            print('updating source.stream')
            source.stream(new_data)

        source_orig.stream(new_data)


def get_new_data(from_ubidots=True):
    if from_ubidots:
        url = "https://industrial.api.ubidots.com/api/v1.6/devices/{}/{}/values/?token={}&page_size={}". \
            format(config['device'], config['variable1'], config['token'], 2)
    else:
        # url = "http://192.168.0.14:5000/envdata-last"
        url = "http://10.147.20.112:5000/envdata-last"
    # print(url)

    request = requests.get(url)
    status = request.status_code
    # print("status: ", status)

    if from_ubidots:
        json_data = request.json()['results']  # ["results"]
    else:
        json_data = request.json()
    # print("data: ", json_data)

    if from_ubidots:
        last_timestamp = datetime.fromtimestamp(json_data[0]['timestamp'] // 1000)
        # print("last timestamp: ", last_timestamp)
        last_value = json_data[0]['value']
    else:
        last_timestamp = datetime.strptime(json_data[1], '%Y-%m-%dT%H:%M:%S.%fZ')
        last_value = json_data[4]

    return last_timestamp, last_value


# show the results
curdoc().add_root(layout1)
curdoc().add_periodic_callback(update, 4000)
curdoc().title = 'humidity'


if __name__ == "__main__":
    show(layout1)

    while True:
        # print('last data: ', get_new_data())
        update()
        time.sleep(5)
