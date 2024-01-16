#!/bin/bash

function wrk() {
    distribution=exp
    thread=50
    connection=50
    duration=30


    cluster=$1
    req_type=$2
    RPS=$3

    if [ ${RPS} -lt ${connection} ]; then
        connection=${RPS}
    fi
    if [ ${connection} -lt ${thread} ]; then
        thread=${connection}
    fi

    name_tag=$4

    if [ ${cluster} == "west" ]; then
        server_ip="http://node1.gangmuk-185120.istio-pg0.clemson.cloudlab.us:31029"
    elif [ ${cluster} == "east" ]; then
    ## TODO: needs valid east ip address
        server_ip="http://node2.gangmuk-185120.istio-pg0.clemson.cloudlab.us:31029"
    else
        echo "@@ ERROR: Wrong cluster: ${cluster}"
        exit
    fi

    #if [ "${req_type}" != "user" ] && [ ${req_type} != "recommend" ] && [ ${req_type} != "reserve" ]; then
    if [ "${req_type}" != "search" ] && [ "${req_type}" != "user" ] && [ ${req_type} != "recommend" ] && [ ${req_type} != "reserve" ]; then
        echo "@@ Wrong req_type: ${req_type}"
        exit
    fi

    if [ ! -d "$name_tag" ]; then
        mkdir -p "$name_tag"
    fi

    filename="${name_tag}/${cluster}_${req_type}_${RPS}.wrklog"

    echo "@@ Start ${req_type} RPS: ${RPS} to ${cluster} for ${duation} (filename: ${filename})"

    echo "@@ +++++++++++++++++++++++++++++++++++++++++++++++++ " > ${filename}
    echo "--------------------------------"
    echo "distribution: ${distribution}"
    echo "thread: ${thread}"
    echo "connection: ${connection}"
    echo "duration: ${duration}"
    echo "cluster: ${cluster}"
    echo "req_type: ${req_type}"
    echo "RPS: ${RPS}"
    echo "--------------------------------"

    echo "--------------------------------" >> ${filename}
    echo "distribution: ${distribution}" >> ${filename}
    echo "thread: ${thread}" >> ${filename}
    echo "connection: ${connection}" >> ${filename}
    echo "duration: ${duration}" >> ${filename}
    echo "cluster: ${cluster}" >> ${filename}
    echo "req_type: ${req_type}" >> ${filename}
    echo "RPS: ${RPS}" >> ${filename}
    echo "--------------------------------" >> ${filename}

    ./wrk -D ${distribution} -t${thread} -c${connection} -d${duration} -L -S -s ./wrk2/scripts/hotel-reservation/${cluster}_${req_type}.lua ${server_ip} -R${RPS} >> ${filename}

    echo "@@ FILENAME: ${filename} written"
}

function sleep_and_print(){
    sl=$1
    echo "@@ sleep ${sl} seconds"
    sleep ${sl}
}

function restart_wasm(){
    ## Restart WasmPlugin
    kubectl delete -f wasmplugins.yaml
    echo "@@ kubectl delete -f wasmplugins.yaml"
    sleep_and_print 60

    kubectl apply -f wasmplugins.yaml
    echo "@@ kubectl apply -f wasmplugins.yaml"
    sleep_and_print 5
}

function restart_slate_controller(){
    ## Restart slate-controller deployment
    kubectl rollout restart deploy slate-controller
    echo "@@ kubectl rollout restart deploy slate-controller"
    sleep_and_print 10
}

function scp_trace_string_file(){
    tg=$1
    ## SCP trace_string.csv from slate-controller pod to the local filesystem
    slate_controller_pod=$(kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name)
    kubectl cp ${slate_controller_pod}:/app/trace_string.csv slate_trace_string_${tg}.slatelog
}


function full_reset(){
    tg=$1

    scp_trace_string_file $tg

    restart_wasm

    restart_slate_controller

}


# init_time=$(date +"%y%m%d_%H%M%S")
# start_time=$(date +%s)

req_type=recommend
rps_list=(50 200 400 600 800 1000)
tag=${req_type}_only_${init_time}
for rps in "${rps_list[@]}"; do
	per_wrk_st=$(date +%s)
	wrk west ${req_type} ${rps} ${tag}
	restart_wasm
	per_wrk_et=$(date +%s)
	per_wk_duration=$((per_wrk_et - per_wrk_st))
	echo "@@ per_wk_duration: ${per_wk_duration} seconds"
done
full_reset ${tag}
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "@@ Duration: ${duration} seconds"

req_type=user
rps_list=(50 200 400 600 800 1000)
tag=${req_type}_only_${init_time}
for rps in "${rps_list[@]}"; do
	per_wrk_st=$(date +%s)
	wrk west ${req_type} ${rps} ${tag}
	restart_wasm
	per_wrk_et=$(date +%s)
	per_wk_duration=$((per_wrk_et - per_wrk_st))
	echo "@@ per_wk_duration: ${per_wk_duration} seconds"
done
full_reset ${tag}
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "@@ Duration: ${duration} seconds"

req_type=reserve
rps_list=(10 20 30 40 50 60 70 80 90 100)
tag=${req_type}_only_${init_time}
for rps in "${rps_list[@]}"; do
	per_wrk_st=$(date +%s)
	wrk west ${req_type} ${rps} ${tag}
	restart_wasm
	per_wrk_et=$(date +%s)
	per_wk_duration=$((per_wrk_et - per_wrk_st))
	echo "@@ per_wk_duration: ${per_wk_duration} seconds"
done
full_reset ${tag}
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "@@ Duration: ${duration} seconds"



# init_time=$(date +"%y%m%d_%H%M%S")
# start_time=$(date +%s)
# tag=case1_${init_time}
# wrk west user 100 ${tag} &
# wrk west recommend 0 ${tag} &
# wrk west reserve 0 ${tag} &
# wait
# reset ${tag}
# end_time=$(date +%s)
# duration=$((end_time - start_time))
# echo "@@ Duration: ${duration} seconds"

# start_time=$(date +%s)
# tag=case2_${init_time}
# wrk west user 0 ${tag} &
# wrk west recommend 100 ${tag} &
# wrk west reserve 0 ${tag} &
# wait
# reset ${tag}
# end_time=$(date +%s)
# duration=$((end_time - start_time))
# echo "@@ Duration: ${duration} seconds"

# start_time=$(date +%s)
# tag=case3_${init_time}
# wrk west user 0 ${tag} &
# wrk west recommend 0 ${tag} &
# wrk west reserve 100 ${tag} &
# wait
# reset ${tag}
# end_time=$(date +%s)
# duration=$((end_time - start_time))
# echo "@@ Duration: ${duration} seconds"

# start_time=$(date +%s)
# tag=case4_${init_time}
# wrk west user 50 ${tag} &
# wrk west recommend 50 ${tag} &
# wrk west reserve 0 ${tag} &
# wait
# reset ${tag}
# end_time=$(date +%s)
# duration=$((end_time - start_time))
# echo "@@ Duration: ${duration} seconds"

# start_time=$(date +%s)
# tag=case5_${init_time}
# wrk west user 50 ${tag} &
# wrk west recommend 0 ${tag} &
# wrk west reserve 50 ${tag} &
# wait
# reset ${tag}
# end_time=$(date +%s)
# duration=$((end_time - start_time))
# echo "@@ Duration: ${duration} seconds"

# start_time=$(date +%s)
# tag=case6_${init_time}
# wrk west user 0 ${tag} &
# wrk west recommend 50 ${tag} &
# wrk west reserve 50 ${tag} &
# wait
# reset ${tag}
# end_time=$(date +%s)
# duration=$((end_time - start_time))
# echo "@@ Duration: ${duration} seconds"

# start_time=$(date +%s)
# tag=case7_${init_time}
# wrk west user 33 ${tag} &
# wrk west recommend 33 ${tag} &
# wrk west reserve 33 ${tag} &
# wait
# reset ${tag}
# end_time=$(date +%s)
# duration=$((end_time - start_time))
# echo "@@ Duration: ${duration} seconds"


#################################################
