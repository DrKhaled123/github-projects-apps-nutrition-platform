#!/bin/bash

# Coolify Application Deployment Script
set -e

COOLIFY_API_TOKEN="7|Pc76Go9w1ELoKy0GBYb2RpMxWWujefpjEKM30R3Obef9679a"
COOLIFY_HOST="http://128.140.111.171:8000"
PROJECT_UUID="nsw8wcsswcoo8oww4ko080sc"
SERVER_UUID="x8gck8ggggsgkggg4coosg0g"

echo "🚀 Deploying DoctorHealthy Applications to Coolify"
echo "Host: $COOLIFY_HOST"
echo "Project: $PROJECT_UUID"
echo "Server: $SERVER_UUID"

# Create Frontend Application (Docker Compose)
echo "📦 Creating Frontend Application..."
FRONTEND_RESPONSE=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -X POST "$COOLIFY_HOST/api/v1/projects/$PROJECT_UUID/applications" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DoctorHealthy Frontend",
    "description": "React frontend for DoctorHealthy platform",
    "git_repository": "https://github.com/your-username/doctorhealthy-frontend.git",
    "git_branch": "main",
    "build_pack": "dockercompose",
    "docker_compose_location": "/",
    "docker_compose_custom_build_command": "docker-compose -f docker-compose.prod.yml build",
    "docker_compose_custom_start_command": "docker-compose -f docker-compose.prod.yml up -d",
    "destination_docker": {
      "network": "coolify",
      "network_id": null
    },
    "environment_variables": {
      "REACT_APP_API_URL": "https://api.doctorhealthy1.com",
      "REACT_APP_ENVIRONMENT": "production"
    },
    "domains": [
      {
        "domain": "my.doctorhealthy1.com",
        "is_primary": true
      }
    ],
    "instant_deploy": false,
    "server_uuid": "'$SERVER_UUID'"
  }')

FRONTEND_UUID=$(echo $FRONTEND_RESPONSE | jq -r '.uuid // empty')
echo "Frontend UUID: $FRONTEND_UUID"

# Create Backend Application (Docker)
echo "🔧 Creating Backend Application..."
BACKEND_RESPONSE=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -X POST "$COOLIFY_HOST/api/v1/projects/$PROJECT_UUID/applications" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DoctorHealthy Backend",
    "description": "Go backend API for DoctorHealthy platform",
    "git_repository": "https://github.com/your-username/doctorhealthy-backend.git",
    "git_branch": "main",
    "build_pack": "docker",
    "dockerfile_location": "/",
    "docker_build_command": "docker build -t doctorhealthy-backend .",
    "docker_run_command": "docker run -d --name doctorhealthy-backend -p 8080:8080 --network coolify doctorhealthy-backend",
    "environment_variables": {
      "DB_HOST": "postgres",
      "DB_PORT": "5432",
      "DB_NAME": "doctorhealthy",
      "DB_USER": "postgres",
      "DB_PASSWORD": "your_secure_password",
      "REDIS_HOST": "redis",
      "REDIS_PORT": "6379",
      "ENVIRONMENT": "production"
    },
    "domains": [
      {
        "domain": "backend.doctorhealthy1.com",
        "is_primary": true
      }
    ],
    "instant_deploy": false,
    "server_uuid": "'$SERVER_UUID'"
  }')

BACKEND_UUID=$(echo $BACKEND_RESPONSE | jq -r '.uuid // empty')
echo "Backend UUID: $BACKEND_UUID"

# Create Monitoring Application (Docker Compose)
echo "📊 Creating Monitoring Application..."
MONITORING_RESPONSE=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -X POST "$COOLIFY_HOST/api/v1/projects/$PROJECT_UUID/applications" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DoctorHealthy Monitoring",
    "description": "Grafana + Prometheus monitoring stack",
    "build_pack": "dockercompose",
    "docker_compose_location": "/",
    "docker_compose_custom_domains": "monitor.doctorhealthy1.com",
    "docker_compose_custom_build_command": "docker-compose -f docker-compose.monitoring.yml build",
    "docker_compose_custom_start_command": "docker-compose -f docker-compose.monitoring.yml up -d",
    "environment_variables": {
      "GF_SECURITY_ADMIN_PASSWORD": "admin123",
      "PROMETHEUS_RETENTION": "30d"
    },
    "domains": [
      {
        "domain": "monitor.doctorhealthy1.com",
        "is_primary": true
      }
    ],
    "instant_deploy": false,
    "server_uuid": "'$SERVER_UUID'"
  }')

MONITORING_UUID=$(echo $MONITORING_RESPONSE | jq -r '.uuid // empty')
echo "Monitoring UUID: $MONITORING_UUID"

# Create Database Service (PostgreSQL)
echo "🗄️ Creating Database Service..."
DATABASE_RESPONSE=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -X POST "$COOLIFY_HOST/api/v1/projects/$PROJECT_UUID/databases" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DoctorHealthy Database",
    "description": "PostgreSQL database for DoctorHealthy",
    "database_type": "postgres",
    "postgres_version": "16",
    "destination_docker": {
      "network": "coolify"
    },
    "environment_variables": {
      "POSTGRES_DB": "doctorhealthy",
      "POSTGRES_USER": "postgres",
      "POSTGRES_PASSWORD": "your_secure_password"
    },
    "is_public": false,
    "server_uuid": "'$SERVER_UUID'"
  }')

DATABASE_UUID=$(echo $DATABASE_RESPONSE | jq -r '.uuid // empty')
echo "Database UUID: $DATABASE_UUID"

echo "✅ Applications created successfully!"
echo ""
echo "📋 Summary:"
echo "Frontend: $FRONTEND_UUID (my.doctorhealthy1.com)"
echo "Backend:  $BACKEND_UUID (backend.doctorhealthy1.com)"
echo "Monitoring: $MONITORING_UUID (monitor.doctorhealthy1.com)"
echo "Database: $DATABASE_UUID (PostgreSQL)"

# Save UUIDs for deployment
cat > application-uuids.txt << EOL
FRONTEND_UUID=$FRONTEND_UUID
BACKEND_UUID=$BACKEND_UUID
MONITORING_UUID=$MONITORING_UUID
DATABASE_UUID=$DATABASE_UUID
PROJECT_UUID=$PROJECT_UUID
SERVER_UUID=$SERVER_UUID
EOL

echo ""
echo "💾 UUIDs saved to application-uuids.txt"
echo "🌐 Access Coolify Dashboard: $COOLIFY_HOST"
echo "📚 Next: Configure applications and deploy from dashboard"
