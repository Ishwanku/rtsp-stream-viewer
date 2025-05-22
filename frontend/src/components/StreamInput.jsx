import { useState } from 'react';
import axios from 'axios';

function StreamInput({ onAddStream }) {
  const [rtspUrl, setRtspUrl] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isLoading) return;
    setIsLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/api/stream/', { rtsp_url: rtspUrl });
      console.log('API Response:', response.data);
      onAddStream(response.data);
      setRtspUrl('');
      setError('');
    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Failed to add stream. Please check the URL or network.';
      setError(errorMsg);
      console.error('Stream error:', errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4">
      <div className="flex flex-col">
        <input
          type="text"
          value={rtspUrl}
          onChange={(e) => setRtspUrl(e.target.value)}
          placeholder="Enter RTSP URL"
          className="border p-2 rounded mb-2"
          disabled={isLoading}
        />
        <button
          type="submit"
          className={`p-2 rounded ${isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-500 text-white'}`}
          disabled={isLoading}
        >
          {isLoading ? 'Adding...' : 'Add Stream'}
        </button>
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </div>
    </form>
  );
}

export default StreamInput;