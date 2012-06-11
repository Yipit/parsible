from socket import socket, AF_INET, SOCK_DGRAM
import time

hostname = "127.0.0.1"
port = 8125
udp = socket(AF_INET,SOCK_DGRAM)

def _send_statsd(data):
    udp.sendto(data, (hostname, port))

def output_print_line(line):
    print line

def output_statsd_timer(stat, metric_time):
    data = "{0}:{1}|ms".format(stat, metric_time)
    _send_statsd(data)

def output_statsd_count(stat, count=None):
    if count is None:
        count = 1
    data = "{0}:{1}|c".format(stat, count)
    _send_statsd(data)
