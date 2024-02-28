#!/bin/bash

echo "WANRING: THIS IS DEPRECATED. USE run_wrk.py instead"
exit

function wrk() {
    cluster=$1
    req_type=$2
    RPS=$3
    dir=$4
    distribution=exp
    thread=50
    connection=50
    duration=30
    nodename=$(kubectl get nodes | grep "node1" | awk '{print $1}')
    ingressgw_http2_nodeport=$(kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name=="http2") | .nodePort')
    server_ip="http://${nodename}:${ingressgw_http2_nodeport}"
    echo $server_ip
    name="${cluster}_${req_type}_${RPS}.wrklog"
    filename="${dir}/${name}"
    if [ ${RPS} -lt ${connection} ]; then
        connection=${RPS}
    fi
    if [ ${connection} -lt ${thread} ]; then
        thread=${connection}
    fi
    if [ "${req_type}" != "search" ] && [ "${req_type}" != "user" ] && [ ${req_type} != "recommend" ] && [ ${req_type} != "reserve" ]; then
        echo "@@ Wrong req_type: ${req_type}"
        exit
    fi
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi

    python ~/projects/slate-benchmark/scrape_resource_config.py > ${dir}/deployment_resource_${name}.txt
    echo "@@ python scrape_resource_config.py > ${dir}/deployment_resource_${name}.txt"

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
    sleep_and_print 10
}

function restart_slate_controller(){
    ## Restart slate-controller deployment
    kubectl rollout restart deploy slate-controller
    echo "@@ kubectl rollout restart deploy slate-controller"
    sleep_and_print 10
}

function scp_trace_string_file(){
    dir=$1
    req_type=$2
    rps=$3
    ## SCP trace_string.csv from slate-controller pod to the local filesystem
    slate_controller_pod=$(kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name)
    echo "scp_trace_string_file"
    echo "source: ${slate_controller_pod}:/app/trace_string.csv"
    echo "destination: ${dir}/slate_trace_string_${req_type}_${rps}.slatelog"
    echo "kubectl cp ${slate_controller_pod}:/app/trace_string.csv ${dir}/slate_trace_string_${dir}.slatelog"
    kubectl cp ${slate_controller_pod}:/app/trace_string.csv ${dir}/slate_trace_string_${dir}.slatelog
}


#function full_reset(){
#    tg=$1
#    scp_trace_string_file $tg
#    restart_wasm
#    restart_slate_controller
#}

start_time=$(date +%s)
cluster=west # west or east

# req_type_list=(reserve search recommend user)
req_type_list=(search)
for req_type in "${req_type_list[@]}"; do
    dir=${req_type}_test
    # rps_list=(100 200 300 400 500 600 700 800 900 1000)
    rps_list=(200)
    for rps in "${rps_list[@]}"; do
        per_wrk_st=$(date +%s)
        wrk ${cluster} ${req_type} ${rps} ${dir}
        scp_trace_string_file ${dir} ${req_type} ${rps}
        # restart_wasm
        restart_slate_controller
        per_wrk_et=$(date +%s)
        per_wk_duration=$((per_wrk_et - per_wrk_st))
        echo "@@ per_wk_duration: ${per_wk_duration} seconds"
    done
done
restart_slate_controller

end_time=$(date +%s)
duration=$((end_time - start_time))
echo "@@ Total runtime: ${duration} seconds"
