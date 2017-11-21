# CMU Ubuntu VNC DEMO

Small example script that synthesis's a VM in a cloudlet through
the cloudlet gateway.

## What does it do?

1. POST request to create VM passing the overlay in the request.
2. Connects to the spawned VPN on the gateway using the provided client
config from the response of the POST request.
3. Connects to the VNC server that is running in the VM.
4. Upon disconnect it sets a DELETE request to destroy the VM in the overlay.

## How to use it?

1. First you need to install dependencies. `make deps`
2. Run the command passing in a user ID. This can be anything bus should be
unique between different users of the gateway. `sudo ./cmu-ubuntu.py blake`

## Why does it need root?

At the moment it needs root to connect to the VPN.
