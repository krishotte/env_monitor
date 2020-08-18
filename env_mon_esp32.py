import network
import utime
import machine
import uping
import bme280
import urequests
from m_file import uini
from machine import I2C, Pin, ADC
import json


class NetworkConnection:
    """
    manages network connectivity
    provide configuration file name on init
    """
    def __init__(self, config_file):
        self.sta_if = network.WLAN(network.STA_IF)
        print('network is active: ', self.sta_if.active())
        self.sta_if.active(True)
        self.ini = uini()
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        self.conf = self.ini.read(self.config_file)
        try:
            self.ssid = self.conf['ssid']
        except KeyError:
            self.ssid = ''
        try:
            self.passwd = self.conf['passwd']
        except:
            self.passwd = ''
        try:
            self.ipaddr = self.conf['ipaddr']
        except:
            self.ipaddr = ''
        try:
            self.gateway = self.conf['gateway']
        except:
            self.gateway = ''
        print('loaded config: ssid: ', self.ssid, ' passwd: ', self.passwd, ' ip address: ', self.ipaddr, ' gateway: ', self.gateway)

    def connect(self):
        """
        connects to AP
        assigns provided ip address to server
        """
        i = 0
        while i < 6 and self.sta_if.isconnected() == False:
            i += 1
            self.sta_if.connect(self.ssid, self.passwd)
            print('connecting... ', self.sta_if.isconnected(), ", stage: ", i)
            utime.sleep(3)
        print('is connected?: ', self.sta_if.isconnected())
        if self.sta_if.isconnected():
            self.sta_if.ifconfig((self.ipaddr,'255.255.255.0','192.168.0.1','192.168.0.1'))
            psig.duty(10)
        else:
            psig.duty(0)
        print('ifconfig: ', self.sta_if.ifconfig())
        # return sta_if.ifconfig()[0]

    def connect2(self):
        """
        connects to AP
        improved preferred connect method
        """
        self.sta_if.ifconfig((self.ipaddr, '255.255.255.0', self.gateway, self.gateway))
        self.sta_if.connect(self.ssid, self.passwd)
        utime.sleep(5)
        print('is connected? (sta_if): ', self.sta_if.isconnected())
        print('ifconfig: ', self.sta_if.ifconfig())
        check_conn = self.check_conn()
        print('network connected: ', check_conn)
        if check_conn:
            psig.duty(10)
        else:
            psig.duty(0)
        return check_conn

    def check_conn(self):
        """
        checks network connection by pinging gateway
        uses uping.py
        """
        print('is connected? (sta_if): ', self.sta_if.isconnected())
        try:
            ping_status = uping.ping(self.gateway)
            if ping_status == (4, 4):
                conn_status = True
                print('ping: connected')
            else:
                conn_status = True
                print('ping: some packets lost')
        except OSError:
            print('ping: not connected')
            conn_status = False
        return conn_status

    def close(self):
        print('disconnecting network...')
        self.sta_if.disconnect()
        print('network connected: ', self.check_conn())
        psig.duty(0)


# global variables:
config = {
    'rst_threshold': 200,
    'pwm_freq': 5000,
    'deepsleep_period': 10000,
    'token': '',
    'device_label': 'demo',
    'batt_divider': 1,
    'batt_correction': 1,
    'batt_threshold': 3.2
}
config.update(uini().read("conf.json"))

pwm_freq = config['pwm_freq']
psig = machine.PWM(machine.Pin(2), freq=pwm_freq)
psig.duty(100)


def read_env_from_bme280():
    i2c = I2C(scl=Pin(5), sda=Pin(4), freq=400000)
    bme = bme280.BME280(i2c=i2c)

    bme.read_compensated_data()
    utime.sleep(1.5)

    t, p, h = bme.read_compensated_data()

    t = t / 100
    p = p / 25600
    h = h / 1024

    data = (t, p, h)
    return data


def read_battery_level(divider, correction):
    """
    reads battery voltage (V)
    :param divider: voltage divider value - full resistance / used resistance
    :param correction: multiplication factor
    :return:
    """
    adc = ADC(Pin(33))
    adc.atten(ADC.ATTN_11DB)    # voltage range(0, 3.6V)
    # adc.atten(ADC.ATTN_6DB)     # voltage range(0, 2V)
    adc.width(ADC.WIDTH_12BIT)  # 4096 levels

    raw_adc_value = adc.read()
    # voltage = raw_adc_value / 338 + 0.67  # calibrated for 470k/ 1M voltage divider
    voltage = raw_adc_value / 402 + 0.456
    voltage_corrected = voltage * correction

    return raw_adc_value, voltage, voltage_corrected


def write_data_to_ubidots(data):
    token = config['token']  # Put your TOKEN here
    device_label = config['device_label']  # Put your device label here
    """
    temperature = "temperature"  # Put your first variable label here
    pressure = "pressure"  # Put your second variable label here
    humidity = "humidity"
    """

    # url = "http://things.ubidots.com/api/v1.6/devices/{}".format(device_label)
    url = "http://192.168.0.14:5000/envdata"
    headers = {"X-Auth-Token": token, "Content-Type": "application/json"}
    """
    payload = {
        temperature: data[0],
        pressure: data[1],
        humidity: data[2]
    }
    """
    payload = data

    # Makes the HTTP requests
    status = 400
    attempts = 0
    while status >= 400 and attempts <= 5:
        req = urequests.post(url=url, headers=headers, json=payload)
        status = req.status_code
        attempts += 1
        req.close()
        utime.sleep(1)

    # Processes results
    if status >= 400:
        print("[ERROR] Could not send data after 5 attempts, please check \
                your token credentials and internet connection")
        return False

    print("[INFO] request made properly, your device is updated")
    return True


def main():
    battery = read_battery_level(config['batt_divider'], config['batt_correction'])
    print('battery voltage: ', battery)
    if battery[1] < config['batt_threshold']:
        print('!! BATTERY LEVEL LOW !!')

    net = NetworkConnection('conf.json')
    net_status = net.connect2()

    env = read_env_from_bme280()
    print('env: ', env)

    payload = {
        'temperature': env[0],
        'pressure': env[1],
        'humidity': env[2],
        'battery': battery[1]
    }
    try:
        write_data_to_ubidots(json.dumps(payload))
    except (ValueError, NotImplementedError):
        print('urequests error')
        psig.duty(100)
    except (IndexError, OSError):
        print('socket error')
        psig.duty(25)

    net.close()

    if battery[1] < config['batt_threshold']:
        machine.deepsleep(config['deepsleep_period'] * 300)
    else:
        machine.deepsleep(config['deepsleep_period'])


def test_batt():
    battery = read_battery_level(config['batt_divider'], config['batt_correction'])
    print('battery voltage: ', battery)
    if battery[1] < config['batt_threshold']:
        print('!! BATTERY LEVEL LOW !!')
    return battery


def test_batt_conti():
    while True:
        # psig.duty(100)
        # net = NetworkConnection('conf.json')
        #net_status = net.connect2()

        battery_voltage = test_batt()[1]
        """
        payload = {
            'battery': battery_voltage
        }
        try:
            write_data_to_ubidots(payload)
        except (ValueError, NotImplementedError):
            print('urequests error')
            psig.duty(100)
        except (IndexError, OSError):
            print('socket error')
            psig.duty(25)

        net.close()
        utime.sleep(8)
        """
        utime.sleep(1)
