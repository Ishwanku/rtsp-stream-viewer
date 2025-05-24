import { useState } from 'react';
import StreamInput from './components/StreamInput';
import StreamPlayer from './components/StreamPlayer';
import './index.css';
import axios from 'axios';

function App() {
  const [streams, setStreams] = useState([]);

  const addStream = (streamData) => {
    setStreams([...streams, streamData]);
  };

  const removeStream = async (streamId) => {
    try {
      await axios.post(`${import.meta.env.VITE_BACKEND_URL}/api/stream/stop-stream/`, { stream_id: streamId });
      setStreams(streams.filter((stream) => stream.stream_id !== streamId));
    } catch (err) {
      console.error('Error stopping stream:', err);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">RTSP Stream Viewer</h1>
      <StreamInput onAddStream={addStream} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {streams.map((stream) => (
          <div key={stream.stream_id} className="relative">
            <StreamPlayer stream={stream} />
            <button
              onClick={() => removeStream(stream.stream_id)}
              className="absolute top-2 right-2 bg-red-500 text-white p-1 rounded"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;