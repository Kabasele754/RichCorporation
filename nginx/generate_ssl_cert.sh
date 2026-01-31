#!/bin/bash

# Générer les certificats SSL Let's Encrypt
certbot certonly --standalone -d richcorporationsa.com -d www.richcorporationsa.com --agree-tos -n --email pepexykabasele@gmail.com

# Copier les certificats dans le répertoire Nginx
cp /etc/letsencrypt/live/richcorporationsa.com/fullchain.pem /etc/nginx/ssl/cert.pem
cp /etc/letsencrypt/live/richcorporationsa.com/privkey.pem /etc/nginx/ssl/privkey.pem
# Redémarrer Nginx pour charger les nouveaux certificats
nginx -s reload
