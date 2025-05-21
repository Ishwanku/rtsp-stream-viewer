import { useEffect, useRef } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

function StreamPlayer({ stream }) {
  const videoRef = useRef(null);
  const playerRef = useRef(null);

  useEffect(() => {
    const baseUrl = process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : 'https://rtsp-stream-viewer-backend.vercel.app';
    const streamUrl = `${baseUrl}${stream.stream_url}`;
    console.log('Stream URL:', streamUrl);

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
        console.error('Video.js error:', playerRef.current.error());
      });
    }

    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [stream.stream_url]);

  return (
    <div className="border rounded overflow-hidden">
      <video ref={videoRef} className="video-js vjs-default-skin" controls />
    </div>
  );
}

export default StreamPlayer;