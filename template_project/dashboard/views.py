from django.shortcuts import render

def main_dashboard_view(request):
    return render(request, 'dashboard/main_dashboard.html')
