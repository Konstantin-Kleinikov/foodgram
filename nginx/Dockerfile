FROM nginx:1.22.1
COPY nginx.conf /etc/nginx/templates/default.conf.template
RUN mkdir -p /static
RUN mkdir -p /media
RUN mkdir -p /frontend_static
RUN chmod -R 755 /static
RUN chmod -R 755 /media
RUN chmod -R 755 /frontend_static
