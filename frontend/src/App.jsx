import { useState } from 'react';
import StreamInput from './components/StreamInput';
import StreamPlayer from './components/StreamPlayer';
import './index.css';

function App() {
  const [streams, setStreams] = useState([]);

  const addStream = (streamData) => {
    setStreams([...streams, streamData]);
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">RTSP Stream Viewer</h1>
      <StreamInput onAddStream={addStream} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {streams.map((stream) => (
          <StreamPlayer key={stream.stream_id} stream={stream} />
        ))}
      </div>
    </div>
  );
}

export default App;