#!/bin/bash

echo "🚀 Starting Simple Email Tracker deployment..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Remove old images (optional)
echo "🧹 Cleaning up old images..."
docker system prune -f

# Build and start services
echo "🏗️ Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running!"
    echo ""
    echo "🌐 Application URLs:"
    echo "   Dashboard: http://localhost:5000"
    echo "   Admin:     http://localhost:5000/admin"
    echo ""
    echo "📊 Database:"
    echo "   MySQL:     localhost:3306"
    echo "   Database:  simple_tracker"
    echo "   Username:  tracker"
    echo "   Password:  tracker"
    echo ""
    echo "📝 To view logs: docker-compose logs -f"
    echo "🛑 To stop:     docker-compose down"
else
    echo "❌ Services failed to start. Check logs with: docker-compose logs"
    exit 1
fi