import { useEffect, useRef, useState } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

function StreamPlayer({ stream }) {
  const videoRef = useRef(null);
  const playerRef = useRef(null);
  const [status, setStatus] = useState('connecting');
  const [error, setError] = useState('');

  useEffect(() => {
    const defaultBackendUrl = import.meta.env.DEV ? 'http://localhost:8000' : 'https://rtsp-stream-viewer-backend.vercel.app';
    const baseUrl = import.meta.env.VITE_BACKEND_URL || defaultBackendUrl;
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
    if (!playerRef.current) {
      const videoElement = videoRef.current;
      const player = videojs(videoElement, {
        autoplay: true,
        controls: true,
        responsive: true,
        fluid: true,
        liveui: true,
        html5: {
          hls: {
            enableLowInitialPlaylist: true,
            smoothQualityChange: true,
            overrideNative: true
          }
        },
        sources: [{
          src: streamUrl,
          type: 'application/x-mpegURL'
        }],
        errorDisplay: true
      }, () => {
        console.log('Video.js player initialized');
        player.on('error', () => {
          const err = player.error();
          console.error('Video.js error:', err);
          setStatus('failed');
          setError(err.message || 'Failed to play stream');
        });

        player.on('waiting', () => {
          console.log('Video is waiting for data');
          setStatus('buffering');
        });

        player.on('playing', () => {
          console.log('Video is playing');
          setStatus('connected');
        });

        player.on('stalled', () => {
          console.log('Video playback stalled');
          setStatus('buffering');
        });

        playerRef.current = player;
      });
    }

    return () => {
      ws.close();
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [stream.stream_id, stream.stream_url]);

  return (
    <div className="border rounded overflow-hidden relative bg-black">
      <video 
        ref={videoRef} 
        className="video-js vjs-default-skin vjs-big-play-centered" 
        controls 
        playsInline
      />
      <div
        className={`absolute top-2 left-2 text-white p-1 px-2 rounded text-sm ${
          status === 'connecting' ? 'bg-blue-500' :
          status === 'buffering' ? 'bg-yellow-500' :
          status === 'connected' ? 'bg-green-500' :
          status === 'failed' ? 'bg-red-500' :
          status === 'stopped' ? 'bg-gray-500' :
          'bg-black bg-opacity-50'
        }`}
      >
        {status === 'connecting' && 'Connecting...'}
        {status === 'buffering' && 'Buffering...'}
        {status === 'connected' && 'Connected'}
        {status === 'failed' && `Error: ${error || 'Unknown error'}`}
        {status === 'stopped' && 'Stream Stopped'}
      </div>
    </div>
  );
}

export default StreamPlayer;