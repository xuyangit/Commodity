#!/bin/bash
/usr/local/haproxy/sbin/haproxy -f /usr/local/haproxy/haproxy.cfg
cd /home/xuyang/Desktop/Commodity
python test.py &
python test1.py &