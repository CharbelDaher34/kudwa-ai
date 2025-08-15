# Render.com Deployment Guide

This project is configured to deploy on Render.com using the `render.yaml` file. The application consists of three main components:

## Services

### 1. Database (PostgreSQL)
- **Name**: `kudwa-postgres`
- **Type**: PostgreSQL database
- **Plan**: Starter (free tier)

### 2. Backend API (FastAPI)
- **Name**: `kudwa-backend` 
- **Type**: Web service
- **Runtime**: Docker
- **Port**: 8430
- **Dockerfile**: `Dockerfile.backend`

### 3. Frontend (Streamlit)
- **Name**: `kudwa-frontend`
- **Type**: Web service  
- **Runtime**: Docker
- **Port**: 8431
- **Dockerfile**: `Dockerfile.frontend`

## Deployment Steps

1. **Fork or clone this repository** to your GitHub account

2. **Connect to Render.com**:
   - Go to [Render.com](https://render.com)
   - Sign up or log in
   - Connect your GitHub account

3. **Create a new service**:
   - Click "New +" and select "Blueprint"
   - Connect your repository
   - Render will automatically detect the `render.yaml` file

4. **Set environment variables** in the Render dashboard:
   - Navigate to your backend service settings
   - Add the following environment variables:
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `GEMINI_API_KEY`: Your Google Gemini API key  
     - `GOOGLE_API_KEY`: Your Google API key

5. **Deploy**:
   - Render will automatically deploy all services
   - The database will be created first
   - Then the backend API will be deployed
   - Finally, the frontend will be deployed

## Service Architecture

```
Frontend (Streamlit) → Backend (FastAPI) → Database (PostgreSQL)
```

- The frontend communicates with the backend via REST API
- The backend handles data processing and database operations
- All services are interconnected using Render's service discovery

## Environment Variables

### Backend Service
- `DATABASE_URL`: Automatically provided by Render from the PostgreSQL service
- `OPENAI_API_KEY`: Must be set manually
- `GEMINI_API_KEY`: Must be set manually  
- `GOOGLE_API_KEY`: Must be set manually

### Frontend Service
- `API_BASE_URL`: Automatically provided by Render from the backend service

## Important Notes

1. **Database Migration**: The application automatically creates tables and ingests initial data on first startup

2. **API Keys**: You must manually set your API keys in the Render dashboard after deployment

3. **Service Dependencies**: The frontend depends on the backend, which depends on the database. Render handles this automatically.

4. **Free Tier Limitations**: 
   - Services may spin down after inactivity
   - Database storage is limited
   - Consider upgrading for production use

## Troubleshooting

- Check service logs in the Render dashboard
- Ensure all environment variables are properly set
- Verify that your API keys are valid
- Monitor service health using the provided health check endpoints

## Local Development

For local development, use Docker Compose:
```bash
docker-compose up
```

This will start all services locally with the configuration in `docker-compose.yml`.
