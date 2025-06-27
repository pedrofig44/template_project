# predictions/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q, Max, Avg
from datetime import datetime, timedelta
import calendar
import json
from collections import defaultdict

from location.models import Distrito, Concelho
from .models import WildfirePrediction
from dashboard.utils import generate_pie_chart, generate_line_chart


def _get_fire_season_info(target_date):
    """Get fire season status for a given date"""
    month = target_date.month
    day = target_date.day
    
    # Fire season: May 1 to October 31
    is_fire_season = (month >= 5 and month <= 10)
    
    if not is_fire_season:
        return {
            'is_fire_season': False,
            'status': 'Out of Season',
            'class': 'secondary',
            'message': 'Fire season runs from May 1 to October 31'
        }
    
    # Determine intensity within fire season
    if (month == 7 or month == 8) or (month == 9 and day <= 15):
        intensity = 'Peak Season'
        class_name = 'danger'
    elif month == 6 or (month == 9 and day > 15) or month == 10:
        intensity = 'High Season'
        class_name = 'warning'
    else:  # May
        intensity = 'Early Season'
        class_name = 'info'
    
    return {
        'is_fire_season': True,
        'status': intensity,
        'class': class_name,
        'message': f'Active fire season period - {intensity.lower()}'
    }


def _calculate_risk_level_from_probability(probability):
    """Convert probability to risk level (1-5) following model patterns"""
    if probability >= 0.8:
        return 5
    elif probability >= 0.6:
        return 4
    elif probability >= 0.4:
        return 3
    elif probability >= 0.2:
        return 2
    else:
        return 1


def _get_risk_color(risk_level):
    """Get color for risk level visualization - consistent with existing patterns"""
    color_map = {
        1: '#28a745',  # Green - Reduced Risk
        2: '#ffc107',  # Yellow - Moderate Risk  
        3: '#fd7e14',  # Orange - High Risk
        4: '#dc3545',  # Red - Very High Risk
        5: '#990000'   # Dark Red - Maximum Risk
    }
    return color_map.get(risk_level, '#28a745')


@login_required
def prediction_dashboard(request):
    """
    Detailed prediction dashboard with manual selection and deep analysis
    """
    from datetime import datetime, timedelta
    from django.db.models import Q
    from .services import WildfirePredictionService
    from analytics.models import ConcelhoRiskAnalytics
    from dashboard.utils import generate_line_chart, generate_pie_chart
    
    # Get all concelhos for selection with distrito names
    all_concelhos = []
    concelhos_raw = Concelho.objects.all().order_by('name')
    
    for concelho in concelhos_raw:
        try:
            # Get distrito name by the foreign key relationship
            distrito_name = concelho.distrito.name if concelho.distrito else "Unknown"
            all_concelhos.append({
                'dico_code': concelho.dico_code,
                'name': concelho.name,
                'distrito_name': distrito_name
            })
        except Exception as e:
            # If there's an issue with the relationship, use distrito_id as fallback
            all_concelhos.append({
                'dico_code': concelho.dico_code,
                'name': concelho.name,
                'distrito_name': str(concelho.distrito_id) if hasattr(concelho, 'distrito_id') else "Unknown"
            })
    
    # Handle form inputs
    selected_concelho_code = request.GET.get('concelho')
    selected_date_str = request.GET.get('date')
    comparison_mode = request.GET.get('compare', 'false') == 'true'
    comparison_concelhos = request.GET.getlist('compare_concelho')
    
    # Default date to today if not specified
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    # Fire season info
    fire_season_info = _get_fire_season_info(selected_date)
    
    # Context base
    context = {
        'all_concelhos': all_concelhos,
        'selected_date': selected_date,
        'selected_concelho_code': selected_concelho_code,
        'comparison_mode': comparison_mode,
        'comparison_concelhos': comparison_concelhos,
        'fire_season_info': fire_season_info,
        'today': timezone.now().date(),
        'tomorrow': timezone.now().date() + timedelta(days=1),
    }
    
    # Main prediction analysis
    prediction_result = None
    feature_analysis = None
    historical_data = None
    
    if selected_concelho_code:
        try:
            selected_concelho = Concelho.objects.get(dico_code=selected_concelho_code)
            context['selected_concelho'] = selected_concelho
            
            # Try to get existing prediction first
            existing_prediction = WildfirePrediction.objects.filter(
                concelho=selected_concelho,
                prediction_date=selected_date
            ).first()
            
            if existing_prediction:
                # Use stored prediction
                prediction_result = {
                    'probability': float(existing_prediction.probability),
                    'prediction': existing_prediction.prediction,
                    'confidence': float(existing_prediction.confidence),
                    'risk_level': _calculate_risk_level_from_probability(float(existing_prediction.probability)),
                    'fire_season': existing_prediction.fire_season,
                    'fwi': float(existing_prediction.fwi) if existing_prediction.fwi else 0,
                    'forest_percentage': float(existing_prediction.forest_percentage) if existing_prediction.forest_percentage else 0,
                    'model_name': existing_prediction.ml_model.name,
                    'created_at': existing_prediction.created_at,
                    'data_source': 'stored'
                }
            else:
                # Generate new prediction using service
                try:
                    service = WildfirePredictionService()
                    prediction_result = service.predict(selected_concelho, selected_date)
                    prediction_result['data_source'] = 'generated'
                except Exception as e:
                    context['prediction_error'] = f"Could not generate prediction: {str(e)}"
            
            # Get feature analysis data
            if prediction_result:
                feature_analysis = _analyze_prediction_features(selected_concelho, selected_date, prediction_result)
            
            # Get historical data for trend analysis
            historical_data = _get_historical_predictions(selected_concelho, selected_date)
            
        except Concelho.DoesNotExist:
            context['error'] = f"Concelho with code {selected_concelho_code} not found"
    
    # Comparison analysis
    comparison_results = []
    if comparison_mode and comparison_concelhos:
        for concelho_code in comparison_concelhos:
            try:
                concelho = Concelho.objects.get(dico_code=concelho_code)
                
                # Get distrito name safely
                try:
                    distrito_name = concelho.distrito.name
                except:
                    distrito_name = "Unknown"
                
                # Get or generate prediction
                existing_pred = WildfirePrediction.objects.filter(
                    concelho=concelho,
                    prediction_date=selected_date
                ).first()
                
                if existing_pred:
                    comp_result = {
                        'concelho': concelho,
                        'distrito_name': distrito_name,
                        'probability': float(existing_pred.probability),
                        'prediction': existing_pred.prediction,
                        'risk_level': _calculate_risk_level_from_probability(float(existing_pred.probability)),
                        'confidence': float(existing_pred.confidence),
                    }
                else:
                    # Generate prediction for comparison
                    try:
                        service = WildfirePredictionService()
                        comp_pred = service.predict(concelho, selected_date)
                        comp_result = {
                            'concelho': concelho,
                            'distrito_name': distrito_name,
                            'probability': comp_pred['probability'],
                            'prediction': comp_pred['prediction'],
                            'risk_level': comp_pred.get('risk_level', 1),
                            'confidence': comp_pred['confidence'],
                        }
                    except Exception:
                        comp_result = {
                            'concelho': concelho,
                            'distrito_name': distrito_name,
                            'error': 'Could not generate prediction'
                        }
                
                comparison_results.append(comp_result)
                
            except Concelho.DoesNotExist:
                continue
    
    # Add results to context
    context.update({
        'prediction_result': prediction_result,
        'feature_analysis': feature_analysis,
        'historical_data': historical_data,
        'comparison_results': comparison_results,
    })
    
    return render(request, 'predictions/dashboard.html', context)


def _analyze_prediction_features(concelho, prediction_date, prediction_result):
    """Analyze the features that contributed to the prediction"""
    analysis = {
        'fwi_analysis': {},
        'land_use_analysis': {},
        'temporal_analysis': {},
        'risk_history_analysis': {},
        'charts': {}
    }
    
    # Weather Analysis using StationObservation instead of FWI
    try:
        from climate.models import StationObservation
        from location.models import WeatherStation
        
        # Get weather stations in this concelho
        stations = WeatherStation.objects.filter(concelho=concelho)
        if stations.exists():
            # Get recent observations
            recent_obs = StationObservation.objects.filter(
                station__in=stations,
                timestamp__date__lte=prediction_date,
                timestamp__date__gte=prediction_date - timedelta(days=7)
            ).order_by('-timestamp')[:7]
            
            if recent_obs:
                temps = [obs.temperature for obs in recent_obs if obs.temperature != -99.0]
                humidity = [obs.humidity for obs in recent_obs if obs.humidity != -99.0]
                wind_speeds = [obs.wind_speed_kmh for obs in recent_obs if obs.wind_speed_kmh != -99.0]
                
                if temps:
                    analysis['fwi_analysis'] = {
                        'current_temp': temps[0] if temps else 0,
                        'avg_temp_week': sum(temps) / len(temps) if temps else 0,
                        'current_humidity': humidity[0] if humidity else 0,
                        'avg_humidity_week': sum(humidity) / len(humidity) if humidity else 0,
                        'current_wind': wind_speeds[0] if wind_speeds else 0,
                        'trend': 'increasing' if len(temps) > 1 and temps[0] > temps[-1] else 'stable',
                        'risk_level': 'high' if (temps[0] > 25 and humidity[0] < 40) else 'moderate' if temps[0] > 20 else 'low'
                    }
    except Exception as e:
        # If weather data is not available, skip this analysis
        pass
    
    # Land use analysis
    try:
        land_occupation = concelho.land_occupation.first()
        if land_occupation:
            forest_pct = float(land_occupation.florestas or 0)
            analysis['land_use_analysis'] = {
                'forest_percentage': forest_pct,
                'risk_factor': 'high' if forest_pct > 60 else 'moderate' if forest_pct > 30 else 'low',
                'primary_land_use': 'forest-dominant' if forest_pct > 50 else 'mixed'
            }
    except Exception:
        pass
    
    # Temporal analysis
    month = prediction_date.month
    day_of_year = prediction_date.timetuple().tm_yday
    
    # Fire season analysis
    if 5 <= month <= 10:  # Fire season
        if month in [7, 8]:
            season_risk = 'peak'
        elif month in [6, 9]:
            season_risk = 'high'
        else:
            season_risk = 'moderate'
    else:
        season_risk = 'low'
    
    analysis['temporal_analysis'] = {
        'season_risk': season_risk,
        'month': month,
        'day_of_year': day_of_year,
        'fire_season': 5 <= month <= 10
    }
    
    # Risk history analysis
    try:
        from analytics.models import ConcelhoRiskAnalytics
        recent_risk = ConcelhoRiskAnalytics.objects.filter(
            concelho=concelho,
            analysis_date__lte=prediction_date
        ).order_by('-analysis_date').first()
        
        if recent_risk:
            analysis['risk_history_analysis'] = {
                'historical_mean': float(recent_risk.risk_mean),
                'risk_trend': 'above_average' if float(recent_risk.risk_mean) > 2.5 else 'average'
            }
    except Exception:
        pass
    
    return analysis


def _get_historical_predictions(concelho, current_date):
    """Get historical predictions for trend analysis"""
    # Get predictions from last 30 days
    start_date = current_date - timedelta(days=30)
    
    historical_predictions = WildfirePrediction.objects.filter(
        concelho=concelho,
        prediction_date__gte=start_date,
        prediction_date__lte=current_date
    ).order_by('prediction_date')
    
    if not historical_predictions:
        return None
    
    # Prepare data for chart
    dates = []
    probabilities = []
    
    for pred in historical_predictions:
        dates.append(pred.prediction_date.strftime('%Y-%m-%d'))
        probabilities.append(float(pred.probability))
    
    # Generate trend chart
    try:
        from dashboard.utils import generate_line_chart
        import polars as pl
        
        # Create DataFrame for chart
        chart_df = pl.DataFrame({
            'timestamp': dates,
            'probability': probabilities
        })
        
        trend_chart = generate_line_chart(
            df=chart_df,
            title=f"30-Day Prediction Trend - {concelho.name}",
            x_axis="Date",
            y_axis="Risk Probability"
        )
        
        return {
            'predictions': historical_predictions,
            'trend_chart': trend_chart,
            'average_probability': sum(probabilities) / len(probabilities),
            'trend_direction': 'increasing' if probabilities[-1] > probabilities[0] else 'decreasing'
        }
    except Exception:
        return {
            'predictions': historical_predictions,
            'trend_chart': None
        }


@login_required
def historical_analysis(request):
    """
    Comprehensive historical analysis of wildfire predictions
    """
    from django.db.models import Count, Avg, Min, Max, Q
    from datetime import datetime, timedelta
    from collections import defaultdict
    import calendar
    from dashboard.utils import generate_line_chart, generate_pie_chart
    
    # Date range selection
    end_date = timezone.now().date()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    time_range = request.GET.get('time_range', '6_months')  # Default to 6 months
    
    # Handle time range selection
    if time_range == '1_month':
        start_date = end_date - timedelta(days=30)
    elif time_range == '3_months':
        start_date = end_date - timedelta(days=90)
    elif time_range == '6_months':
        start_date = end_date - timedelta(days=180)
    elif time_range == '1_year':
        start_date = end_date - timedelta(days=365)
    elif time_range == 'all_time':
        # Get earliest prediction date
        earliest = WildfirePrediction.objects.aggregate(earliest=Min('prediction_date'))['earliest']
        start_date = earliest if earliest else end_date - timedelta(days=365)
    elif time_range == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = end_date - timedelta(days=180)
    else:
        start_date = end_date - timedelta(days=180)
    
    # Get base queryset for the selected period
    base_predictions = WildfirePrediction.objects.filter(
        prediction_date__gte=start_date,
        prediction_date__lte=end_date
    ).select_related('concelho', 'ml_model')
    
    # Overview Statistics
    total_predictions = base_predictions.count()
    unique_concelhos = base_predictions.values('concelho').distinct().count()
    fire_season_predictions = base_predictions.filter(fire_season=True).count()
    high_risk_predictions = base_predictions.filter(probability__gte=0.6).count()
    
    # Model Performance Analysis
    model_stats = base_predictions.values('ml_model__name').annotate(
        prediction_count=Count('id'),
        avg_probability=Avg('probability'),
        avg_confidence=Avg('confidence'),
        high_risk_count=Count('id', filter=Q(probability__gte=0.6)),
        fire_predictions=Count('id', filter=Q(prediction=True))
    ).order_by('-prediction_count')
    
    # Temporal Analysis - Daily trends
    daily_trends = _analyze_daily_trends(base_predictions, start_date, end_date)
    
    # Seasonal Analysis - Monthly patterns
    seasonal_analysis = _analyze_seasonal_patterns(base_predictions)
    
    # Geographic Analysis - Top performing concelhos
    geographic_analysis = _analyze_geographic_patterns(base_predictions)
    
    # Risk Level Distribution Over Time
    risk_distribution_over_time = _analyze_risk_distribution_over_time(base_predictions)
    
    # Fire Season Analysis
    fire_season_analysis = _analyze_fire_season_performance(base_predictions)
    
    # Data Quality Analysis
    data_quality_analysis = _analyze_data_quality(base_predictions)
    
    # Generate Charts
    charts = _generate_historical_charts(
        daily_trends, seasonal_analysis, risk_distribution_over_time, 
        fire_season_analysis, start_date, end_date
    )
    
    # Insights and Recommendations
    insights = _generate_insights(
        base_predictions, seasonal_analysis, geographic_analysis, 
        model_stats, fire_season_analysis
    )
    
    context = {
        # Date controls
        'start_date': start_date,
        'end_date': end_date,
        'time_range': time_range,
        
        # Overview stats
        'total_predictions': total_predictions,
        'unique_concelhos': unique_concelhos,
        'fire_season_predictions': fire_season_predictions,
        'high_risk_predictions': high_risk_predictions,
        'high_risk_percentage': (high_risk_predictions / total_predictions * 100) if total_predictions > 0 else 0,
        
        # Analysis results
        'model_stats': model_stats,
        'daily_trends': daily_trends,
        'seasonal_analysis': seasonal_analysis,
        'geographic_analysis': geographic_analysis,
        'risk_distribution_over_time': risk_distribution_over_time,
        'fire_season_analysis': fire_season_analysis,
        'data_quality_analysis': data_quality_analysis,
        
        # Charts
        'charts': charts,
        
        # Insights
        'insights': insights,
    }
    
    return render(request, 'predictions/historical_analysis.html', context)


def _analyze_daily_trends(predictions, start_date, end_date):
    """Analyze daily prediction trends"""
    daily_data = predictions.values('prediction_date').annotate(
        prediction_count=Count('id'),
        avg_probability=Avg('probability'),
        high_risk_count=Count('id', filter=Q(probability__gte=0.6)),
        fire_predictions=Count('id', filter=Q(prediction=True))
    ).order_by('prediction_date')
    
    return {
        'daily_data': list(daily_data),
        'total_days': (end_date - start_date).days,
        'avg_predictions_per_day': sum(d['prediction_count'] for d in daily_data) / len(daily_data) if daily_data else 0
    }


def _analyze_seasonal_patterns(predictions):
    """Analyze seasonal and monthly patterns"""
    monthly_data = defaultdict(lambda: {'count': 0, 'avg_probability': 0, 'high_risk': 0})
    
    # Group by month
    for pred in predictions:
        month = pred.prediction_date.month
        monthly_data[month]['count'] += 1
        monthly_data[month]['total_probability'] = monthly_data[month].get('total_probability', 0) + float(pred.probability)
        if pred.probability >= 0.6:
            monthly_data[month]['high_risk'] += 1
    
    # Calculate averages
    for month, data in monthly_data.items():
        if data['count'] > 0:
            data['avg_probability'] = data['total_probability'] / data['count']
            data['high_risk_percentage'] = (data['high_risk'] / data['count']) * 100
        data['month_name'] = calendar.month_name[month]
    
    # Fire season vs non-fire season
    fire_season_months = [5, 6, 7, 8, 9, 10]
    fire_season_data = predictions.filter(prediction_date__month__in=fire_season_months)
    non_fire_season_data = predictions.exclude(prediction_date__month__in=fire_season_months)
    
    fire_season_stats = {
        'count': fire_season_data.count(),
        'avg_probability': fire_season_data.aggregate(avg=Avg('probability'))['avg'] or 0,
        'high_risk_count': fire_season_data.filter(probability__gte=0.6).count()
    }
    
    non_fire_season_stats = {
        'count': non_fire_season_data.count(),
        'avg_probability': non_fire_season_data.aggregate(avg=Avg('probability'))['avg'] or 0,
        'high_risk_count': non_fire_season_data.filter(probability__gte=0.6).count()
    }
    
    return {
        'monthly_data': dict(monthly_data),
        'fire_season_stats': fire_season_stats,
        'non_fire_season_stats': non_fire_season_stats,
        'peak_months': [7, 8, 9],  # Typical peak fire season
        'early_season_months': [5, 6],
        'late_season_months': [10]
    }


def _analyze_geographic_patterns(predictions):
    """Analyze geographic patterns and concelho performance"""
    concelho_stats = predictions.values(
        'concelho__name', 'concelho__dico_code', 'concelho__distrito_id'
    ).annotate(
        prediction_count=Count('id'),
        avg_probability=Avg('probability'),
        high_risk_count=Count('id', filter=Q(probability__gte=0.6)),
        max_probability=Max('probability'),
        fire_predictions=Count('id', filter=Q(prediction=True))
    ).order_by('-avg_probability')
    
    # Top high-risk concelhos
    top_high_risk = list(concelho_stats.filter(high_risk_count__gt=0)[:10])
    
    # Most active concelhos (most predictions)
    most_active = list(concelho_stats.order_by('-prediction_count')[:10])
    
    # Distrito-level analysis
    distrito_stats = defaultdict(lambda: {
        'count': 0, 'total_probability': 0, 'high_risk': 0, 'concelhos': set()
    })
    
    for pred in predictions:
        distrito_id = pred.concelho.distrito_id
        distrito_stats[distrito_id]['count'] += 1
        distrito_stats[distrito_id]['total_probability'] += float(pred.probability)
        distrito_stats[distrito_id]['concelhos'].add(pred.concelho.name)
        if pred.probability >= 0.6:
            distrito_stats[distrito_id]['high_risk'] += 1
    
    # Calculate distrito averages
    for distrito_id, stats in distrito_stats.items():
        if stats['count'] > 0:
            stats['avg_probability'] = stats['total_probability'] / stats['count']
            stats['high_risk_percentage'] = (stats['high_risk'] / stats['count']) * 100
            stats['concelho_count'] = len(stats['concelhos'])
    
    return {
        'top_high_risk_concelhos': top_high_risk,
        'most_active_concelhos': most_active,
        'distrito_stats': dict(distrito_stats),
        'total_concelhos_analyzed': len(concelho_stats)
    }


def _analyze_risk_distribution_over_time(predictions):
    """Analyze how risk levels have changed over time"""
    risk_levels_over_time = defaultdict(lambda: defaultdict(int))
    
    for pred in predictions:
        week = pred.prediction_date.isocalendar()[1]  # Week of year
        year = pred.prediction_date.year
        time_key = f"{year}-W{week:02d}"
        
        # Categorize by risk level
        if pred.probability >= 0.8:
            risk_levels_over_time[time_key]['extreme'] += 1
        elif pred.probability >= 0.6:
            risk_levels_over_time[time_key]['high'] += 1
        elif pred.probability >= 0.4:
            risk_levels_over_time[time_key]['moderate'] += 1
        elif pred.probability >= 0.2:
            risk_levels_over_time[time_key]['low'] += 1
        else:
            risk_levels_over_time[time_key]['very_low'] += 1
        
        risk_levels_over_time[time_key]['total'] += 1
    
    return dict(risk_levels_over_time)


def _analyze_fire_season_performance(predictions):
    """Analyze model performance during fire season vs non-fire season"""
    fire_season_months = [5, 6, 7, 8, 9, 10]
    
    fire_season_preds = predictions.filter(
        prediction_date__month__in=fire_season_months
    )
    
    non_fire_season_preds = predictions.exclude(
        prediction_date__month__in=fire_season_months
    )
    
    fire_season_analysis = {
        'total_predictions': fire_season_preds.count(),
        'avg_probability': fire_season_preds.aggregate(avg=Avg('probability'))['avg'] or 0,
        'avg_confidence': fire_season_preds.aggregate(avg=Avg('confidence'))['avg'] or 0,
        'high_risk_count': fire_season_preds.filter(probability__gte=0.6).count(),
        'fire_predictions': fire_season_preds.filter(prediction=True).count(),
    }
    
    non_fire_season_analysis = {
        'total_predictions': non_fire_season_preds.count(),
        'avg_probability': non_fire_season_preds.aggregate(avg=Avg('probability'))['avg'] or 0,
        'avg_confidence': non_fire_season_preds.aggregate(avg=Avg('confidence'))['avg'] or 0,
        'high_risk_count': non_fire_season_preds.filter(probability__gte=0.6).count(),
        'fire_predictions': non_fire_season_preds.filter(prediction=True).count(),
    }
    
    return {
        'fire_season': fire_season_analysis,
        'non_fire_season': non_fire_season_analysis,
        'seasonal_difference': {
            'probability_diff': fire_season_analysis['avg_probability'] - non_fire_season_analysis['avg_probability'],
            'confidence_diff': fire_season_analysis['avg_confidence'] - non_fire_season_analysis['avg_confidence']
        }
    }


def _analyze_data_quality(predictions):
    """Analyze data quality metrics"""
    total_predictions = predictions.count()
    
    quality_stats = {
        'has_real_fwi': predictions.filter(has_real_fwi=True).count(),
        'high_quality': predictions.filter(data_quality_score__gte=0.8).count(),
        'medium_quality': predictions.filter(
            data_quality_score__gte=0.6, data_quality_score__lt=0.8
        ).count(),
        'low_quality': predictions.filter(data_quality_score__lt=0.6).count(),
        'avg_quality_score': predictions.aggregate(avg=Avg('data_quality_score'))['avg'] or 0,
        'avg_processing_time': predictions.exclude(
            processing_time_ms__isnull=True
        ).aggregate(avg=Avg('processing_time_ms'))['avg'] or 0
    }
    
    # Calculate percentages
    if total_predictions > 0:
        quality_stats['real_fwi_percentage'] = (quality_stats['has_real_fwi'] / total_predictions) * 100
        quality_stats['high_quality_percentage'] = (quality_stats['high_quality'] / total_predictions) * 100
    
    return quality_stats


def _generate_historical_charts(daily_trends, seasonal_analysis, risk_distribution, 
                               fire_season_analysis, start_date, end_date):
    """Generate all charts for historical analysis"""
    charts = {}
    
    try:
        import polars as pl
        
        # Daily trends chart
        if daily_trends['daily_data']:
            daily_df = pl.DataFrame(daily_trends['daily_data'])
            if not daily_df.is_empty():
                chart_df = daily_df.select([
                    pl.col('prediction_date').cast(pl.Utf8).alias('timestamp'),
                    'avg_probability'
                ])
                
                charts['daily_trends'] = generate_line_chart(
                    df=chart_df,
                    title=f"Daily Average Risk Probability ({start_date} to {end_date})",
                    x_axis="Date",
                    y_axis="Average Probability"
                )
        
        # Monthly patterns chart
        monthly_data = seasonal_analysis['monthly_data']
        if monthly_data:
            months = []
            probabilities = []
            for month in range(1, 13):
                if month in monthly_data:
                    months.append(calendar.month_abbr[month])
                    probabilities.append(monthly_data[month]['avg_probability'])
                else:
                    months.append(calendar.month_abbr[month])
                    probabilities.append(0)
            
            monthly_df = pl.DataFrame({
                'timestamp': months,
                'avg_probability': probabilities
            })
            
            charts['monthly_patterns'] = generate_line_chart(
                df=monthly_df,
                title="Monthly Risk Patterns",
                x_axis="Month",
                y_axis="Average Probability"
            )
        
        # Fire season comparison chart
        fire_stats = fire_season_analysis
        if fire_stats['fire_season']['total_predictions'] > 0:
            comparison_data = {
                'Fire Season': fire_stats['fire_season']['avg_probability'],
                'Non-Fire Season': fire_stats['non_fire_season']['avg_probability']
            }
            
            charts['fire_season_comparison'] = generate_pie_chart(
                data=comparison_data,
                title="Fire Season vs Non-Fire Season Risk",
                height=300
            )
    
    except Exception as e:
        print(f"Error generating charts: {e}")
    
    return charts


def _generate_insights(predictions, seasonal_analysis, geographic_analysis, 
                      model_stats, fire_season_analysis):
    """Generate key insights and recommendations"""
    insights = []
    
    # Seasonal insights
    peak_month_data = seasonal_analysis['monthly_data']
    if peak_month_data:
        peak_month = max(peak_month_data.items(), key=lambda x: x[1]['avg_probability'])
        insights.append({
            'type': 'seasonal',
            'title': 'Peak Risk Month',
            'description': f'{peak_month[1]["month_name"]} shows the highest average risk probability ({peak_month[1]["avg_probability"]:.2f})',
            'icon': '📅',
            'severity': 'warning' if peak_month[1]['avg_probability'] > 0.5 else 'info'
        })
    
    # Geographic insights
    if geographic_analysis['top_high_risk_concelhos']:
        top_risk_concelho = geographic_analysis['top_high_risk_concelhos'][0]
        insights.append({
            'type': 'geographic',
            'title': 'Highest Risk Area',
            'description': f'{top_risk_concelho["concelho__name"]} has the highest average risk probability ({top_risk_concelho["avg_probability"]:.2f})',
            'icon': '🗺️',
            'severity': 'danger' if top_risk_concelho['avg_probability'] > 0.6 else 'warning'
        })
    
    # Model performance insights
    if model_stats:
        primary_model = model_stats[0]
        insights.append({
            'type': 'model',
            'title': 'Model Performance',
            'description': f'Primary model "{primary_model["ml_model__name"]}" shows {primary_model["avg_confidence"]:.2f} average confidence',
            'icon': '🤖',
            'severity': 'success' if primary_model['avg_confidence'] > 0.7 else 'warning'
        })
    
    # Fire season insights
    fire_season_stats = fire_season_analysis['fire_season']
    non_fire_season_stats = fire_season_analysis['non_fire_season']
    
    if fire_season_stats['total_predictions'] > 0 and non_fire_season_stats['total_predictions'] > 0:
        prob_diff = fire_season_stats['avg_probability'] - non_fire_season_stats['avg_probability']
        insights.append({
            'type': 'seasonal',
            'title': 'Fire Season Impact',
            'description': f'Fire season predictions are {prob_diff:.2f} points higher on average than non-fire season',
            'icon': '🔥',
            'severity': 'warning' if prob_diff > 0.3 else 'info'
        })
    
    return insights


@login_required
def prediction_risk_map(request):
    """
    View for displaying the live wildfire prediction risk map of Portugal
    """
    # Get current date and handle date selection
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    
    date_selection = request.GET.get('date', 'today')
    if date_selection == 'tomorrow':
        selected_date = tomorrow
        prediction_type = 'tomorrow'
    else:
        selected_date = today
        prediction_type = 'today'
        date_selection = 'today'  # normalize
    
    # Get fire season information
    fire_season_info = _get_fire_season_info(selected_date)
    
    # Get ALL concelhos first
    all_concelhos = Concelho.objects.all()
    
    # Fetch latest predictions for the selected date/type
    predictions = WildfirePrediction.get_latest_predictions(prediction_type)
    
    # Create a dictionary of predictions by concelho code for easy lookup
    predictions_dict = {}
    for pred in predictions:
        predictions_dict[pred.concelho.dico_code] = pred
    
    # Process all concelhos, with or without predictions
    predictions_data = []
    for concelho in all_concelhos:
        # Check if we have a prediction for this concelho
        if concelho.dico_code in predictions_dict:
            pred = predictions_dict[concelho.dico_code]
            # Calculate risk level if not stored
            risk_level = _calculate_risk_level_from_probability(float(pred.probability))
            
            predictions_data.append({
                'concelho_code': concelho.dico_code,
                'concelho_name': concelho.name,
                'distrito_code': str(concelho.distrito.district_code),
                'distrito_name': concelho.distrito.name,
                'probability': float(pred.probability),
                'risk_level': risk_level,
                'risk_color': _get_risk_color(risk_level) if concelho.in_wildfire_training else '#808080',
                'prediction': pred.prediction,
                'confidence': float(pred.confidence),
                'fire_season': pred.fire_season,
                'fwi': float(pred.fwi) if pred.fwi else 0,
                'forest_percentage': float(pred.forest_percentage) if pred.forest_percentage else 0,
                'in_training_data': concelho.in_wildfire_training
            })
        else:
            # No prediction available - use default values
            predictions_data.append({
                'concelho_code': concelho.dico_code,
                'concelho_name': concelho.name,
                'distrito_code': str(concelho.distrito.district_code),
                'distrito_name': concelho.distrito.name,
                'probability': 0.0,
                'risk_level': 0,  # Use 0 for no data
                'risk_color': '#808080',  # Grey for no data or not in training
                'prediction': False,
                'confidence': 0.0,
                'fire_season': fire_season_info['is_fire_season'],
                'in_training_data': concelho.in_wildfire_training
            })
    
    # Calculate risk distribution statistics (only for concelhos with predictions in training data)
    risk_counts = defaultdict(int)
    total_concelhos = len(all_concelhos)
    concelhos_with_predictions = 0
    
    for pred in predictions_data:
        if pred['in_training_data'] and pred['risk_level'] > 0:
            risk_counts[pred['risk_level']] += 1
            concelhos_with_predictions += 1
    
    # Calculate percentages for risk distribution
    risk_distribution = {}
    for level in range(1, 6):
        count = risk_counts[level]
        # Calculate percentage based on concelhos with predictions
        percentage = (count / concelhos_with_predictions * 100) if concelhos_with_predictions > 0 else 0
        risk_distribution[level] = {
            'count': count,
            'percentage': round(percentage, 1)
        }
    
    # High risk areas (level 4 and 5) - only from training data
    high_risk_predictions = [p for p in predictions_data if p['risk_level'] >= 4 and p['in_training_data']]
    high_risk_count = len(high_risk_predictions)
    
    # Medium risk areas (level 3) - only from training data
    medium_risk_count = risk_counts[3]
    
    # Low risk areas (level 1 and 2) - only from training data
    low_risk_count = risk_counts[1] + risk_counts[2]
    
    # Prepare distrito-level data for map navigation
    distritos_data = {}
    distritos = Distrito.objects.all()
    
    for distrito in distritos:
        district_predictions = [p for p in predictions_data if p['distrito_code'] == str(distrito.district_code)]
        # Only consider training data concelhos for statistics
        training_predictions = [p for p in district_predictions if p['in_training_data'] and p['risk_level'] > 0]
        
        # Calculate average risk level for distrito
        if training_predictions:
            avg_risk = sum(p['risk_level'] for p in training_predictions) / len(training_predictions)
            max_risk = max(p['risk_level'] for p in training_predictions)
        else:
            avg_risk = 1
            max_risk = 1
        
        distritos_data[str(distrito.district_code)] = {
            'name': distrito.name,
            'avg_risk_level': round(avg_risk, 1),
            'max_risk_level': max_risk,
            'concelhos_count': len(district_predictions),
            'training_concelhos_count': len(training_predictions),
            'high_risk_concelhos': len([p for p in training_predictions if p['risk_level'] >= 4])
        }
    
    # Create map data JSON for JavaScript
    map_data = {}
    for pred in predictions_data:
        map_data[pred['concelho_code']] = {
            'name': pred['concelho_name'],
            'distrito': pred['distrito_name'],
            'risk_level': pred['risk_level'],
            'risk_color': pred['risk_color'],
            'probability': pred['probability'],
            'prediction': pred['prediction'],
            'confidence': pred['confidence'],
            'fire_season': pred['fire_season'],
            'in_training_data': pred['in_training_data']
        }
    
    # Generate risk distribution pie chart (only include levels with data from training concelhos)
    chart_data = {}
    for level in range(1, 6):
        count = risk_distribution[level]['count']
        if count > 0:  # Only include levels that have concelhos
            level_names = {
                1: 'Level 1 (Very Low)',
                2: 'Level 2 (Low)', 
                3: 'Level 3 (Moderate)',
                4: 'Level 4 (High)',
                5: 'Level 5 (Extreme)'
            }
            chart_data[level_names[level]] = count
    
    # Generate chart if we have data
    if chart_data:
        risk_distribution_chart = generate_pie_chart(
            data=chart_data,
            title=f"Risk Distribution - {selected_date.strftime('%B %d, %Y')} (Training Data Only)",
            height=300
        )
    else:
        # Fallback empty chart
        risk_distribution_chart = generate_pie_chart(
            data={'No Data': 1},
            title="No Prediction Data Available",
            height=300
        )
    
    # Count of concelhos in/out of training data
    in_training_count = len([p for p in predictions_data if p['in_training_data']])
    out_of_training_count = total_concelhos - in_training_count
    
    # Prepare context for template
    context = {
        # Date and selection
        'today': today,
        'tomorrow': tomorrow,
        'selected_date': selected_date,
        'date_selection': date_selection,
        
        # Fire season info
        'fire_season_status': fire_season_info['status'],
        'fire_season_class': fire_season_info['class'],
        'fire_season_message': fire_season_info['message'],
        'current_date': timezone.now(),
        
        # Risk statistics (only for training data)
        'risk_distribution': risk_distribution,
        'risk_distribution_chart': risk_distribution_chart,
        'high_risk_count': high_risk_count,
        'medium_risk_count': medium_risk_count,
        'low_risk_count': low_risk_count,
        'total_concelhos': total_concelhos,
        'concelhos_with_predictions': concelhos_with_predictions,
        
        # High risk areas for alerts (only from training data)
        'high_risk_predictions': high_risk_predictions[:10],  # Top 10 for display
        
        # Map and navigation data
        'map_data_json': json.dumps(map_data),
        'distritos_data': distritos_data,
        
        # Prediction metadata
        'prediction_type': prediction_type,
        'predictions_count': len(predictions_data),
        
        # Training data statistics
        'in_training_count': in_training_count,
        'out_of_training_count': out_of_training_count,
    }
    
    return render(request, 'predictions/risk_map.html', context)