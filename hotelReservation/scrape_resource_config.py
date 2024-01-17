from kubernetes import client, config

def main():
    # Load Kubernetes configuration from default location or a specific kubeconfig file
    config.load_kube_config()

    # Create a Kubernetes API client
    api_instance = client.AppsV1Api()

    try:
        # List all deployments in the cluster
        namespace = "default"
        deployments = api_instance.list_namespaced_deployment(namespace, watch=False)

        # Iterate through deployments and extract CPU limits and requests
        for deployment in deployments.items:
            metadata = deployment.metadata
            spec = deployment.spec.template.spec.containers[0]

            # Check if limits and requests are defined
            cpu_limit = spec.resources.limits.get("cpu") if spec.resources.limits else "N/A"
            cpu_request = spec.resources.requests.get("cpu") if spec.resources.requests else "N/A"
            mem_limit = spec.resources.limits.get("mem") if spec.resources.limits else "N/A"
            mem_request = spec.resources.requests.get("mem") if spec.resources.requests else "N/A"

            # Write the information to the file
            print(f"Deployment: {metadata.name}")
            print(f"CPU Limit: {cpu_limit}")
            print(f"CPU Request: {cpu_request}")
            print(f"MEM Limit: {mem_limit}")
            print(f"MEM Request: {mem_request}")
            print("\n")

        print("Resource information written to deployment_resources.txt")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

