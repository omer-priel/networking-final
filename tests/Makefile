SHELL:=/usr/bin/env bash -O globstar

dhcp-release:
	sudo dhclient -r

dhcp-get-ip:
	sudo dhclient

dhcp-renew:
	sudo dhclient -r
	sudo dhclient

dhcp-show-ip:
	ip a

dhcp-show-apps-on-68:
	sudo lsof -i -P -n | grep :68

dhcp-kill-dhclient:
	sudo killall dhclient
