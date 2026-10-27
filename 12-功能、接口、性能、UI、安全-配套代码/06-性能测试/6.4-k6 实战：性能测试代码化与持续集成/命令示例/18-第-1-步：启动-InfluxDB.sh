docker run -d --name influxdb \
  -p 8086:8086 \
  -e INFLUXDB_DB=k6 \
  influxdb:1.8
