import os
import subprocess
from datetime import datetime
from kubernetes import client, config
import math
import time

def are_all_pods_ready(namespace='default'):
    # Load kubeconfig
    config.load_kube_config()

    # Create a client for the CoreV1API
    v1 = client.CoreV1Api()

    # List all pods in the specified namespace
    pods = v1.list_namespaced_pod(namespace)

    # Check if all pods are ready
    all_pods_ready = True
    for pod in pods.items:
        if pod.status.conditions is None:
            all_pods_ready = False
            break
        for condition in pod.status.conditions:
            if condition.type == 'Ready' and condition.status != 'True':
                all_pods_ready = False
                # print(f"Pod {pod.metadata.name} is not ready")
                break  # Break out of the inner loop
    return all_pods_ready

def scrape_resource_config():
    # Load Kubernetes configuration from default location or a specific kubeconfig file
    config.load_kube_config()

    # Create a Kubernetes API client
    api_instance = client.AppsV1Api()

    try:
        namespace = "default"
        deployments = api_instance.list_namespaced_deployment(namespace, watch=False)
        resource_allocation = ""
        for deployment in deployments.items:
            metadata = deployment.metadata
            spec = deployment.spec.template.spec.containers[0]

            cpu_limit = spec.resources.limits.get("cpu") if spec.resources.limits else "N/A"
            cpu_request = spec.resources.requests.get("cpu") if spec.resources.requests else "N/A"
            mem_limit = spec.resources.limits.get("mem") if spec.resources.limits else "N/A"
            mem_request = spec.resources.requests.get("mem") if spec.resources.requests else "N/A"

            resource_allocation += f"Deployment,{metadata.name}\n"
            resource_allocation += f"CPU Limit,{cpu_limit}\n"
            resource_allocation += f"CPU Request,{cpu_request}\n"
            resource_allocation += f"Mem Limit,{mem_limit}\n"
            resource_allocation += f"Mem Request,{mem_request}\n"

    except Exception as e:
        print(f"Error: {e}")
        
    return resource_allocation

def convert_memory_to_mib(memory_usage):
    # Convert memory usage to MiB
    unit = memory_usage[-2:]  # Extract the unit (Ki, Mi, Gi)
    value = int(memory_usage[:-2])  # Extract the numeric value
    if unit == "Ki":
        return value / 1024  # 1 MiB = 1024 KiB
    elif unit == "Mi":
        return value
    elif unit == "Gi":
        return value * 1024  # 1 GiB = 1024 MiB
    else:
        return value / (1024**2)  # Assume the value is in bytes if no unit

def convert_cpu_to_millicores(cpu_usage):
    # Convert CPU usage to millicores
    if cpu_usage.endswith('n'):  # nanocores
        return int(cpu_usage.rstrip('n')) / 1000000
    elif cpu_usage.endswith('u'):  # assuming 'u' to be a unit close to millicores
        return int(cpu_usage.rstrip('u')) / 1000  # Convert assuming 'u' represents microcores
    else:
        return int(cpu_usage)  # Assuming direct millicore value


def get_pod_metrics(namespace='default'):
    # Load the kubeconfig file
    config.load_kube_config()

    # Create a client for the Metrics API
    api = client.CustomObjectsApi()

    # Fetch the pod metrics in the specified namespace
    try:
        metrics = api.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="pods"
        )
        output_str = ""
        for pod in metrics['items']:
            # print(f"Pod: {pod['metadata']['name']}")
            output_str += f"Pod: {pod['metadata']['name']}\n"
            for container in pod['containers']:
                container_name = container['name']
                cpu_usage = pod['containers'][0]['usage']['cpu']
                cpu_usage_millicores = convert_cpu_to_millicores(cpu_usage)
                memory_usage = container['usage']['memory']
                # Convert memory usage to MiB
                memory_usage_mib = convert_memory_to_mib(memory_usage)
                # print(f"Container: {container_name}, CPU: {math.ceil(cpu_usage_millicores)}m, Memory: {math.ceil(memory_usage_mib)} MiB")
                output_str += f"Container: {container_name}, CPU: {math.ceil(cpu_usage_millicores)}m, Memory: {math.ceil(memory_usage_mib)} MiB\n"

    except client.rest.ApiException as e:
        print(f"Exception when calling CustomObjectsApi->list_namespaced_custom_object: {e}")
    return output_str

def run_command(command):
    """Run shell command and return its output"""
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return output.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.output.decode('utf-8')}")
        exit(1)

def run_wrk(cluster, req_type, rps, dir):
    distribution = "exp"
    thread = 50
    connection = 50
    duration = 60
    nodename = run_command("kubectl get nodes | grep 'node1' | awk '{print $1}'")
    ingressgw_http2_nodeport = run_command("kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name==\"http2\") | .nodePort'")
    server_ip = f"http://{nodename}:{ingressgw_http2_nodeport}"
    print(server_ip)
    name = f"{cluster}_{req_type}_{rps}.wrklog"
    output_fn = os.path.join(dir, name)
    if rps < connection:
        connection = rps
    if connection < thread:
        thread = connection
    if req_type not in ["search", "user", "recommend", "reserve"]:
        print(f"@@ Wrong req_type: {req_type}")
        exit(1)
    if not os.path.isdir(dir):
        os.makedirs(dir)
    
    
    print(f"@@ Start {req_type} RPS: {rps} to {cluster} for {duration} (output_fn: {output_fn})")
    with open(output_fn, "w") as f:
        f.write("@@ +++++++++++++++++++++++++++++++++++++++++++++++++ \n")
        info = f"""
--------------------------------
distribution: {distribution}
thread: {thread}
connection: {connection}
duration: {duration}
cluster: {cluster}
req_type: {req_type}
RPS: {rps}
--------------------------------
"""
        f.write(info)
    
    wrk_command = f"./wrk -D {distribution} -t{thread} -c{connection} -d{duration} -L -S -s ./wrk2/scripts/hotel-reservation/{cluster}_{req_type}.lua {server_ip} -R{rps} >> {output_fn}"
    run_command(wrk_command)
    print(f"@@ OUTPUT FILENAME: {output_fn} written")
    return output_fn

def sleep_and_print(sl):
    print(f"@@ sleep {sl} seconds")
    run_command(f"sleep {sl}")

def disable_istio():
    run_command("kubectl label namespace default istio-injection=disabled")
    print("@@ kubectl label namespace default istio-injection=disabled")
    sleep_and_print(10)

def enable_istio():
    run_command("kubectl label namespace default istio-injection=enabled")
    print("@@ kubectl label namespace default istio-injection=enabled")
    sleep_and_print(10)

def delete_wasm():
    run_command("kubectl delete -f wasmplugins.yaml")
    print("@@ kubectl delete -f wasmplugins.yaml")
    sleep_and_print(5)

def apply_wasm():
    run_command("kubectl apply -f wasmplugins.yaml")
    print("@@ kubectl apply -f wasmplugins.yaml")
    sleep_and_print(5)

def restart_wasm():
    run_command("kubectl delete -f wasmplugins.yaml")
    print("@@ kubectl delete -f wasmplugins.yaml")
    sleep_and_print(60)
    run_command("kubectl apply -f wasmplugins.yaml")
    print("@@ kubectl apply -f wasmplugins.yaml")
    sleep_and_print(10)

def restart_deploy(exclude=[]):
    print("start restart deploy")
    config.load_kube_config()
    api_instance = client.AppsV1Api()
    # excluded_deployment_name = "slate-controller"
    try:
        deployments = api_instance.list_namespaced_deployment(namespace="default")
        for deployment in deployments.items:
            if deployment.metadata.name not in exclude:
                run_command(f"kubectl rollout restart deploy {deployment.metadata.name}")
    except client.ApiException as e:
        print("Exception when calling AppsV1Api->list_namespaced_deployment: %s\n" % e)
        
    while True:
        if are_all_pods_ready():
            break
        time.sleep(1)
    time.sleep(5)
    print("restart deploy is done")

def restart_slate_controller():
    run_command("kubectl rollout restart deploy slate-controller")
    print("@@ kubectl rollout restart deploy slate-controller")
    sleep_and_print(10)

def scp_trace_string_file(dir, cluster, req_type, rps):
    slate_controller_pod = run_command("kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name")
    # destination = f"{dir}/slate_trace_string_{req_type}_{rps}.slatelog"
    destination = f"{dir}/{cluster}_{req_type}_{rps}.slatelog"
    run_command(f"kubectl cp {slate_controller_pod}:/app/trace_string.csv {destination}")
    print(f"scp_trace_string_file")
    print(f"source: {slate_controller_pod}:/app/trace_string.csv")
    print(f"destination: {destination}")

def main():
    start_time = datetime.now()
    cluster = "west"
    # with_wasm = [True, False]
    istio_config = True
    # with_wasm = [True, False]
    with_wasm = [True]
    
    # if istio_config == False:
    #     disable_istio()
    # else:
    #     enable_istio()
        
    req_type_list = ["recommend"]
    # req_type_list = ["reserve"] # reserve is not working
    # req_type_list = ["user", "recommend", "search"]
    rps_list = {
                # "user": [1000, 2000, 3000, 4000], \
                "user": [4000], \
                # "user": [100, 500, 1000, 1500, 2000], \
                "recommend": [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000], \
                # "search": [10, 50, 100, 200, 300], \
                "search": [20, 40, 60, 80, 100, 150, 200], \
                # "reserve": [50] \
                }
    
    for wasm_config in with_wasm:
        if istio_config == True:
            print(f"wasm config: {wasm_config}")
            if wasm_config:
                apply_wasm()
            else:
                delete_wasm()
                restart_deploy(exclude=[])
        print(f"istio config: {istio_config}")
        
        postfix = "0229_without_cpulimit"
        print(f"\n* postfix for output file: {postfix}")
        for i in [5,4,3,2,1]:
            print(f"will start in {i} seconds")
            time.sleep(1)
        for req_type in req_type_list:
            if istio_config:
                if wasm_config:
                    dir = f"{req_type}_with_wasm_{postfix}"
                else:
                    dir = f"{req_type}_without_wasm_{postfix}"
            else:
                dir = f"{req_type}_without_istio_{postfix}"
            for rps in rps_list[req_type]:
                per_wrk_st = datetime.now()
                output_fn = run_wrk(cluster, req_type, rps, dir)
                pod_metrics = get_pod_metrics('default')
                resource_allocation = scrape_resource_config()
                with open(output_fn, "a") as f:
                    f.write("@@ pod_metrics\n")
                    f.write(pod_metrics)
                    f.write("@@ resource_allocation\n")
                    f.write(resource_allocation)
                # restart_wasm()
                scp_trace_string_file(dir, cluster, req_type, rps)
                # restart_deploy(exclude=["slate-controller"])
                restart_deploy(exclude=[])
                per_wrk_et = datetime.now()
                per_wk_duration = (per_wrk_et - per_wrk_st).seconds
                print(f"@@ per_wk_duration: {per_wk_duration} seconds")
            # restart_slate_controller()
        end_time = datetime.now()
        duration = (end_time - start_time).seconds
        print(f"@@ Total runtime: {duration} seconds")

if __name__ == "__main__":
    main()
