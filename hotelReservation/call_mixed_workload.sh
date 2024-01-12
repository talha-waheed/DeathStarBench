distribution=exp
thread=20
connection=50
duration=60
RPS=100
server="http://node1.gangmuk-185120.istio-pg0.clemson.cloudlab.us:31029"
./wrk -D ${distribution} -t${thread} -c${connection} -d${duration} -L -S -s ./wrk2/scripts/hotel-reservation/west-mixed-workload_type_1.lua ${server}  -R${RPS}
