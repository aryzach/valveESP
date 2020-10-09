import time
from machine import Pin

led = Pin(2, Pin.OUT)



while True:
	if led.value():
		led.value(0)
                print('on')
	else:
		led.value(1)
                print('off')
	time.sleep_ms(250)
