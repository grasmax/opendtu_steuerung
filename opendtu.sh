
logfiletimestamp=$(date "+%Y%m%d_%H%M%S")

#date   >> /mnt/wd2tb/script/opendtu/log/opendtu_log_$logfiletimestamp.txt
date   >> /mnt/wd2tb/script/opendtu/log/opendtu.txt

cd /mnt/wd2tb/script/opendtu
#/usr/bin/python opendtu.py >> /mnt/wd2tb/script/opendtu/log/opendtu_log_$logfiletimestamp.txt
/usr/bin/python opendtu.py >> /mnt/wd2tb/script/opendtu/log/opendtu.txt



