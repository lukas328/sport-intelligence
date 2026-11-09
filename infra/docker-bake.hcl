# The app images of the compose stack (infra/docker-compose.yml), tagged with the names compose
# gives them in project "handball-ai" (COMPOSE_PROJECT_NAME=handball-ai, otherwise compose names
# the project after the checkout directory), so `docker compose up --no-build` uses them.
# CI (e2e job) builds them with the layer cache the images job writes (one GitHub Actions cache
# scope per app). Run from the repo root:
#   docker buildx bake -f infra/docker-bake.hcl --load

group "default" {
  targets = ["api", "worker", "gpu-worker", "web"]
}

target "api" {
  context    = "."
  dockerfile = "apps/api/Dockerfile"
  # the migrate service runs the API image
  tags = ["handball-ai-api", "handball-ai-migrate"]
}

target "worker" {
  context    = "."
  dockerfile = "apps/worker/Dockerfile"
  tags       = ["handball-ai-worker"]
}

target "gpu-worker" {
  context    = "."
  dockerfile = "apps/gpu-worker/Dockerfile"
  tags       = ["handball-ai-gpu-worker"]
}

target "web" {
  context    = "."
  dockerfile = "apps/web/Dockerfile"
  tags       = ["handball-ai-web"]
}
