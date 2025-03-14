# utils/views.py
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from location.models import City, WeatherStation, Concelho

@login_required
def search_items(request):
    """
    Generic search view for dropdown items
    """
    if request.method == 'POST':
        search_term = request.POST.get('search', '').strip()
        item_type = request.POST.get('item_type', 'station')
        current_id = request.POST.get('current_id', None)
        
        items = []
        context = {
            'current_id': current_id,
        }
        
        # Handle different types of searches
        if item_type == 'station':
            # Weather stations search
            stations_query = Q(name__icontains=search_term)
            if search_term:  # Only apply the complex query if there's a search term
                stations_query |= Q(concelho__name__icontains=search_term)
                
            items = WeatherStation.objects.filter(stations_query).order_by('name')[:20]
            
            context.update({
                'items': items,
                'base_url': request.POST.get('base_url', '/climate/temperature/'),
                'query_param': 'station',
                'extra_params': request.POST.get('extra_params', 'range=24h')
            })
            
        elif item_type == 'city':
            # Cities search
            cities_query = Q(name__icontains=search_term)
            if search_term:  # Only apply the complex query if there's a search term
                cities_query |= Q(concelho__name__icontains=search_term)
                
            items = City.objects.filter(cities_query).order_by('name')[:20]
            
            context.update({
                'items': items,
                'base_url': request.POST.get('base_url', '/dashboard/main_dashboard/'),
                'query_param': 'location',
                'hx_target': request.POST.get('hx_target', '#dashboard-content')
            })
            
        # Add more item types as needed
            
        if not search_term:
            # If no search term, return top/selected items
            if item_type == 'station':
                items = WeatherStation.objects.all().order_by('name')[:20]
            elif item_type == 'city':
                items = City.objects.all().order_by('name')[:20]
            
            context['items'] = items
            
        # Render the results template
        html = render_to_string('components/search_results.html', context)
        return HttpResponse(html)
    
    # Return empty response for non-POST requests
    return HttpResponse('')