import { useState } from 'react';

function AddStreamForm({ onAddStream }) {
  const [rtspUrl, setRtspUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!rtspUrl.trim() || isLoading) return;
    // Basic validation for RTSP URL format (can be improved)
    if (!rtspUrl.startsWith('rtsp://')) {
      alert('Invalid RTSP URL. It should start with rtsp://');
      return;
    }
    setIsLoading(true);
    const success = await onAddStream(rtspUrl); // Call onAddStream and wait for its result
    if (success) {
      setRtspUrl(''); // Clear input only on success
    }
    setIsLoading(false);
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4 p-4 bg-gray-100 rounded shadow">
      <div className="flex items-center">
        <input
          type="text"
          value={rtspUrl}
          onChange={(e) => setRtspUrl(e.target.value)}
          placeholder="Enter RTSP Stream URL (e.g., rtsp://...)"
          className="flex-grow p-2 border rounded-l focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={isLoading}
        />
        <button 
          type="submit"
          className={`bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-r focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            isLoading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          disabled={isLoading}
        >
          {isLoading ? 'Adding...' : 'Add Stream'}
        </button>
      </div>
    </form>
  );
}

export default AddStreamForm; 