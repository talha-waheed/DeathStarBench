#!/usr/bin/env bash

for i in {1..1000}; do
  curl -d "first_name=first_name_"$i"&last_name=last_name_"$i"&username=username_"$i"&password=password_"$i \
      http://node2.gangmuk-196723.istio-pg0.apt.emulab.net:30001/wrk2-api/user/register
done
