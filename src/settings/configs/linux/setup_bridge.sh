#!/bin/sh

ip link add name br0 type bridge
ip link set dev br0 up
ip link set dev enp9s0 promisc on
ip link set dev enp9s0 up
ip link set dev enp9s0 master br0

ip addr add dev br0 10.10.0.1/24
