# RTSP Stream Viewer

A web application to view RTSP streams, built with React.js (frontend) and Django (backend) for Skylark Labs' Full Stack Engineer Coding Test.

## Project Structure

- `frontend/`: React application deployed on Vercel.
- `backend/`: Django application with FFmpeg, deployed on Vercel.

## Features

- Add RTSP streams via URL.
- Display multiple streams in a responsive grid.
- Play/pause controls with Video.js.
- Real-time stream status via WebSockets.
- HLS streaming with AWS S3 storage.
- Stream removal and resource cleanup.

## Prerequisites

- Node.js and npm (v18+)
- Python (v3.8+)
- FFmpeg
- Git
- Vercel CLI
- Redis (e.g., Upstash)
- AWS S3 bucket
- AWS IAM credentials

## Local Development

### Backend

1. Navigate to `backend/`:

   ```bash
   cd backend
