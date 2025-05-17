<!-- RTSP Stream Viewer
A web application to view RTSP streams, built with React.js (frontend) and Django (backend) for Skylark Labs' Full Stack Engineer Coding Test.
Project Structure

frontend/: React application deployed on Vercel.
backend/: Django application with FFmpeg, deployed on Vercel.

Setup Instructions
Prerequisites

Node.js and npm (v18+)
Python (v3.8+)
FFmpeg
Git
Vercel CLI
Redis (cloud-hosted, e.g., Upstash)

Local Development
Backend

Navigate to backend/:cd backend

Create a virtual environment and activate it:python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies:pip install -r requirements.txt

Set up environment variables in a .env file:SECRET_KEY=your-secret-key
DEBUG=True
REDIS_URL=redis://your-redis-url

Apply Django migrations:python manage.py migrate

Run the Django development server:python manage.py runserver

Frontend

Navigate to frontend/:cd frontend

Install dependencies:npm install

Start the development server:npm start

Deployment

Frontend: Deployed on Vercel.
Run vercel in the frontend/ directory.

Backend: Deployed on Vercel.
Run vercel in the backend/ directory.
Set environment variables in the Vercel dashboard.

Live Demo

Frontend: Vercel Frontend URL (to be updated)
Backend: Vercel Backend URL (to be updated)

Testing
Use public RTSP streams provided in the test document for testing. -->
