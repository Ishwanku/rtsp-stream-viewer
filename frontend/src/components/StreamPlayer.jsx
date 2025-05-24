import { useEffect, useRef, useState } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

function StreamPlayer({ stream }) {
  const videoRef = useRef(null);
  const playerRef = useRef(null);
  const [status, setStatus] = useState('connecting');
  const [error, setError] = useState('');

  useEffect(() => {
    const baseUrl = import.meta.env.VITE_BACKEND_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : 'https://rtsp-stream-viewer-backend.vercel.app');
    const streamUrl = stream.stream_url;
    console.log('Stream URL:', streamUrl);

    // Initialize WebSocket
    const ws = new WebSocket(baseUrl.replace('http', 'ws').replace('https', 'wss') + '/ws/streams/');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.stream_id === stream.stream_id) {
        setStatus(data.status);
        setError(data.error || '');
      }
    };
    ws.onclose = () => console.log('WebSocket closed');

    // Initialize Video.js player
    const timer = setTimeout(() => {
      if (!playerRef.current) {
        const videoElement = videoRef.current;
        playerRef.current = videojs(videoElement, {
          autoplay: true,
          controls: true,
          sources: [{
            src: streamUrl,
            type: 'application/x-mpegURL'
          }],
          errorDisplay: true
        }, () => {
          console.log('Video.js player initialized');
        });

        playerRef.current.on('error', () => {
          const err = playerRef.current.error();
          console.error('Video.js error:', err);
          setStatus('failed');
          setError(err.message || 'Failed to play stream');
        });
      }
    }, 2000);

    return () => {
      clearTimeout(timer);
      ws.close();
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [stream.stream_id, stream.stream_url]);

  return (
    <div className="border rounded overflow-hidden relative">
      <video ref={videoRef} className="video-js vjs-default-skin" controls />
      <div className="absolute top-2 left-2 bg-black bg-opacity-50 text-white p-1 rounded">
        {status === 'connecting' && 'Connecting...'}
        {status === 'connected' && 'Connected'}
        {status === 'failed' && `Failed: ${error}`}
        {status === 'stopped' && 'Stream Stopped'}
      </div>
    </div>
  );
}

export default StreamPlayer;