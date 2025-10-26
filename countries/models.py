from django.db import models

class Country(models.Model):
    name = models.CharField(max_length=255, unique=True)
    capital = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=255, null=True, blank=True)
    population = models.BigIntegerField()
    currency_code = models.CharField(max_length=3, null=True)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    estimated_gdp = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    flag_url = models.URLField(null=True, blank=True)
    last_refreshed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "countries"
        ordering = ['name']

    def __str__(self):
        return self.name
