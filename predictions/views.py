# predictions/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
from location.models import Distrito, Concelho
from climate.models import FireRisk
from .models import WildfirePrediction

@login_required
def prediction_risk_map(request):
    
    return render(request, 'predictions/risk_map.html')