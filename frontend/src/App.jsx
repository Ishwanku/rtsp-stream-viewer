import { useState } from 'react';
import AddStreamForm from './components/AddStreamForm';
import StreamPlayer from './components/StreamPlayer';
import './index.css';
import axios from 'axios';

function App() {
  const [streams, setStreams] = useState([]);
  const [error, setError] = useState('');

  const defaultBackendUrl = import.meta.env.DEV ? 'http://localhost:8000' : 'https://rtsp-stream-viewer-backend.vercel.app';
  const backendUrl = import.meta.env.VITE_BACKEND_URL || defaultBackendUrl;

  const addStream = async (rtspUrl) => {
    setError('');
    try {
      const response = await axios.post(`${backendUrl}/api/stream/start/`, { rtsp_url: rtspUrl });
      
      if (response.data && response.data.stream_id && response.data.stream_url) {
        if (!streams.find(s => s.stream_id === response.data.stream_id)) {
            setStreams(prevStreams => [...prevStreams, response.data]);
        } else {
            console.warn(`Stream ${response.data.stream_id} already exists.`);
        }
        return true;
      } else {
        console.error('Invalid response from backend when adding stream:', response.data);
        setError('Failed to start stream: Invalid response from backend.');
        return false;
      }
    } catch (err) {
      console.error('Error adding stream:', err);
      setError(err.response?.data?.error || err.message || 'Failed to add stream. Check console for details.');
      return false;
    }
  };

  const removeStream = async (streamId) => {
    try {
      await axios.post(`${backendUrl}/api/stream/stop/`, { stream_id: streamId });
      setStreams(streams.filter((stream) => stream.stream_id !== streamId));
    } catch (err) {
      console.error('Error stopping stream:', err);
    }
  };

  return (
    <div className="container mx-auto p-4 font-sans">
      <header className="mb-6 text-center">
        <h1 className="text-4xl font-bold text-gray-800">RTSP Stream Viewer</h1>
      </header>
      
      <AddStreamForm onAddStream={addStream} />
      
      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 border border-red-400 rounded">
          <p><strong>Error:</strong> {error}</p>
        </div>
      )}

      {streams.length === 0 && !error && (
        <div className="text-center text-gray-500 mt-8">
            <p>No streams added yet. Use the form above to add your first RTSP stream.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {streams.map((stream) => (
          <div key={stream.stream_id} className="relative bg-white shadow-lg rounded-lg overflow-hidden">
            <StreamPlayer stream={stream} />
            <button
              onClick={() => removeStream(stream.stream_id)}
              className="absolute top-3 right-3 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold py-1 px-2 rounded-full shadow focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50 transition-colors duration-150 ease-in-out"
              title="Remove Stream"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;