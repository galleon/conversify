# Avatar UI Docker Setup

This document explains how to run the Avatar UI component using Docker and docker-compose.

## Overview

The Avatar UI is a Next.js application that provides a web interface for interacting with the Conversify voice agent. It runs on port 3000 and connects to LiveKit for real-time communication.

## Quick Start

1. **Set up environment variables** (see Environment Variables section below)
2. **Run with docker-compose**:
   ```bash
   # From the project root
   docker-compose -f docker-compose.cpu.yml up avatar-ui

   # Or build and run everything including UI
   docker-compose -f docker-compose.cpu.yml up
   ```
3. **Access the UI** at http://localhost:3000

## Environment Variables

The Avatar UI requires LiveKit credentials to function. These should be set in your environment or `.env.local` file.

### Required Variables

Create `conversify/.env.local` (or set in your environment) with:

```bash
# LiveKit Server Configuration
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
```

### Optional Variables

```bash
# App Configuration
NEXT_PUBLIC_APP_CONFIG_ENDPOINT=http://localhost:8080/config
NEXT_PUBLIC_CONN_DETAILS_ENDPOINT=/api/connection-details
SANDBOX_ID=your_sandbox_id
```

## Docker Setup

### Dockerfile

The UI uses a multi-stage Docker build:

1. **Dependencies stage**: Installs npm/pnpm dependencies
2. **Builder stage**: Builds the Next.js application
3. **Runner stage**: Creates optimized production image

### Build Process

```bash
# Build the UI image
docker build -t conversify-ui ./avatar-ui

# Or use docker-compose
docker-compose -f docker-compose.cpu.yml build avatar-ui
```

### Standalone Output

The Next.js app is configured with `output: 'standalone'` for optimal Docker deployment. This creates a self-contained server bundle.

## Development vs Production

### Development

For local development outside Docker:

```bash
cd avatar-ui
pnpm install
pnpm dev
```

Create `avatar-ui/.env.local` with your LiveKit credentials.

### Production (Docker)

The Docker setup uses environment variables passed through docker-compose, allowing you to keep credentials in the main `.env.local` file at the project root.

## Network Architecture

```
Browser (localhost:3000)
    ↓
Avatar UI Container (port 3000)
    ↓
LiveKit Server (LIVEKIT_URL)
    ↓
Conversify Agent (port 8080)
```

## Troubleshooting

### Common Issues

1. **"waiting for video and audio track"**
   - Check LiveKit credentials are correct
   - Ensure LIVEKIT_URL is accessible from the container
   - Verify the Conversify agent is running and connected to the same LiveKit server

2. **Connection refused errors**
   - Check that LIVEKIT_URL uses the correct protocol (ws:// or wss://)
   - Ensure LiveKit server is running and accessible
   - For local development, use `host.docker.internal` instead of `localhost` in Docker

3. **Build failures**
   - Ensure you have the correct Node.js version (20+)
   - Clear Docker cache: `docker builder prune`
   - Check that all required files are present and not excluded by .dockerignore

### Debug Mode

Enable debug logging by setting `NODE_ENV=development` in the environment variables or by modifying the `useDebugMode` hook.

### Logs

View UI logs:
```bash
docker-compose -f docker-compose.cpu.yml logs avatar-ui
```

## Integration with Main Application

The Avatar UI integrates with the Conversify system through:

1. **LiveKit Room Connection**: Connects to the same LiveKit room as the agent
2. **API Endpoints**: Uses `/api/connection-details` to get room tokens
3. **Environment Sharing**: Shares LiveKit credentials with the main application

## Security Notes

- Never commit `.env.local` files to version control
- Use strong, unique API keys for production
- Consider using Docker secrets for sensitive credentials in production
- The UI exposes LiveKit credentials to the browser, ensure your LiveKit server is properly secured

## Customization

- Modify `app-config.ts` to change default settings
- Update theme colors in `lib/types.ts`
- Customize UI components in the `components/` directory
- Add new environment variables in the docker-compose files as needed
