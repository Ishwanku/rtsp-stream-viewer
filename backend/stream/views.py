from django.http import HttpResponse, HttpResponseForbidden
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import ffmpeg
import os
import logging
from decouple import config

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class StreamView(APIView):
    def post(self, request):
        print("POST /api/stream/ called")
        print("Data:", request.data)

        rtsp_url = request.data.get('rtsp_url')
        logger.info(f"Received RTSP URL: {rtsp_url}")

        if not rtsp_url:
            logger.error("RTSP URL is required")
            return Response({'error': 'RTSP URL is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            logger.info("Probing RTSP URL")
            probe = ffmpeg.probe(rtsp_url)
            logger.info(f"Probe result: {probe}")

            stream_id = os.urandom(16).hex()
            output_dir = f'static/streams/{stream_id}'
            output_path = os.path.join(output_dir, 'index.m3u8')
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Output path: {output_path}")

            logger.info("Starting FFmpeg process")
            stream = (
                ffmpeg
                .input(rtsp_url, rtsp_transport='tcp')
                .output(
                    output_path,
                    format='hls',
                    hls_time=10,
                    hls_list_size=3,
                    hls_segment_filename=os.path.join(output_dir, '%03d.ts'),
                    vcodec='copy',
                    acodec='copy'
                )
                .run_async(pipe_stderr=True)
            )

            # Capture FFmpeg stderr output
            stderr = stream.stderr.read().decode()
            if stderr:
                logger.error(f"FFmpeg stderr: {stderr}")

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


# GET http://localhost:8000/ returns a simple message
def index(request):
    return HttpResponse("RTSP Stream Viewer is running!")
