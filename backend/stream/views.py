import os
import uuid
import ffmpeg
import redis
import boto3
import logging
import subprocess
import time
import platform
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
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
            # Determine FFmpeg path (Windows compatibility)
            ffmpeg_path = './ffmpeg.exe' if os.path.exists('./ffmpeg.exe') else 'ffmpeg'
            try:
                version = subprocess.check_output([ffmpeg_path, '-version'], stderr=subprocess.STDOUT).decode()
                logger.info(f"FFmpeg version: {version.splitlines()[0]}")
            except Exception as e:
                logger.warning(f"Could not verify FFmpeg version: {str(e)}")

            # Validate RTSP URL by probing with extended parameters
            logger.info("Probing RTSP URL")
            probe = ffmpeg.probe(
                rtsp_url,
                rtsp_transport='tcp',
                analyzeduration=10000000,  # 10 seconds
                probesize=10000000,       # 10 MB
                timeout=60000000,
                user_agent='FFmpeg'
            )
            logger.info(f"Probe result: {probe}")
            
            # Generate a unique stream ID
            stream_id = str(uuid.uuid4())
            output_path = f'streams/{stream_id}/index.m3u8'
            os.makedirs(os.path.join(settings.STATIC_ROOT, 'streams', stream_id), exist_ok=True)
            local_output = os.path.join(settings.STATIC_ROOT, output_path)
            logger.info(f"Local output path: {local_output}")
            
            # Start FFmpeg process to convert RTSP to HLS
            logger.info("Starting FFmpeg process")
            stream = (
                ffmpeg
                .input(
                    rtsp_url,
                    re=None,  # Read at native frame rate
                    rtsp_transport='tcp',
                    analyzeduration=10000000,
                    probesize=10000000,
                    timeout=60000000,
                    user_agent='FFmpeg'
                )
                .output(
                    local_output,
                    format='hls',
                    hls_time=2,
                    hls_list_size=3,
                    hls_segment_filename=os.path.join(settings.STATIC_ROOT, f'streams/{stream_id}/%03d.ts'),
                    vcodec='libx264',
                    acodec='aac',
                    preset='ultrafast',
                    vsync='1',  # Synchronize video timestamps
                    loglevel='verbose'
                )
                .run_async(pipe_stderr=True, cmd=ffmpeg_path)
            )

            # Store process in Redis
            redis_client = redis.Redis.from_url(settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0])
            redis_client.set(f'stream:{stream_id}', stream.pid, ex=3600)
            logger.info(f"Stored stream {stream_id} in Redis with PID {stream.pid}")

            # Wait for index.m3u8 to be generated
            timeout = 60  # seconds
            start_time = time.time()
            while not os.path.exists(local_output):
                if time.time() - start_time > timeout:
                    stream.terminate()
                    redis_client.delete(f'stream:{stream_id}')
                    logger.error("Timeout waiting for index.m3u8")
                    return Response({'error': 'FFmpeg failed to generate HLS playlist within timeout'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                time.sleep(1)
            
            # Upload HLS files to S3
            s3 = boto3.client(
                's3',
                aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'),
                region_name=config('AWS_S3_REGION_NAME')
            )
            for file in os.listdir(os.path.join(settings.STATIC_ROOT, f'streams/{stream_id}')):
                local_file = os.path.join(settings.STATIC_ROOT, f'streams/{stream_id}', file)
                s3_key = f'streams/{stream_id}/{file}'
                s3.upload_file(local_file, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
                logger.info(f"Uploaded {local_file} to S3: {s3_key}")

            # Notify frontend via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'streams', {'type': 'stream_update', 'stream_id': stream_id, 'status': 'connected'}
            )

            stream_url = f'{settings.HLS_URL}{stream_id}/index.m3u8'
            logger.info(f"Stream URL generated: {stream_url}")
            return Response({
                'stream_id': stream_id,
                'stream_url': stream_url
            }, status=status.HTTP_200_OK)
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg error: {error_msg}")
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'streams', {'type': 'stream_update', 'stream_id': stream_id, 'status': 'failed', 'error': error_msg}
            )
            return Response({'error': f'FFmpeg failed: {error_msg}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'streams', {'type': 'stream_update', 'stream_id': stream_id, 'status': 'failed', 'error': str(e)}
            )
            return Response({'error': 'Server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestRTSPView(APIView):
    def get(self, request):
        rtsp_url = request.query_params.get('rtsp_url', 'rtsp://admin:admin123@49.248.155.178:555/cam/realmonitor?channel=1&subtype=0')
        try:
            ffmpeg_path = './ffmpeg.exe' if os.path.exists('./ffmpeg.exe') else 'ffmpeg'
            probe = ffmpeg.probe(
                rtsp_url,
                rtsp_transport='tcp',
                analyzeduration=10000000,
                probesize=10000000,
                timeout=60000000,
                user_agent='FFmpeg'
            )
            return Response({'probe': probe}, status=status.HTTP_200_OK)
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            return Response({'error': f'FFmpeg failed: {error_msg}'}, status=status.HTTP_400_BAD_REQUEST)

class StopStreamView(APIView):
    def post(self, request):
        stream_id = request.data.get('stream_id')
        if not stream_id:
            return Response({'error': 'Stream ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            redis_client = redis.Redis.from_url(settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0])
            pid = redis_client.get(f'stream:{stream_id}')
            if pid:
                if platform.system() == 'Windows':
                    subprocess.run(['taskkill', '/F', '/PID', pid.decode()], check=True)
                else:
                    subprocess.run(['kill', '-9', pid.decode()], check=True)
                redis_client.delete(f'stream:{stream_id}')
                logger.info(f"Stopped stream {stream_id} with PID {pid.decode()}")

                # Delete HLS files from S3
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'),
                    region_name=config('AWS_S3_REGION_NAME')
                )
                response = s3_client.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix=f'streams/{stream_id}/')
                objects = [{'Key': obj['Key']} for obj in response.get('Contents', [])]
                if objects:
                    s3_client.delete_objects(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Delete={'Objects': objects})
                logger.info(f"Deleted S3 objects for stream {stream_id}")

                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    'streams', {'type': 'stream_update', 'stream_id': stream_id, 'status': 'stopped'}
                )
                return Response({'message': f'Stream {stream_id} stopped'}, status=status.HTTP_200_OK)
            return Response({'error': 'Stream not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error stopping stream {stream_id}: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)