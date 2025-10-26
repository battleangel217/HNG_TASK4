import os
import random
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import FileResponse, HttpResponse
from .models import Country
from .serializers import CountrySerializer
import json

class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    lookup_field = 'name'
    
    def get_queryset(self):
        queryset = Country.objects.all()
        
        # Filter by region
        region = self.request.query_params.get('region', None)
        if region:
            queryset = queryset.filter(region__iexact=region)
            
        # Filter by currency
        currency = self.request.query_params.get('currency', None)
        if currency:
            queryset = queryset.filter(currency_code__iexact=currency)
            
        # Sort by GDP
        sort = self.request.query_params.get('sort', None)
        if sort == 'gdp_desc':
            queryset = queryset.order_by('-estimated_gdp')
            
        return queryset

    def get_object(self):
        return get_object_or_404(Country, name__iexact=self.kwargs['name'])

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        try:
            # Fetch countries data
            countries_response = requests.get(
                'https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies',
                timeout=10
            )
            countries_data = countries_response.json()

            # Fetch exchange rates
            exchange_response = requests.get('https://open.er-api.com/v6/latest/USD', timeout=10)
            exchange_data = exchange_response.json()
            rates = exchange_data.get('rates', {})

            # Process each country
            for country_data in countries_data:
                # Extract currency code if available
                currencies = country_data.get('currencies', [])
                currency_code = currencies[0].get('code') if currencies else None

                # Calculate exchange rate and GDP
                exchange_rate = None
                estimated_gdp = None
                if currency_code and currency_code in rates:
                    exchange_rate = rates[currency_code]
                    population = country_data.get('population', 0)
                    if population and exchange_rate:
                        multiplier = random.uniform(1000, 2000)
                        estimated_gdp = (population * multiplier) / exchange_rate

                # Update or create country record
                country, _ = Country.objects.update_or_create(
                    name=country_data['name'],
                    defaults={
                        'capital': country_data.get('capital'),
                        'region': country_data.get('region'),
                        'population': country_data.get('population', 0),
                        'currency_code': currency_code,
                        'exchange_rate': exchange_rate,
                        'estimated_gdp': estimated_gdp,
                        'flag_url': country_data.get('flag'),
                    }
                )

            # Generate summary image
            self.generate_summary_image()

            return Response({
                'message': 'Countries data refreshed successfully',
                'total_countries': Country.objects.count()
            })

        except requests.exceptions.RequestException as e:
            return Response({
                'error': 'External data source unavailable',
                'details': str(e)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({
                'error': 'Internal server error',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def status(self, request):
        total_countries = Country.objects.count()
        last_refreshed = Country.objects.order_by('-last_refreshed_at').first()
        last_refreshed_at = last_refreshed.last_refreshed_at if last_refreshed else None

        return Response({
            'total_countries': total_countries,
            'last_refreshed_at': last_refreshed_at
        })

    @action(detail=False, methods=['get'])
    def image(self, request):
        image_path = os.path.join(settings.BASE_DIR, 'cache', 'summary.png')
        if not os.path.exists(image_path):
            return Response({
                'error': 'Summary image not found'
            }, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(open(image_path, 'rb'), content_type='image/png')

    def generate_summary_image(self):
        # Ensure cache directory exists
        cache_dir = os.path.join(settings.BASE_DIR, 'cache')
        os.makedirs(cache_dir, exist_ok=True)

        # Create image
        width = 800
        height = 600
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)

        try:
            # Try to load a system font
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            # Fallback to default font
            font = ImageFont.load_default()

        # Draw content
        y_position = 50
        
        # Total countries
        total_countries = Country.objects.count()
        draw.text((50, y_position), f'Total Countries: {total_countries}', fill='black', font=font)
        y_position += 50

        # Top 5 countries by GDP
        draw.text((50, y_position), 'Top 5 Countries by GDP:', fill='black', font=font)
        y_position += 40

        top_countries = Country.objects.filter(
            estimated_gdp__isnull=False
        ).order_by('-estimated_gdp')[:5]

        for country in top_countries:
            gdp_text = f'{country.name}: ${country.estimated_gdp:,.2f}'
            draw.text((70, y_position), gdp_text, fill='black', font=font)
            y_position += 30

        # Last refresh timestamp
        y_position += 20
        last_refresh = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        draw.text((50, y_position), f'Last Refreshed: {last_refresh}', fill='black', font=font)

        # Save image
        image.save(os.path.join(cache_dir, 'summary.png'))
