# Background Radiation Monitor

**A simple balenaCloud application to measure and record background radiation in your area. Radiation is detected with a cheaply available board, and connected to a Raspberry Pi to provide InfluxDB for datalogging and Grafana for pretty charts.**

![grafana-dashboard](https://raw.githubusercontent.com/balenalabs-incubator/background-radiation-monitor/master/assets/grafana-dashboard.png)

## Hardware required

* A Raspberry Pi (any model should be good for this, but I’d recommend a 3 or above just for performance reasons)
* An 8GB (or larger) SD card (we recommend SanDisk Extreme Pro SD cards)
* A power supply (PSU)
* A radiation detector [Amazon UK](https://www.amazon.co.uk/KKmoon-Assembled-Counter-Radiation-Detector/dp/B07S86Q5X8) or [AliExpress](https://www.aliexpress.com/item/32884861168.html?spm=a2g0o.productlist.0.0.5faf6aa9OuQXsc)
* Some [Dupont cables/jumper jerky](https://shop.pimoroni.com/products/jumper-jerky?variant=348491271) (you’ll need 3 female-female cables)


## Hardware connection

There are 3 connections we need to make from the radiation detector board to the Raspberry Pi. They are +5V and Ground (GND) for power, and the output pulse line to detect the count. Note that this is called `VIN` which can be a bit confusing as this usually means ‘voltage input’ or something similar, but on this board, it’s the output.

![pi-geiger-simple](https://raw.githubusercontent.com/balenalabs-incubator/background-radiation-monitor/master/assets/pi-geiger-simple.png)

In this configuration you only need to provide 5 volt power to one of the two boards; if you’re powering the Pi with a standard micro-USB power supply, that will power the detector board via the connections we’ve just made, as well.

## Software setup

Running this project is as simple as deploying it to a balenaCloud application, then downloading the OS image from the dashboard and flashing your SD card.

[![](https://balena.io/deploy.png)](https://dashboard.balena-cloud.com/deploy)

We recommend this button as the de-facto method for deploying new apps on balenaCloud, but as an alternative, you can set this project up with the repo and balenaCLI if you choose. Get the code from this repo, and set up [balenaCLI](https://github.com/balena-io/balena-cli) on your computer to push the code to balenaCloud and your devices. [Read more](https://www.balena.io/docs/learn/deploy/deployment/).

## Access the dashboard

Once the software has been deployed and downloaded to your device, the dashboard will be accessible on the local IP address of the device, or via the balenaCloud public URL feature.

![public-url](https://raw.githubusercontent.com/balenalabs-incubator/background-radiation-monitor/master/assets/public-url.png)
