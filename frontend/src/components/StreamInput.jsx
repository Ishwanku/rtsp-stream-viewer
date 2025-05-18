import { useState } from "react";
import axios from "axios";

function StreamInput({ onAddStream }) {
  const [rtspUrl, setRtspUrl] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('http://localhost:8000/api/stream/', { rtsp_url: rtspUrl });
      onAddStream(response.data);
      setRtspUrl("");
      setError("");
    } catch (err) {
      if (err.response && err.response.status === 400) {
        setError("Invalid RTSP URL");
      } else {
        setError("An error occurred while adding the stream");
      }
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
        />
        <button type="submit" className="bg-blue-500 text-white p-2 rounded">
          Add Stream
        </button>
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </div>
    </form>
  );
}

export default StreamInput;
