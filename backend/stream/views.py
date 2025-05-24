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

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ffmpeg.log')
    ]
)

logger = logging.getLogger(__name__)
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
            ffmpeg_path = os.path.abspath('./ffmpeg.exe') if os.path.exists('./ffmpeg.exe') else 'ffmpeg'
            logger.debug(f"Using FFmpeg path: {ffmpeg_path}")
            
            # Generate a unique stream ID and create absolute paths
            stream_id = str(uuid.uuid4())
            stream_dir = os.path.abspath(os.path.join(settings.MEDIA_ROOT, 'streams', stream_id))
            # Output paths will now be relative to stream_dir when used in FFmpeg command with cwd=stream_dir
            ffmpeg_output_playlist = 'index.m3u8'
            ffmpeg_segment_pattern = '%03d.ts'
            
            logger.info(f"Stream directory (absolute): {stream_dir}")
            # logger.info(f"Output path (absolute): {output_path}") # No longer the primary ffmpeg output path variable
            # logger.info(f"Segment pattern (absolute): {segment_pattern}") # No longer the primary ffmpeg segment pattern variable
            
            # Ensure parent directories exist
            os.makedirs(os.path.dirname(stream_dir), exist_ok=True)
            
            # Create stream directory with explicit permissions
            try:
                if os.path.exists(stream_dir):
                    logger.warning(f"Stream directory already exists: {stream_dir}")
                    # Clean up existing directory
                    for file in os.listdir(stream_dir):
                        os.remove(os.path.join(stream_dir, file))
                else:
                    os.makedirs(stream_dir, exist_ok=True)
                    logger.info(f"Created stream directory: {stream_dir}")
                
                # Verify directory permissions
                if not os.access(stream_dir, os.W_OK):
                    logger.error(f"No write permission for directory: {stream_dir}")
                    return Response({'error': 'No write permission for stream directory'}, 
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            except Exception as e:
                logger.error(f"Error creating/verifying stream directory: {str(e)}")
                return Response({'error': f'Failed to create stream directory: {str(e)}'}, 
                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                # Test RTSP connection first using direct FFmpeg command
                logger.info("Testing RTSP connection...")
                test_cmd = [ffmpeg_path, '-rtsp_transport', 'tcp', '-i', rtsp_url, '-t', '1', '-f', 'null', '-']
                logger.debug(f"Test command: {' '.join(test_cmd)}")
                
                test_result = subprocess.run(
                    test_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5  # Reduced timeout to 5 seconds
                )
                
                if test_result.returncode != 0:
                    error_msg = test_result.stderr.decode()
                    logger.error(f"RTSP connection test failed: {error_msg}")
                    # Check for specific error messages
                    if "Failed to resolve hostname" in error_msg:
                        return Response({'error': 'Failed to resolve RTSP server hostname. Please check the URL and network connection.'}, 
                                     status=status.HTTP_400_BAD_REQUEST)
                    elif "Connection refused" in error_msg:
                        return Response({'error': 'Connection refused by RTSP server. Please check if the server is running and accessible.'}, 
                                     status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({'error': f'Failed to connect to RTSP stream: {error_msg}'}, 
                                     status=status.HTTP_400_BAD_REQUEST)
                logger.info("RTSP connection test successful")
            except subprocess.TimeoutExpired:
                logger.error("RTSP connection test timed out")
                return Response({'error': 'Connection timeout. The RTSP server is not responding. Please check if the URL is correct and the server is accessible.'}, 
                             status=status.HTTP_408_REQUEST_TIMEOUT)
            except Exception as e:
                logger.error(f"Error testing RTSP connection: {str(e)}")
                return Response({'error': f'Error connecting to RTSP stream: {str(e)}'}, 
                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Start FFmpeg process to convert RTSP to HLS
            logger.info("Starting FFmpeg process")
            try:
                # Build FFmpeg command with absolute paths for input, relative for output (due to cwd)
                ffmpeg_cmd = [
                    ffmpeg_path,
                    '-rtsp_transport', 'tcp',
                    '-analyzeduration', '1000000',  # Increased analyze duration
                    '-probesize', '1000000',        # Increased probe size
                    '-timeout', '5000000',
                    '-i', rtsp_url, # rtsp_url is already absolute or fully qualified
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-tune', 'zerolatency',
                    '-g', '15',
                    '-keyint_min', '15',
                    '-sc_threshold', '0',
                    '-bf', '0',
                    '-maxrate', '500k',
                    '-bufsize', '1000k',
                    '-s', '640x360',
                    '-r', '15',
                    '-threads', '4',
                    '-f', 'hls',
                    '-hls_time', '2',
                    '-hls_list_size', '3',
                    '-hls_flags', 'delete_segments+append_list+independent_segments+program_date_time',
                    '-hls_segment_type', 'mpegts',
                    '-hls_playlist_type', 'event',
                    '-hls_segment_filename', ffmpeg_segment_pattern, # Use relative pattern
                    '-hls_init_time', '1', # This causes a warning, consider removing if issues persist
                    '-hls_start_number_source', 'datetime',
                    '-hls_allow_cache', '0',
                    # Redundant HLS flags removed below
                    # '-hls_segment_type', 'mpegts',
                    # '-hls_playlist_type', 'event',
                    # '-hls_flags', 'delete_segments+append_list+independent_segments+program_date_time',
                    ffmpeg_output_playlist # Use relative playlist path
                ]
                logger.debug(f"Full FFmpeg command: {' '.join(ffmpeg_cmd)}")

                # Start FFmpeg process
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    cwd=stream_dir  # Set working directory to stream_dir
                )
                
                logger.info(f"FFmpeg process started with PID: {process.pid}")
                
                # Store process ID in memory
                if not hasattr(StreamView, '_processes'):
                    StreamView._processes = {}
                StreamView._processes[stream_id] = process.pid
                logger.debug(f"Started FFmpeg process with PID: {process.pid}")

                # Wait for index.m3u8 or .ts segments to be generated
                timeout = 45  # increased timeout to 45 seconds
                start_time = time.time()
                logger.info(f"Waiting for index.m3u8 or .ts segments to be generated (timeout: {timeout}s)")
                
                def stream_ready():
                    # Check for playlist or at least one segment using paths relative to stream_dir
                    # but os.path.exists needs absolute paths or paths relative to Django's CWD.
                    # So we construct absolute paths for checking here.
                    absolute_output_playlist = os.path.join(stream_dir, ffmpeg_output_playlist)
                    if os.path.exists(absolute_output_playlist) and os.path.getsize(absolute_output_playlist) > 0:
                        logger.info(f"Found playlist file: {absolute_output_playlist}")
                        return True
                    tmp_path = absolute_output_playlist + '.tmp'
                    if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                        logger.info(f"Found temporary playlist file: {tmp_path}")
                        return True
                    ts_files = [f for f in os.listdir(stream_dir) if f.endswith('.ts')]
                    if ts_files:
                        logger.info(f"Found {len(ts_files)} .ts files")
                        return True
                    return False
                
                while not stream_ready():
                    if time.time() - start_time > timeout:
                        process.terminate()
                        if stream_id in StreamView._processes:
                            del StreamView._processes[stream_id]
                        logger.error("Timeout waiting for index.m3u8 or .ts segments")
                        # Get FFmpeg error output
                        try:
                            stderr_output = process.stderr.read()
                            logger.error(f"FFmpeg error output: {stderr_output}")
                            # Log the last few lines of FFmpeg output for debugging
                            if stderr_output:
                                last_lines = stderr_output.strip().split('\n')[-10:]
                                logger.error("Last 10 lines of FFmpeg output:")
                                for line in last_lines:
                                    logger.error(line)
                        except Exception as e:
                            logger.error(f"Error reading FFmpeg stderr: {str(e)}")
                        # Log directory contents
                        try:
                            dir_contents = os.listdir(stream_dir)
                            logger.error(f"Stream directory contents on timeout: {dir_contents}")
                            # Log directory permissions
                            logger.error(f"Directory permissions: {oct(os.stat(stream_dir).st_mode)[-3:]}")
                            # Log file sizes if any exist
                            for file in dir_contents:
                                file_path = os.path.join(stream_dir, file)
                                if os.path.isfile(file_path):
                                    logger.error(f"File {file} size: {os.path.getsize(file_path)} bytes")
                        except Exception as e:
                            logger.error(f"Error listing stream directory: {str(e)}")
                        # Clean up stream directory
                        try:
                            for file in os.listdir(stream_dir):
                                os.remove(os.path.join(stream_dir, file))
                            os.rmdir(stream_dir)
                        except Exception as e:
                            logger.error(f"Error cleaning up stream directory: {str(e)}")
                        return Response({'error': 'FFmpeg failed to generate HLS playlist or segments within timeout'}, 
                                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
                    time.sleep(0.1)
                    # Check if FFmpeg process is still running
                    if process.poll() is not None:
                        try:
                            stderr_output = process.stderr.read()
                            logger.error(f"FFmpeg process exited prematurely. Error: {stderr_output}")
                        except Exception as e:
                            logger.error(f"Error reading FFmpeg stderr: {str(e)}")
                        return Response({'error': f'FFmpeg process failed: {stderr_output}'}, 
                                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    # Log progress
                    elapsed = time.time() - start_time
                    if elapsed % 1 < 0.1:
                        logger.debug(f"Still waiting for index.m3u8 or .ts segments... Elapsed time: {elapsed:.1f}s")
                
                logger.info(f"HLS playlist generated: {os.path.join(stream_dir, ffmpeg_output_playlist)}")

                # Notify frontend via WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    'streams', {'type': 'stream_update', 'stream_id': stream_id, 'status': 'connected'}
                )
                logger.debug("Sent WebSocket notification")

                stream_url = f'{settings.HLS_URL}{stream_id}/{ffmpeg_output_playlist}'
                logger.info(f"Stream URL generated: {stream_url}")
                return Response({
                    'stream_id': stream_id,
                    'stream_url': stream_url
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error starting FFmpeg process: {str(e)}", exc_info=True)
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
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