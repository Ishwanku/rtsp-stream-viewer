from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import ffmpeg
import os
import logging
import subprocess
import time
from decouple import config

logger = logging.getLogger(__name__)

class StreamView(APIView):
    def post(self, request):
        rtsp_url = request.data.get('rtsp_url')
        logger.info(f"Received RTSP URL: {rtsp_url}")
        if not rtsp_url:
            logger.error("RTSP URL is required")
            return Response({'error': 'RTSP URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Log FFmpeg version for debugging
            ffmpeg_path = './ffmpeg' if os.path.exists('./ffmpeg') else 'ffmpeg'
            try:
                version = subprocess.check_output([ffmpeg_path, '-version'], stderr=subprocess.STDOUT).decode()
                logger.info(f"FFmpeg version: {version.splitlines()[0]}")
            except Exception as e:
                logger.warning(f"Could not verify FFmpeg version: {str(e)}")

            # Validate RTSP URL by probing
            logger.info("Probing RTSP URL")
            probe = ffmpeg.probe(rtsp_url, rtsp_transport='tcp', timeout=60000000, user_agent='FFmpeg')
            logger.info(f"Probe result: {probe}")
            
            # Generate a unique stream ID
            stream_id = os.urandom(16).hex()
            output_path = f'static/streams/{stream_id}/index.m3u8'
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.info(f"Output path: {output_path}")
            
            # Start FFmpeg process to convert RTSP to HLS
            logger.info("Starting FFmpeg process")
            stream = (
                ffmpeg
                .input(rtsp_url, rtsp_transport='tcp', timeout=60000000, user_agent='FFmpeg')
                .output(output_path, format='hls', hls_time=10, hls_list_size=3, hls_segment_filename=f'static/streams/{stream_id}/%03d.ts', vcodec='libx264', acodec='aac', preset='ultrafast', loglevel='verbose')
                .run_async(pipe_stderr=True, cmd=ffmpeg_path)
            )
            # Wait for index.m3u8 to be generated
            timeout = 60  # seconds
            start_time = time.time()
            while not os.path.exists(output_path):
                if time.time() - start_time > timeout:
                    stream.terminate()
                    logger.error("Timeout waiting for index.m3u8")
                    return Response({'error': 'FFmpeg failed to generate HLS playlist within timeout'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                time.sleep(1)
            
            # Read FFmpeg stderr for errors
            stderr = stream.stderr.read(4096).decode()
            if stderr and ("Error" in stderr or "fail" in stderr.lower()):
                logger.error(f"FFmpeg stderr: {stderr}")
                stream.terminate()
                return Response({'error': f'FFmpeg error: {stderr}'}, status=status.HTTP_400_BAD_REQUEST)
            logger.info(f"FFmpeg stderr: {stderr}")
            
            stream_url = f'/static/streams/{stream_id}/index.m3u8'
            logger.info(f"Stream URL generated: {stream_url}")
            return Response({
                'stream_id': stream_id,
                'stream_url': stream_url
            }, status=status.HTTP_200_OK)
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg error: {error_msg}")
            return Response({'error': f'FFmpeg failed: {error_msg}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response({'error': 'Server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestRTSPView(APIView):
    def get(self, request):
        rtsp_url = request.query_params.get('rtsp_url', 'rtsp://admin:admin123@49.248.155.178:555/cam/realmonitor?channel=1&subtype=0')
        try:
            probe = ffmpeg.probe(rtsp_url, rtsp_transport='tcp', timeout=60000000, user_agent='FFmpeg')
            return Response({'probe': probe}, status=status.HTTP_200_OK)
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            return Response({'error': f'FFmpeg failed: {error_msg}'}, status=status.HTTP_400_BAD_REQUEST)