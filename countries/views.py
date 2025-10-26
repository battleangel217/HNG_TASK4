import os
import random
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
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

    def list(self, request, *args, **kwargs):
        """Return a plain list (not paginated) of countries to match required API contract."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, name=None):
        country = Country.objects.filter(name__iexact=name).first()
        if not country:
            return Response({"error": "Country not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(country)
        return Response(serializer.data)

    def destroy(self, request, name=None):
        country = Country.objects.filter(name__iexact=name).first()
        if not country:
            return Response({"error": "Country not found"}, status=status.HTTP_404_NOT_FOUND)
        country.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _validate_required_fields(self, data, partial=False):
        errors = {}
        # For create (partial=False) require these fields
        if not partial:
            if not data.get('name'):
                errors['name'] = 'is required'
            # population may be provided as str; check presence
            if 'population' not in data or data.get('population') in [None, '']:
                errors['population'] = 'is required'
            if not data.get('currency_code'):
                errors['currency_code'] = 'is required'
        return errors

    def create(self, request, *args, **kwargs):
        errors = self._validate_required_fields(request.data, partial=False)
        if errors:
            return Response({"error": "Validation failed", "details": errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": "Validation failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, name=None, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = Country.objects.filter(name__iexact=name).first()
        if not instance:
            return Response({"error": "Country not found"}, status=status.HTTP_404_NOT_FOUND)
        errors = self._validate_required_fields(request.data, partial=partial)
        if errors:
            return Response({"error": "Validation failed", "details": errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response({"error": "Validation failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        # Fetch external data first. If either external API fails, do not modify DB.
        try:
            countries_resp = requests.get(
                'https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies',
                timeout=15,
            )
            countries_resp.raise_for_status()
            countries_data = countries_resp.json()
        except requests.exceptions.RequestException:
            return Response({"error": "External data source unavailable", "details": "Could not fetch data from countries API"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            exchange_resp = requests.get('https://open.er-api.com/v6/latest/USD', timeout=15)
            exchange_resp.raise_for_status()
            exchange_json = exchange_resp.json()
            rates = exchange_json.get('rates')
            if rates is None:
                raise ValueError('rates missing')
        except (requests.exceptions.RequestException, ValueError):
            return Response({"error": "External data source unavailable", "details": "Could not fetch data from exchange rates API"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Both external APIs are OK — proceed to update DB inside a transaction
        try:
            with transaction.atomic():
                for country_data in countries_data:
                    name = country_data.get('name')
                    if not name:
                        continue

                    currencies = country_data.get('currencies') or []
                    currency_code = None
                    if len(currencies) > 0 and currencies[0]:
                        currency_code = currencies[0].get('code') if isinstance(currencies[0], dict) else None

                    exchange_rate = None
                    estimated_gdp = None

                    population = country_data.get('population') or 0

                    if not currencies:
                        # Spec: if currencies array is empty, set currency_code null, exchange_rate null, estimated_gdp 0
                        currency_code = None
                        exchange_rate = None
                        estimated_gdp = 0
                    else:
                        if currency_code and currency_code in rates:
                            try:
                                exchange_rate = float(rates[currency_code])
                            except Exception:
                                exchange_rate = None

                            if population and exchange_rate:
                                multiplier = random.uniform(1000, 2000)
                                estimated_gdp = (population * multiplier) / exchange_rate
                        else:
                            # currency present but not found in rates
                            exchange_rate = None
                            estimated_gdp = None

                    # Match existing by name case-insensitive
                    existing = Country.objects.filter(name__iexact=name).first()
                    if existing:
                        existing.capital = country_data.get('capital')
                        existing.region = country_data.get('region')
                        existing.population = population
                        existing.currency_code = currency_code
                        existing.exchange_rate = exchange_rate
                        existing.estimated_gdp = estimated_gdp
                        existing.flag_url = country_data.get('flag')
                        # auto_now will update last_refreshed_at on save
                        existing.save()
                    else:
                        Country.objects.create(
                            name=name,
                            capital=country_data.get('capital'),
                            region=country_data.get('region'),
                            population=population,
                            currency_code=currency_code,
                            exchange_rate=exchange_rate,
                            estimated_gdp=estimated_gdp,
                            flag_url=country_data.get('flag')
                        )

            # Generate summary image
            self.generate_summary_image()

            last_ref = Country.objects.order_by('-last_refreshed_at').first()
            last_refreshed_at = last_ref.last_refreshed_at if last_ref else None

            return Response({
                'message': 'Countries data refreshed successfully',
                'total_countries': Country.objects.count(),
                'last_refreshed_at': last_refreshed_at,
            })
        except Exception as e:
            return Response({'error': 'Internal server error', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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


@api_view(['GET'])
def status_view(request):
    """Top-level status endpoint expected at /status"""
    total_countries = Country.objects.count()
    last_refreshed = Country.objects.order_by('-last_refreshed_at').first()
    last_refreshed_at = last_refreshed.last_refreshed_at if last_refreshed else None
    return Response({
        'total_countries': total_countries,
        'last_refreshed_at': last_refreshed_at
    })
