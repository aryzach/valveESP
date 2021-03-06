def wifiConnect():
    import network
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect('twistedfields', 'alwaysbekind')
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())

