#!/bin/env python3

import argparse
import os
import subprocess
import sys
import tempfile
import threading
import time

import requests


def connect_vpn(config):
    """Connect to the VPN."""
    stop = threading.Event()
    connected = threading.Event()

    def _spawn_vpn():
        with tempfile.TemporaryDirectory() as tmpdir:
            vpn_config = os.path.join(tmpdir, 'client.ovpn')
            with open(vpn_config, 'w') as stream:
                stream.write(config)
            print('Connecting to the gateway VPN.')
            process = subprocess.Popen(
                ['openvpn', vpn_config],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            time.sleep(5)  # Wait 5 seconds make sure its fully connected.
            if process.returncode is not None:
                raise subprocess.CalledProcessError(
                    process.returncode, 'openvpn', process.stdout.read())
            connected.set()
            stop.wait()
            print('Disconnecting the gateway VPN.')
            process.kill()
            process.wait()

    thread = threading.Thread(target=_spawn_vpn)
    thread.start()
    connected.wait()
    return stop, thread


def disconnect_vpn(vpn):
    """Disconnect from the VPN."""
    stop, thread = vpn
    stop.set()
    thread.join()


def create(user):
    """Create the VM in the cloudlet and connect to it with VNC."""
    with open('vnc-overlay.zip', 'rb') as stream:
        files = {
            'overlay': stream.read()
        }
    print('Requesting VM be created in cloudlet and pushing overlay.')
    resp = requests.post(
        'http://orangebox72.elijah.cs.cmu.edu:2000/',
        files=files,
        data={
            'user_id': user,
            'app_id': 'vncdesktop',
        })
    if resp.status_code != 201:
        raise Exception('Failed to create VM in cloudlet: %s' % resp.text)
    return resp.json()


def destroy(user):
    """Destroy the VM in the cloudlet."""
    print('Requesting VM to be destroyed in cloudlet.')
    requests.delete(
        'http://orangebox72.elijah.cs.cmu.edu:2000/',
        params={
            'user_id': user,
            'app_id': 'vncdesktop',
        })
    print('VM destroyed in cloudlet.')


def spawn_vnc_server(ip):
    """Spawn the VNC server on the VM."""
    stop = threading.Event()
    running = threading.Event()

    def _spawn_vnc():
        process = subprocess.Popen([
            'sshpass', '-p', 'ubuntu', 'ssh',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'StrictHostKeyChecking=no',
            '-L', '5900:localhost:5900',
            'ubuntu@%s ' % ip,
            'x11vnc -display :0 -noxdamage'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        time.sleep(5)  # Wait 5 seconds make sure its running.
        if process.returncode is not None:
            raise subprocess.CalledProcessError(
                process.returncode, 'sshpass', process.stdout.read())
        running.set()
        stop.wait()
        process.kill()
        process.wait()

    thread = threading.Thread(target=_spawn_vnc)
    thread.start()
    running.wait()
    return stop, thread


def destroy_vnc_server(vpn):
    """Destory from the VPN server."""
    stop, thread = vpn
    stop.set()
    thread.join()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Spawn Ubuntu Desktop in Cloudlet')
    parser.add_argument(
        'user', nargs=1,
        help=(
            "User ID in the cloudlet. (Can be anything.)"))
    args = parser.parse_args()
    if os.geteuid() != 0:
        print('Must be ran as root so VPN connection can be created.')
        sys.exit(1)
    vpn = None
    vnc = None
    try:
        resp = create(args.user)
        try:
            vpn = connect_vpn(resp['vpn'])
            try:
                vnc = spawn_vnc_server(resp['ip'])
                print('Spawning the VNC client.')
                subprocess.check_output(['gvncviewer', 'localhost'])
            finally:
                if vnc:
                    destroy_vnc_server(vnc)
        finally:
            if vpn:
                disconnect_vpn(vpn)
    finally:
        destroy(args.user)


if __name__ == '__main__':
    main()
