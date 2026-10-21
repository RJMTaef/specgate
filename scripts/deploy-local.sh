#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for tool in docker kind kubectl uv; do
  command -v "$tool" >/dev/null || { echo "Missing prerequisite: $tool"; exit 1; }
done
tag="$(git rev-parse --short=12 HEAD)"
if ! kind get clusters | awk '$0 == "specgate" { found=1 } END { exit !found }'; then
  kind create cluster --config deploy/kind.yaml --wait 120s
fi
docker build -t "specgate:$tag" .
kind load docker-image "specgate:$tag" --name specgate
# Apply the immutable image in the manifest to avoid resetting the live deployment to :dev.
sed "s/image: specgate:dev/image: specgate:$tag/" deploy/kubernetes.yaml |
  kubectl --context kind-specgate apply -f -
kubectl --context kind-specgate -n specgate rollout status deployment/screening --timeout=120s
echo "Ready. Run: kubectl --context kind-specgate -n specgate port-forward svc/screening 8000:8000"
