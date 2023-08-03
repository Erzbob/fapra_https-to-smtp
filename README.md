This project was developed in the course of an internship at the Fernuni in Hagen. The task required giving a client the ability to access the Internet (http and https) in a network, although this is only allowed to a special computer (the server) in that network.

Setting up the lab environment: 
- Follow this to install Postfix: https://www.digitalocean.com/community/tutorials/how-to-install-and-configure-postfix-on-ubuntu-20-04.
- Follow this to install Courier IMAP: https://docs.gitlab.com/ee/administration/reply_by_email_postfix_setup.html
- On the client, install Postfix as the email server and Courier IMAP (both from the apt of your Debian based Linux distribution). Configure Postfix' main.cf file so that the server is entered as relay host to which e-mails are forwarded. Use Firefox as your web browser.
- On the server, install Postfix and Courier IMAP as you did for the client. The client is entered here as the relay host in Postfix' main.cf file. On the server you must also install the HTTPS proxy "Tinyproxy". Tinyproxy is also available via the apt.
- Configure the firewall on both machines to allow Postfix and Courier IMAP. If you use "ufw" as a firewall, the terminal commands "sudo ufw allow postfix" and "sudo ufw allow imap" does the trick.

Start the setup:
- Start https_proxy_side.py via a terminal at the server. At startup, pass parameters:
  - The port where tinyproxy is listening (8888 by default),
  - the username and password for the user logged into the server machine and
  - the email addresses of the communication partners.
  Username and password are needed for authentication with the IMAP server.
- In Firefox in the network settings enter "localhost" as proxy for http and https and an unused port, e.g. 8000.
- Start browser_side.py via a terminal at the client. At startup, pass parameters:
  - The port from the previous step,
  - the username and password for the user logged into the client machine and
  - the email addresses of the communication partners.
  Username and password are needed for authentication with the IMAP server.

Browse the internet:
- via firefox on the client machine you are good to go to browse the internet now.
