from rest_framework import serializers
from .models import Country

class CountrySerializer(serializers.ModelSerializer):
    # Ensure numeric fields are returned as numbers (not strings)
    exchange_rate = serializers.FloatField(allow_null=True, read_only=True)
    estimated_gdp = serializers.FloatField(allow_null=True, read_only=True)
    last_refreshed_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Country
        fields = [
            'id', 'name', 'capital', 'region', 'population',
            'currency_code', 'exchange_rate', 'estimated_gdp',
            'flag_url', 'last_refreshed_at'
        ]
        read_only_fields = [
            'id', 'exchange_rate', 'estimated_gdp',
            'last_refreshed_at'
        ]