#!/bin/bash
# Quick SSL Fix for my.doctorhealthy1.com
sudo systemctl stop nginx
sudo certbot certonly --standalone --non-interactive --agree-tos --email admin@doctorhealthy1.com -d my.doctorhealthy1.com --force-renewal
sudo systemctl start nginx
