from django.http import JsonResponse

def status_view(request):
    return JsonResponse({"status": "Backend is running"}, status=200)