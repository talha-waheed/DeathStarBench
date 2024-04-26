slate_controller_pod="slate-controller-9678dd89b-bk8r6"
root="/app"
# fn="constraint.csv"
# src_in_pod="${root}/${fn}"
# kubectl cp ${slate_controller_pod}:${src_in_pod} ${fn}

# fn="constraint.log"
# src_in_pod="${root}/${fn}"
# kubectl cp ${slate_controller_pod}:${src_in_pod} ${fn}

# fn="variable.csv"
# src_in_pod="${root}/${fn}"
# kubectl cp ${slate_controller_pod}:${src_in_pod} ${fn}

# fn="compute_df.csv"
# src_in_pod="${root}/${fn}"
# kubectl cp ${slate_controller_pod}:${src_in_pod} ${fn}

# fn="network_df.csv"
# src_in_pod="${root}/${fn}"
# kubectl cp ${slate_controller_pod}:${src_in_pod} ${fn}

# fn="percentage_df.csv"
# src_in_pod="${root}/${fn}"
# kubectl cp ${slate_controller_pod}:${src_in_pod} ${fn}

fn="request_flow.csv"
src_in_pod="${root}/${fn}"
kubectl cp ${slate_controller_pod}:${src_in_pod} ${fn}