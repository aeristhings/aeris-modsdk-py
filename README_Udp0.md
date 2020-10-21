# Overview

This document gives a brief overview of the Aeris IP Shoulder-Tap System (name pending), and a more detailed overview of the Udp0 shoulder-tap protocol and how you can use this Module SDK to evaluate the Udp0 shoulder-tap protocol for your use case.

Talk to your Aeris sales representative or contact Aeris at https://www.aeris.com/contact-us/ to learn more.

# Scenario

Your Aeris-connected devices need to be able to prompted to perform some action when commanded by your application servers.

However, your Aeris-connected device may be using a technique such as Power Saving Mode (PSM) or extended discontinuous reception (eDRX) to turn off its cellular radio and therefore save power.

# Solution

Aeris' AerFrame APIs allow you to send a shoulder-tap message to your Aeris-connected device; software running on the device receives the shoulder-taps and prompts the application to take some action. 
Aeris' system will do its best to deliver the shoulder-tap to the connected device.

See https://aeriscom.zendesk.com/hc/en-us/articles/360036914654-AerFrame-Device-Communication-and-Control-API for how to use the AerFrame APIs to create shoulder-tap messages.

# Udp0

The Udp0 protocol (or delivery mechanism) works like so:

```
Device    Cellular Network     Aeris AerFrame API             Application Server
 |         |                    |                                     |
 |         |                    |  <----------- create shoulder-tap   |
 |         |                    |                                     |
 |         |                    |  ------- request ID ------------>   |
 |         |                    |                                     |
 |  <---- shoulder-tap packet   |                                     |
 |         |                    |                                     |
 |   ----------- inform of received request ID -------------------->  |
 |         |                    |                                     |
 |  <---- shoulder-tap packet   |                                     |
 |         |                    |                                     |
 |  <---- shoulder-tap packet   |                                     |
 |         |                    |                                     |
 |         |                    |  <----------- cancel shoulder-tap   |
 |         |                    |               by request ID         |
 ```
 
Included in each Udp0 shoulder-tap packet is a sequence number. This sequence number forms part of the request ID used to refer to the shoulder-tap.

## Using this Module SDK

This Module SDK provides two methods for receiving Udp0 shoulder-taps from the Aeris AerFrame APIs. 

### CLI

Run `poetry run aeriscli udp shoulder-tap`

This CLI will cause the radio module to listen on UDP port 23747 for shoulder-tap packets and will print out their request IDs and payloads.

Currently, the CLI only supports the Quectel BG96 radio module.

### Python Integration

The file `aerismodsdk/utils/shoulder_tap.py` exposes the `parse_shoulder_tap` function which decodes a binary packet (received, e.g., through a Python program listening on a UDP socket) into an object that exposes the payload and request ID of the shoulder-tap.
