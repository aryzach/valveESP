# This file is executed on every boot (including wake-boot from deepsleep)
import esp
import wifiConnect

esp.osdebug(None)
wifiConnect.wifiConnect()
#import webrepl
#webrepl.start()
