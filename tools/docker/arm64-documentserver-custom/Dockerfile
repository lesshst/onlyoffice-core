FROM onlyoffice/documentserver:latest

RUN mkdir -p /var/www/onlyoffice/documentserver/server/FileConverter/tools

COPY build/bin/linux_64/x2t /var/www/onlyoffice/documentserver/server/FileConverter/bin/x2t
COPY build/bin/linux_64/libboost_date_time.so /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libboost_date_time.so.1.74.0 /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libboost_regex.so /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libboost_regex.so.1.74.0 /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libboost_filesystem.so /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libboost_filesystem.so.1.74.0 /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libboost_system.so /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libboost_system.so.1.74.0 /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libicudata.so.70 /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libicudata.so.70.1 /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libicui18n.so.70 /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libicui18n.so.70.1 /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libicuuc.so.70 /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY build/bin/linux_64/libicuuc.so.70.1 /var/www/onlyoffice/documentserver/server/FileConverter/bin/
COPY tools/word_html_mapper.py /var/www/onlyoffice/documentserver/server/FileConverter/tools/word_html_mapper.py

RUN chmod 755 /var/www/onlyoffice/documentserver/server/FileConverter/bin/x2t \
    && chmod 644 /var/www/onlyoffice/documentserver/server/FileConverter/tools/word_html_mapper.py
