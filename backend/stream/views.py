from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import ffmpeg
import os
import logging
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
            # Validate RTSP URL by probing
            logger.info("Probing RTSP URL")
            probe = ffmpeg.probe(rtsp_url, rtsp_transport='tcp', timeout=30000000, user_agent='FFmpeg')
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
                .input(rtsp_url, rtsp_transport='tcp', timeout=30000000, user_agent='FFmpeg')
                .output(output_path, format='hls', hls_time=10, hls_list_size=3, hls_segment_filename=f'static/streams/{stream_id}/%03d.ts', vcodec='libx264', acodec='aac', preset='ultrafast')
                .run_async(pipe_stderr=True)
            )
            # Read initial stderr to catch early errors
            stderr = stream.stderr.read(1024).decode()
            if stderr:
                logger.error(f"FFmpeg initial stderr: {stderr}")
                if "Connection to" in stderr or "Error number -138" in stderr:
                    return Response({'error': 'Failed to connect to RTSP server. Check URL or network.'}, status=status.HTTP_400_BAD_REQUEST)
            
            stream_url = f'/static/streams/{stream_id}/index.m3u8'
            logger.info(f"Stream URL generated: {stream_url}")
            return Response({
                'stream_id': stream_id,
                'stream_url': stream_url
            }, status=status.HTTP_200_OK)
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg error: {error_msg}")
            if "Connection to" in error_msg or "Error number -138" in error_msg:
                error_msg = 'Failed to connect to RTSP server. Check URL or network.'
            return Response({'error': f'FFmpeg failed: {error_msg}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response({'error': 'Server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestRTSPView(APIView):
    def get(self, request):
        rtsp_url = request.query_params.get('rtsp_url', 'rtsp://freja.hiof.no:1935/rtplive/definst/hessdalen03.stream')
        try:
            probe = ffmpeg.probe(rtsp_url, rtsp_transport='tcp', timeout=30000000, user_agent='FFmpeg')
            return Response({'probe': probe}, status=status.HTTP_200_OK)
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            if "Connection to" in error_msg or "Error number -138" in error_msg:
                error_msg = 'Failed to connect to RTSP server. Check URL or network.'
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)