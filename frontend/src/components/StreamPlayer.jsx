import { useEffect, useRef } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

function StreamPlayer({ stream }) {
  const videoRef = useRef(null);
  const playerRef = useRef(null);

  useEffect(() => {
    if (!playerRef.current) {
      const videoElement = videoRef.current;
      playerRef.current = videojs(videoElement, {
        autoplay: true,
        controls: true,
        sources: [{
          src: stream.stream_url,
          type: 'application/x-mpegURL'
        }]
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