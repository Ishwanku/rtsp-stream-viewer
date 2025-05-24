import os
import uuid
import ffmpeg
import redis
import boto3
import logging
import subprocess
import time
import platform
from urllib.parse import unquote
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from decouple import config

logger = logging.getLogger(__name__)
# Set logging level to DEBUG for more detailed output
logger.setLevel(logging.DEBUG)

class StreamView(APIView):
    def post(self, request):
        rtsp_url = request.data.get('rtsp_url')
        logger.info(f"Received RTSP URL: {rtsp_url}")
        if not rtsp_url:
            logger.error("RTSP URL is required")
            return Response({'error': 'RTSP URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Decode URL if it's encoded
        rtsp_url = unquote(rtsp_url)
        logger.debug(f"Decoded RTSP URL: {rtsp_url}")
        
        try:
            # Determine FFmpeg path (Windows compatibility)
            ffmpeg_path = './ffmpeg.exe' if os.path.exists('./ffmpeg.exe') else 'ffmpeg'
            logger.debug(f"Using FFmpeg path: {ffmpeg_path}")
            
            # Generate a unique stream ID
            stream_id = str(uuid.uuid4())
            stream_dir = os.path.join(settings.MEDIA_ROOT, 'streams', stream_id)
            os.makedirs(stream_dir, exist_ok=True)
            output_path = os.path.join(stream_dir, 'index.m3u8')
            logger.debug(f"Created stream directory: {stream_dir}")
            
            try:
                # Test RTSP connection first using direct FFmpeg command
                logger.info("Testing RTSP connection...")
                test_result = subprocess.run(
                    [ffmpeg_path, '-rtsp_transport', 'tcp', '-i', rtsp_url, '-t', '1', '-f', 'null', '-'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=15
                )
                if test_result.returncode != 0:
                    error_msg = test_result.stderr.decode()
                    logger.error(f"RTSP connection test failed: {error_msg}")
                    return Response({'error': f'Failed to connect to RTSP stream: {error_msg}'}, status=status.HTTP_400_BAD_REQUEST)
                logger.info("RTSP connection test successful")
            except subprocess.TimeoutExpired:
                logger.error("RTSP connection test timed out")
                return Response({'error': 'Connection timeout'}, status=status.HTTP_408_REQUEST_TIMEOUT)
            except Exception as e:
                logger.error(f"Error testing RTSP connection: {str(e)}")
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Start FFmpeg process to convert RTSP to HLS
            logger.info("Starting FFmpeg process")
            try:
                stream = (
                    ffmpeg
                    .input(
                        rtsp_url,
                        rtsp_transport='tcp',
                        analyzeduration='1000000',  # Reduced from 10000000
                        probesize='1000000',        # Reduced from 10000000
                        timeout='10000000',         # Reduced from 60000000
                        user_agent='FFmpeg',
                        loglevel='debug',
                        reorder_queue_size='0',     # Disable reordering
                        max_delay='500000',         # Maximum delay in microseconds
                        flags='low_delay'           # Enable low delay mode
                    )
                    .output(
                        output_path,
                        format='hls',
                        hls_time=1,                 # Reduced segment time
                        hls_list_size=2,            # Reduced list size
                        hls_flags='delete_segments+append_list',  # Added append_list
                        hls_segment_filename=os.path.join(stream_dir, '%03d.ts'),
                        vcodec='libx264',
                        acodec='aac',
                        preset='ultrafast',
                        tune='zerolatency',
                        vsync='1',
                        g=15,                       # Reduced GOP size
                        keyint_min=15,              # Minimum keyframe interval
                        sc_threshold=0,             # Scene change threshold
                        bf=0,                       # No B-frames
                        maxrate='1000k',            # Maximum bitrate
                        bufsize='2000k',            # Buffer size
                        threads=4,                  # Number of threads
                        fflags='nobuffer+fastseek', # Disable buffering
                        flags='low_delay'           # Enable low delay mode
                    )
                    .overwrite_output()
                    .run_async(pipe_stderr=True, cmd=ffmpeg_path)
                )
            except ffmpeg.Error as e:
                error_msg = e.stderr.decode() if e.stderr else str(e)
                logger.error(f"FFmpeg error while starting stream: {error_msg}")
                return Response({'error': f'Failed to start stream: {error_msg}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Store process ID in memory
            if not hasattr(StreamView, '_processes'):
                StreamView._processes = {}
            StreamView._processes[stream_id] = stream.pid
            logger.debug(f"Started FFmpeg process with PID: {stream.pid}")

            # Wait for index.m3u8 to be generated
            timeout = 15  # reduced timeout to 15 seconds
            start_time = time.time()
            while not os.path.exists(output_path):
                if time.time() - start_time > timeout:
                    stream.terminate()
                    if stream_id in StreamView._processes:
                        del StreamView._processes[stream_id]
                    logger.error("Timeout waiting for index.m3u8")
                    # Clean up stream directory
                    try:
                        for file in os.listdir(stream_dir):
                            os.remove(os.path.join(stream_dir, file))
                        os.rmdir(stream_dir)
                    except Exception as e:
                        logger.error(f"Error cleaning up stream directory: {str(e)}")
                    return Response({'error': 'FFmpeg failed to generate HLS playlist within timeout'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                time.sleep(0.1)  # Reduced sleep time
                # Check if FFmpeg process is still running
                if stream.poll() is not None:
                    stderr_output = stream.stderr.read().decode() if stream.stderr else "No error output available"
                    logger.error(f"FFmpeg process exited prematurely. Error: {stderr_output}")
                    return Response({'error': f'FFmpeg process failed: {stderr_output}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            logger.info(f"HLS playlist generated: {output_path}")

            # Notify frontend via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'streams', {'type': 'stream_update', 'stream_id': stream_id, 'status': 'connected'}
            )
            logger.debug("Sent WebSocket notification")

            stream_url = f'{settings.HLS_URL}{stream_id}/index.m3u8'
            logger.info(f"Stream URL generated: {stream_url}")
            return Response({
                'stream_id': stream_id,
                'stream_url': stream_url
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestRTSPView(APIView):
    def get(self, request):
        rtsp_url = request.query_params.get('rtsp_url')
        if not rtsp_url:
            return Response({'error': 'RTSP URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ffmpeg_path = './ffmpeg.exe' if os.path.exists('./ffmpeg.exe') else 'ffmpeg'
            # Test RTSP connection using FFmpeg directly
            result = subprocess.run(
                [ffmpeg_path, '-rtsp_transport', 'tcp', '-i', rtsp_url, '-t', '1', '-f', 'null', '-'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10
            )
            if result.returncode == 0:
                return Response({'status': 'success'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': result.stderr.decode()}, status=status.HTTP_400_BAD_REQUEST)
        except subprocess.TimeoutExpired:
            return Response({'error': 'Connection timeout'}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StopStreamView(APIView):
    def post(self, request):
        stream_id = request.data.get('stream_id')
        if not stream_id:
            return Response({'error': 'Stream ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if hasattr(StreamView, '_processes') and stream_id in StreamView._processes:
                pid = StreamView._processes[stream_id]
                if platform.system() == 'Windows':
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True)
                else:
                    subprocess.run(['kill', '-9', str(pid)], check=True)
                del StreamView._processes[stream_id]
                
                # Clean up stream directory
                stream_dir = os.path.join(settings.MEDIA_ROOT, 'streams', stream_id)
                if os.path.exists(stream_dir):
                    for file in os.listdir(stream_dir):
                        os.remove(os.path.join(stream_dir, file))
                    os.rmdir(stream_dir)

                # Notify frontend
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    'streams', {'type': 'stream_update', 'stream_id': stream_id, 'status': 'stopped'}
                )
                return Response({'message': f'Stream {stream_id} stopped'}, status=status.HTTP_200_OK)
            return Response({'error': 'Stream not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error stopping stream {stream_id}: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)