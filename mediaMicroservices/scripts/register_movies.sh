#!/usr/bin/env bash

for i in {1..1000}; do
  curl -d "title=title_"$i"&movie_id=movie_id_"$i \
      http://node2.gangmuk-196723.istio-pg0.apt.emulab.net:30001/wrk2-api/movie/register
done
