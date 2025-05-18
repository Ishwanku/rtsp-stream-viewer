from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import ffmpeg
import os

# Simple home view to fix 404 on /
def home(request):
    return HttpResponse("Welcome to the RTSP Stream Viewer API")

class StreamView(APIView):
    def post(self, request):
        print("POST /api/stream/ called")  # Debugging line
        print("Data:", request.data)

        rtsp_url = request.data.get('rtsp_url')
        if not rtsp_url:
            return Response({'error': 'RTSP URL is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Validate the RTSP stream by probing it
            probe_result = ffmpeg.probe(rtsp_url)
            print("FFmpeg probe success:", probe_result)  # Debugging probe result

            # Generate unique stream ID and output path
            stream_id = os.urandom(16).hex()
            output_dir = f'static/streams/{stream_id}'
            output_path = os.path.join(output_dir, 'index.m3u8')

            # Create output directory if not exists
            os.makedirs(output_dir, exist_ok=True)

            # Start FFmpeg to convert RTSP to HLS (blocking for debug)
            (
                ffmpeg
                .input(rtsp_url)
                .output(
                    output_path,
                    format='hls',
                    hls_time=10,
                    hls_list_size=3,
                    hls_segment_filename=os.path.join(output_dir, '%03d.ts')
                )
                .run()  # blocking call, so errors are caught here
            )

            return Response({
                'stream_id': stream_id,
                'stream_url': f'/static/streams/{stream_id}/index.m3u8'
            }, status=status.HTTP_200_OK)

        except ffmpeg.Error as e:
            print("FFmpeg error:", e.stderr.decode() if e.stderr else str(e))
            return Response({'error': 'Invalid RTSP URL or FFmpeg error'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print("Unexpected error:", str(e))
            return Response({'error': 'Server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
